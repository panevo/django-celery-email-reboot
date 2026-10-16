import json
import os.path
import subprocess
import sys
import tempfile
import unittest
import warnings
from email.message import MIMEPart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from unittest import mock

from django.core import checks, mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends import locmem
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase
from django.test.utils import override_settings

import celery
import django
from djcelery_email import tasks, utils
from djcelery_email.backends import CeleryEmailBackend


def even(n):
    return n % 2 == 0


def celery_queue_pop():
    """ Pops a single task from Celery's 'memory://' queue. """
    with celery.current_app.connection() as conn:
        queue = conn.SimpleQueue('django_email', no_ack=True)
        return queue.get().payload


class TracingBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        self.__class__.kwargs = kwargs

    def send_messages(self, messages):
        self.__class__.called = True


class CustomEmailMessage(mail.EmailMessage):
    pass


class CustomEmailMultiAlternatives(mail.EmailMultiAlternatives):
    pass


class UtilTests(TestCase):
    @override_settings(CELERY_EMAIL_MESSAGE_EXTRA_ATTRIBUTES=['extra_attribute'])
    def test_email_to_dict_extra_attrs(self):
        msg = mail.EmailMessage()
        msg.extra_attribute = {'name': 'val'}

        self.assertEqual(utils.email_to_dict(msg)['extra_attribute'], msg.extra_attribute)

    @override_settings(CELERY_EMAIL_MESSAGE_EXTRA_ATTRIBUTES=['extra_attribute'])
    def test_dict_to_email_extra_attrs(self):
        msg_dict = utils.email_to_dict(mail.EmailMessage())
        msg_dict['extra_attribute'] = {'name': 'val'}

        self.assertEqual(utils.email_to_dict(utils.dict_to_email(msg_dict)), msg_dict)

    def check_json_of_msg(self, msg):
        serialized = json.dumps(utils.email_to_dict(msg))
        self.assertEqual(
            utils.email_to_dict(utils.dict_to_email(json.loads(serialized))),
            utils.email_to_dict(msg))

    def test_email_with_attachment(self):
        file_path = os.path.join(os.path.dirname(__file__), 'image.png')
        with open(file_path, 'rb') as file:
            file_contents = file.read()
        msg = mail.EmailMessage(
            'test', 'Testing with Celery! w00t!!', 'from@example.com',
            ['to@example.com'])
        msg.attach('image.png', file_contents)
        self.check_json_of_msg(msg)

    def test_email_with_mime_attachment(self):
        file_path = os.path.join(os.path.dirname(__file__), 'image.png')
        with open(file_path, 'rb') as file:
            file_contents = file.read()
        mimg = MIMEImage(file_contents)
        msg = mail.EmailMessage(
            'test', 'Testing with Celery! w00t!!', 'from@example.com',
            ['to@example.com'])
        msg.attach(mimg)
        self.check_json_of_msg(msg)

    def test_email_with_attachment_from_file(self):
        file_path = os.path.join(os.path.dirname(__file__), 'image.png')
        msg = mail.EmailMessage(
            'test', 'Testing with Celery! w00t!!', 'from@example.com',
            ['to@example.com'])
        msg.attach_file(file_path)
        self.check_json_of_msg(msg)

    @override_settings(CELERY_EMAIL_MESSAGE_CLASS='tests.tests.CustomEmailMessage')
    def test_custom_email_message_class(self):
        msg = utils.get_email_message_class()()
        self.assertIsInstance(msg, CustomEmailMessage)

    @override_settings(CELERY_EMAIL_MULTI_ALTERNATIVES_CLASS='tests.tests.CustomEmailMultiAlternatives')
    def test_custom_email_multi_alternatives_class(self):
        msg = utils.get_email_multi_alternatives_class()()
        self.assertIsInstance(msg, CustomEmailMultiAlternatives)

    def test_email_to_dict_without_tasks_imported(self):
        # utils must load the default settings itself instead of relying on
        # tasks.py having imported conf.py first (#16). Needs a fresh
        # interpreter because this test module already imports tasks.
        code = (
            "import django\n"
            "from django.conf import settings\n"
            "settings.configure()\n"
            "django.setup()\n"
            "from django.core.mail import EmailMessage\n"
            "from djcelery_email.utils import email_to_dict\n"
            "email_to_dict(EmailMessage())\n"
        )
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


# Django 6.0 added MIMEPart attachments and deprecated MIMEBase ones
HAS_MIMEPART_ATTACHMENTS = django.VERSION >= (6, 0)


def read_image():
    with open(os.path.join(os.path.dirname(__file__), 'image.png'), 'rb') as file:
        return file.read()


def inline_image(content):
    image = MIMEImage(content)
    image.add_header('Content-ID', '<logo@example.com>')
    image.add_header('Content-Disposition', 'inline', filename='logo.png')
    return image


def find_part(message, content_id):
    for part in message.walk():
        if part['Content-ID'] == content_id:
            return part
    raise AssertionError('No part with Content-ID %s' % content_id)


class MimeAttachmentTests(TestCase):
    """MIME attachments must arrive as they were attached, with all their headers."""

    def setUp(self):
        super().setUp()
        conf = celery.current_app.conf
        self.addCleanup(setattr, conf, 'task_always_eager', conf.task_always_eager)
        conf.task_always_eager = True

    def round_trip(self, msg):
        return utils.dict_to_email(json.loads(json.dumps(utils.email_to_dict(msg))))

    def test_inline_image_keeps_its_content_id(self):
        content = read_image()
        msg = EmailMultiAlternatives('test', 'body', 'from@example.com', ['to@example.com'])
        msg.attach_alternative('<img src="cid:logo@example.com">', 'text/html')
        with warnings.catch_warnings():
            # Django 6.0+ warns about MIMEBase attachments
            warnings.simplefilter('ignore')
            msg.attach(inline_image(content))

        [result] = msg.send()

        self.assertEqual(result.get(), 1)
        part = find_part(mail.outbox[0].message(), '<logo@example.com>')
        self.assertEqual(part.get_content_type(), 'image/png')
        self.assertEqual(part.get_content_disposition(), 'inline')
        self.assertEqual(part.get_filename(), 'logo.png')
        self.assertEqual(part.get_payload(decode=True), content)

    def test_mime_text_attachment_keeps_its_lines(self):
        text = 'From the report:\nline two\n'
        attachment = MIMEText(text, 'plain', 'utf-8')
        attachment.add_header('Content-Disposition', 'attachment', filename='report.txt')
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            msg.attach(attachment)

        [attachment] = self.round_trip(msg).attachments

        self.assertEqual(attachment.get_payload(decode=True).decode('utf-8'), text)
        self.assertEqual(attachment.get_filename(), 'report.txt')

    def test_mime_and_tuple_attachments_keep_their_order(self):
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])
        msg.attach('first.txt', 'first', 'text/plain')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            msg.attach(inline_image(read_image()))
        msg.attach('last.bin', b'last', 'application/octet-stream')

        first, image, last = self.round_trip(msg).attachments

        self.assertEqual(tuple(first), ('first.txt', 'first', 'text/plain'))
        self.assertEqual(image['Content-ID'], '<logo@example.com>')
        self.assertEqual(tuple(last), ('last.bin', b'last', 'application/octet-stream'))

    @unittest.skipUnless(HAS_MIMEPART_ATTACHMENTS, 'MIMEPart attachments require Django 6.0+')
    def test_mimepart_attachment(self):
        content = read_image()
        part = MIMEPart()
        part.set_content(content, maintype='image', subtype='png', disposition='inline',
                         filename='logo.png', cid='<logo@example.com>')
        msg = EmailMultiAlternatives('test', 'body', 'from@example.com', ['to@example.com'])
        msg.attach_alternative('<img src="cid:logo@example.com">', 'text/html')
        msg.attach(part)

        [result] = msg.send()

        self.assertEqual(result.get(), 1)
        part = find_part(mail.outbox[0].message(), '<logo@example.com>')
        self.assertEqual(part.get_content_disposition(), 'inline')
        self.assertEqual(part.get_filename(), 'logo.png')
        self.assertEqual(part.get_payload(decode=True), content)

    def test_mime_attachments_are_rebuilt_without_deprecation_warnings(self):
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            msg.attach(inline_image(read_image()))
        msg_dict = json.loads(json.dumps(utils.email_to_dict(msg)))

        with warnings.catch_warnings():
            warnings.simplefilter('error')
            [attachment] = utils.dict_to_email(msg_dict).attachments

        # Django 6.0+ expects MIMEPart attachments, older versions MIMEBase ones
        self.assertIsInstance(attachment, MIMEPart if HAS_MIMEPART_ATTACHMENTS else MIMEBase)


class TaskTests(TestCase):
    """
    Tests that the 'tasks.send_email(s)' task works correctly:
        - should accept a single or multiple messages (as dicts)
        - should send all these messages
        - should use the backend set in CELERY_EMAIL_BACKEND
        - should pass the given kwargs to that backend
        - should retry sending failed messages (see TaskErrorTests)
    """
    def test_send_single_email_object(self):
        """ It should accept and send a single EmailMessage object. """
        msg = mail.EmailMessage()
        tasks.send_email(msg, backend_kwargs={})
        self.assertEqual(len(mail.outbox), 1)
        # we can't compare them directly as it's converted into a dict
        # for JSONification and then back. Compare dicts instead.
        self.assertEqual(utils.email_to_dict(msg), utils.email_to_dict(mail.outbox[0]))

    def test_send_single_email_object_no_backend_kwargs(self):
        """ It should send email with backend_kwargs not provided. """
        msg = mail.EmailMessage()
        tasks.send_email(msg)
        self.assertEqual(len(mail.outbox), 1)
        # we can't compare them directly as it's converted into a dict
        # for JSONification and then back. Compare dicts instead.
        self.assertEqual(utils.email_to_dict(msg), utils.email_to_dict(mail.outbox[0]))

    def test_send_single_email_object_response(self):
        """ It should return the number of messages sent, 1 here. """
        msg = mail.EmailMessage()
        messages_sent = tasks.send_email(msg)
        self.assertEqual(messages_sent, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_single_email_dict(self):
        """ It should accept and send a single EmailMessage dict. """
        msg = mail.EmailMessage()
        tasks.send_email(utils.email_to_dict(msg), backend_kwargs={})
        self.assertEqual(len(mail.outbox), 1)
        # we can't compare them directly as it's converted into a dict
        # for JSONification and then back. Compare dicts instead.
        self.assertEqual(utils.email_to_dict(msg), utils.email_to_dict(mail.outbox[0]))

    def test_send_multiple_email_objects(self):
        """ It should accept and send a list of EmailMessage objects. """
        N = 10
        msgs = [mail.EmailMessage() for i in range(N)]
        tasks.send_emails([utils.email_to_dict(msg) for msg in msgs],
                          backend_kwargs={})

        self.assertEqual(len(mail.outbox), N)
        for i in range(N):
            self.assertEqual(utils.email_to_dict(msgs[i]), utils.email_to_dict(mail.outbox[i]))

    def test_send_multiple_email_dicts(self):
        """ It should accept and send a list of EmailMessage dicts. """
        N = 10
        msgs = [mail.EmailMessage() for i in range(N)]
        tasks.send_emails(msgs, backend_kwargs={})

        self.assertEqual(len(mail.outbox), N)
        for i in range(N):
            self.assertEqual(utils.email_to_dict(msgs[i]), utils.email_to_dict(mail.outbox[i]))

    def test_send_multiple_email_dicts_response(self):
        """ It should return the number of messages sent. """
        N = 10
        msgs = [mail.EmailMessage() for i in range(N)]
        messages_sent = tasks.send_emails(msgs, backend_kwargs={})
        self.assertEqual(messages_sent, N)
        self.assertEqual(len(mail.outbox), N)

    @override_settings(CELERY_EMAIL_BACKEND='tests.tests.TracingBackend')
    def test_uses_correct_backend(self):
        """ It should use the backend configured in CELERY_EMAIL_BACKEND. """
        TracingBackend.called = False
        msg = mail.EmailMessage()
        tasks.send_email(utils.email_to_dict(msg), backend_kwargs={})
        self.assertTrue(TracingBackend.called)

    @override_settings(CELERY_EMAIL_BACKEND='tests.tests.TracingBackend')
    def test_backend_parameters(self):
        """ It should pass kwargs like username and password to the backend. """
        TracingBackend.kwargs = None
        msg = mail.EmailMessage()
        tasks.send_email(utils.email_to_dict(msg), backend_kwargs={'foo': 'bar'})
        self.assertEqual(TracingBackend.kwargs.get('foo'), 'bar')

    @override_settings(CELERY_EMAIL_BACKEND='tests.tests.TracingBackend')
    def test_backend_parameters_kwargs(self):
        """ It should pass on kwargs specified as keyword params. """
        TracingBackend.kwargs = None
        msg = mail.EmailMessage()
        tasks.send_email(utils.email_to_dict(msg), foo='bar')
        self.assertEqual(TracingBackend.kwargs.get('foo'), 'bar')


class EvenErrorBackend(locmem.EmailBackend):
    """ Fails to deliver every 2nd message. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_count = 0

    def send_messages(self, messages):
        self.message_count += 1
        if even(self.message_count-1):
            raise RuntimeError("Something went wrong sending the message")
        else:
            return super().send_messages(messages)


class TaskWarningTests(TestCase):
    def test_task_does_not_use_deprecated_get_connection(self):
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            tasks.send_emails([utils.email_to_dict(msg)], {})

        self.assertEqual(len(mail.outbox), 1)
        # Django 6.1 deprecates get_connection()
        self.assertEqual([str(w.message) for w in caught if 'get_connection' in str(w.message)], [])


class TaskErrorTests(TestCase):
    """
    Tests that the 'tasks.send_emails' task does not crash if a single message
    could not be sent and that it requeues that message.
    """
    def setUp(self):
        super().setUp()

        self._retry_calls = []

        def mock_retry(*args, **kwargs):
            self._retry_calls.append((args, kwargs))

        patcher = mock.patch.object(tasks.send_emails, 'retry', mock_retry)
        patcher.start()
        self.addCleanup(patcher.stop)

    @override_settings(CELERY_EMAIL_BACKEND='tests.tests.EvenErrorBackend')
    def test_send_multiple_emails(self):
        N = 10
        msgs = [mail.EmailMessage(subject="msg %d" % i) for i in range(N)]
        tasks.send_emails([utils.email_to_dict(msg) for msg in msgs],
                          backend_kwargs={'foo': 'bar'})

        # Assert that only "odd"/good messages have been sent.
        self.assertEqual(len(mail.outbox), 5)
        self.assertEqual(
            [msg.subject for msg in mail.outbox],
            ["msg 1", "msg 3", "msg 5", "msg 7", "msg 9"]
        )

        # Assert that "even"/bad messages have been requeued,
        # one retry task per bad message.
        self.assertEqual(len(self._retry_calls), 5)
        odd_msgs = [msg for idx, msg in enumerate(msgs) if even(idx)]
        for msg, (args, kwargs) in zip(odd_msgs, self._retry_calls):
            retry_args = args[0]
            self.assertEqual(retry_args, [[utils.email_to_dict(msg)], {'foo': 'bar'}])
            self.assertTrue(isinstance(kwargs.get('exc'), RuntimeError))
            self.assertFalse(kwargs.get('throw', True))


class BackendTests(TestCase):
    """
    Tests that our *own* email backend ('backends.CeleryEmailBackend') works,
    i.e. it submits the correct number of jobs (according to the chunk size)
    and passes backend parameters to the task.
    """
    def setUp(self):
        super().setUp()

        self._delay_calls = []

        def mock_delay(*args, **kwargs):
            self._delay_calls.append((args, kwargs))

        patcher = mock.patch.object(tasks.send_emails, 'delay', mock_delay)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_backend_parameters(self):
        """ Our backend should pass kwargs to the 'send_emails' task. """
        kwargs = {'auth_user': 'user', 'auth_password': 'pass'}
        mail.send_mass_mail([
            ('test1', 'Testing with Celery! w00t!!', 'from@example.com', ['to@example.com']),
            ('test2', 'Testing with Celery! w00t!!', 'from@example.com', ['to@example.com'])
        ], **kwargs)

        self.assertEqual(len(self._delay_calls), 1)
        args, kwargs = self._delay_calls[0]
        messages, backend_kwargs = args
        self.assertEqual(messages[0]['subject'], 'test1')
        self.assertEqual(messages[1]['subject'], 'test2')
        self.assertEqual(backend_kwargs, {'username': 'user', 'password': 'pass'})

    def test_chunking(self):
        """
        Given 11 messages and a chunk size of 4, the backend should queue
        11/4 = 3 jobs (2 jobs with 4 messages and 1 job with 3 messages).
        """
        N = 11
        chunksize = 4

        with override_settings(CELERY_EMAIL_CHUNK_SIZE=4):
            mail.send_mass_mail([
                ("subject", "body", "from@example.com", ["to@example.com"])
                for _ in range(N)
            ])

            num_chunks = 3  # floor(11.0 / 4.0)
            self.assertEqual(len(self._delay_calls), num_chunks)

            full_tasks = self._delay_calls[:-1]
            last_task = self._delay_calls[-1]

            for args, kwargs in full_tasks:
                self.assertEqual(len(args[0]), chunksize)

            args, kwargs = last_task
            self.assertEqual(len(args[0]), N % chunksize)


class ConfigTests(TestCase):
    """
    Tests that our Celery task has been initialized with the correct options
    (those set in the CELERY_EMAIL_TASK_CONFIG setting)
    """
    def test_setting_extra_configs(self):
        self.assertEqual(tasks.send_email.queue, 'django_email')
        self.assertEqual(tasks.send_email.delivery_mode, 1)
        self.assertEqual(tasks.send_email.rate_limit, '50/m')


class IntegrationTests(TestCase):
    # We run these tests in ALWAYS_EAGER mode, but they might as well be
    # executed using a real backend (maybe we can add that to the test setup in
    # the future?)

    def setUp(self):
        super().setUp()
        # Celery keeps its settings in a mapping, which mock.patch.object can't restore.
        conf = celery.current_app.conf
        self.addCleanup(setattr, conf, 'task_always_eager', conf.task_always_eager)
        conf.task_always_eager = True

    def test_sending_email(self):
        [result] = mail.send_mail('test', 'Testing with Celery! w00t!!', 'from@example.com',
                                  ['to@example.com'])
        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'test')

    def test_sending_html_email(self):
        msg = EmailMultiAlternatives('test', 'Testing with Celery! w00t!!', 'from@example.com',
                                     ['to@example.com'])
        html = '<p>Testing with Celery! w00t!!</p>'
        msg.attach_alternative(html, 'text/html')
        [result] = msg.send()
        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'test')
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(list(mail.outbox[0].alternatives[0]), [html, 'text/html'])

    def test_sending_mail_with_text_attachment(self):
        msg = mail.EmailMessage(
            'test', 'Testing with Celery! w00t!!', 'from@example.com',
            ['to@example.com'])
        msg.attach('image.png', 'csv content', 'text/csv')
        [result] = msg.send()
        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'test')
        self.assertEqual(mail.outbox[0].content_subtype, "plain")

    def test_sending_html_only_email(self):
        msg = mail.EmailMessage('test', 'Testing <b>with Celery! w00t!!</b>', 'from@example.com',
                                ['to@example.com'])
        msg.content_subtype = "html"
        [result] = msg.send()
        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'test')
        self.assertEqual(mail.outbox[0].content_subtype, "html")

    def test_sending_mass_email(self):
        emails = (
            ('mass 1', 'mass message 1', 'from@example.com', ['to@example.com']),
            ('mass 2', 'mass message 2', 'from@example.com', ['to@example.com']),
        )
        [result] = mail.send_mass_mail(emails)
        self.assertEqual(result.get(), 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, 'mass 1')
        self.assertEqual(mail.outbox[1].subject, 'mass 2')

    def test_sending_mass_email_chunked(self):
        emails = [
            ('mass %i' % i, 'message', 'from@example.com', ['to@example.com'])
            for i in range(11)]
        with override_settings(CELERY_EMAIL_CHUNK_SIZE=4):
            [result1, result2, result3] = mail.send_mass_mail(emails)
            self.assertEqual(result1.get(), 4)
            self.assertEqual(result2.get(), 4)
            self.assertEqual(result3.get(), 3)
            self.assertEqual(len(mail.outbox), 11)
            self.assertEqual(mail.outbox[0].subject, 'mass 0')
            self.assertEqual(mail.outbox[1].subject, 'mass 1')


class ConflictingPackageCheckTests(TestCase):
    def conflict_warnings(self):
        return [m for m in checks.run_checks() if m.id == 'djcelery_email.W001']

    def test_warns_when_django_celery_email_is_installed(self):
        # A dist-info folder on sys.path is all importlib.metadata needs to
        # report the original django-celery-email as installed (#20).
        with tempfile.TemporaryDirectory() as site_dir:
            dist_info = os.path.join(site_dir, 'django_celery_email-3.0.0.dist-info')
            os.mkdir(dist_info)
            with open(os.path.join(dist_info, 'METADATA'), 'w') as f:
                f.write('Metadata-Version: 2.1\nName: django-celery-email\nVersion: 3.0.0\n')
            sys.path.insert(0, site_dir)
            try:
                warnings = self.conflict_warnings()
            finally:
                sys.path.remove(site_dir)

        self.assertEqual(len(warnings), 1)
        self.assertIn('django-celery-email', warnings[0].msg)

    def test_no_warning_without_django_celery_email(self):
        self.assertEqual(self.conflict_warnings(), [])


class MailersCheckTests(TestCase):
    def test_no_errors_without_mailers(self):
        self.assertEqual([m for m in checks.run_checks() if m.id == 'djcelery_email.E001'], [])


class FailSilentlyTests(TestCase):
    def test_fail_silently_without_deprecation_warning(self):
        # Django 6.1 deprecates passing fail_silently to BaseEmailBackend, so the
        # backend has to handle it itself.
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            backend = CeleryEmailBackend(fail_silently=True)
        self.assertTrue(backend.fail_silently)


HAS_MAILERS = hasattr(mail, 'mailers')

MAILERS = {
    'default': {
        'BACKEND': 'djcelery_email.backends.CeleryEmailBackend',
        'OPTIONS': {'using': 'wrapped'},
    },
    'wrapped': {
        'BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    },
}


@unittest.skipUnless(HAS_MAILERS, 'MAILERS requires Django 6.1+')
@override_settings(MAILERS=MAILERS)
class MailersTests(TestCase):
    def setUp(self):
        super().setUp()
        conf = celery.current_app.conf
        self.addCleanup(setattr, conf, 'task_always_eager', conf.task_always_eager)
        conf.task_always_eager = True

    def assertInvalidMailer(self, options, message):
        mailers = {**MAILERS, 'default': {**MAILERS['default'], 'OPTIONS': options}}
        with override_settings(MAILERS=mailers):
            with self.assertRaisesMessage(mail.InvalidMailer, message):
                mail.mailers['default']

    def test_sends_through_wrapped_mailer(self):
        [result] = mail.send_mail('test', 'body', 'from@example.com', ['to@example.com'])

        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].sent_using, 'wrapped')

    def test_retry_keeps_wrapped_mailer(self):
        mailers = {**MAILERS, 'wrapped': {'BACKEND': 'tests.tests.EvenErrorBackend'}}
        msgs = [mail.EmailMessage(subject="msg %d" % i) for i in range(2)]

        with override_settings(MAILERS=mailers), mock.patch.object(tasks.send_emails, 'retry') as retry:
            tasks.send_emails([utils.email_to_dict(msg) for msg in msgs], using='wrapped')

        retry.assert_called_once()
        self.assertEqual(retry.call_args.kwargs['kwargs'], {'using': 'wrapped'})

    def mailer_errors(self):
        return [m for m in checks.run_checks() if m.id == 'djcelery_email.E001']

    def test_task_queued_before_mailers_sends_through_wrapped_mailer(self):
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])

        # Queued with EMAIL_BACKEND, before the project switched to MAILERS
        tasks.send_emails([utils.email_to_dict(msg)], {})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].sent_using, 'wrapped')

    def test_task_queued_before_mailers_sends_through_default_mailer(self):
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])

        with override_settings(MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}}):
            tasks.send_emails([utils.email_to_dict(msg)], {})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].sent_using, 'default')

    def test_task_queued_before_mailers_ignores_backend_options(self):
        msg = mail.EmailMessage('test', 'body', 'from@example.com', ['to@example.com'])

        with self.assertLogs('djcelery_email.tasks', 'WARNING') as logs:
            tasks.send_emails([utils.email_to_dict(msg)], {'username': 'user', 'password': 'secret'})

        self.assertEqual(mail.outbox[0].sent_using, 'wrapped')
        [log] = logs.output
        self.assertIn("'wrapped'", log)
        self.assertIn('password, username', log)
        self.assertNotIn('secret', log)

    def test_check_accepts_valid_mailers(self):
        self.assertEqual(self.mailer_errors(), [])

    def test_check_reports_invalid_mailers(self):
        cases = [
            ({}, "'using'"),
            ({'using': 'default'}, "'using'"),
            ({'using': 'missing'}, "'missing'"),
            ({'using': 'wrapped', 'host': 'smtp.example.com'}, "'host'"),
        ]
        for options, message in cases:
            mailers = {**MAILERS, 'default': {**MAILERS['default'], 'OPTIONS': options}}
            with self.subTest(options=options), override_settings(MAILERS=mailers):
                [error] = self.mailer_errors()
                self.assertEqual(error.level, checks.ERROR)
                self.assertIn("MAILERS['default']", error.msg)
                self.assertIn(message, error.msg)

    def test_using_is_required(self):
        self.assertInvalidMailer({}, "'using'")

    def test_using_cannot_refer_to_itself(self):
        self.assertInvalidMailer({'using': 'default'}, "'using'")

    def test_using_must_refer_to_existing_mailer(self):
        self.assertInvalidMailer({'using': 'missing'}, "'missing'")

    def test_unknown_options_are_rejected(self):
        self.assertInvalidMailer({'using': 'wrapped', 'host': 'smtp.example.com'}, "'host'")
