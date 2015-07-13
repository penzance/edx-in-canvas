import ddt
from django.conf import settings
from django.contrib.auth.models import User
import django.http
from mock import patch, ANY
import edx2canvas.models as models
import edx2canvas.lti_consumer as lti_consumer
import test_common

@ddt.ddt
class LaunchLtiPreviewTests(test_common.TestBase):

    def setUp(self):
        super(LaunchLtiPreviewTests, self).setUp()
        self.request = django.http.HttpRequest()
        self.request.method = 'GET'
        self.request.GET = {
            'course_id': self.edx_course_id, 'usage_id': self.edx_usage_id
        }
        self.request.user = User()

    @ddt.data(
        'course_id',
        'usage_id',
    )
    def test_missing_post_parameter(self, param):
        del self.request.GET[param]
        response = lti_consumer.launch_lti_preview(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status when parameter {} missing'.format(param)
        )

    def test_main_with_missing_course(self):
        with patch('edx2canvas.models.EdxCourse.objects.get') as get_mock:
            get_mock.side_effect = models.EdxCourse.DoesNotExist()
            response = lti_consumer.launch_lti_preview(self.request)
        self.assertEqual(
            response.status_code, 404,
            'Expected Not Found status code when edX course does not exist'
        )

@ddt.ddt
class GetLtiContextTests(test_common.TestBase):

    def setUp(self):
        super(GetLtiContextTests, self).setUp()
        self.lti_preview_settings = {
            'url_base': 'https://edx.example.com/lti_provider/courses',
            'key': 'preview_key',
            'secret': 'preview_secret',
            'tool_consumer_instance_guid': 'Consumer GUID',
            'user_id': 'Preview user',
            'roles': '[student]',
            'context_id': 'Installation context',
            'lti_version': 'LTI-1p0'
        }
        self.launch_url = u'{}/{}/{}'.format(
                self.lti_preview_settings['url_base'],
                self.edx_course_key, self.edx_usage_id
            )
        settings.EDX_LTI_PREVIEW_SETTINGS = self.lti_preview_settings
        self.oauth_values = dict(
            oauth_nonce='oauth_nonce',
            oauth_signature='oauth_signature',
            oauth_timestamp='oauth_timestamp',
            oauth_signature_method='oauth_signature_method',
            oauth_version='oauth_version'
        )
        authorization_header = 'OAuth '
        for k, v in self.oauth_values.iteritems():
            authorization_header += '{}={},'.format(k, v)
        authorization_header = authorization_header[:-1]
        self.sign_mock = self.setup_patch(
            'edx2canvas.lti_consumer.Client.sign',
            (None, {'Authorization': authorization_header}, None)
        )

    @ddt.data(
        ('oauth_consumer_key', 'preview_key'),
        ('tool_consumer_instance_guid', 'Consumer GUID'),
        ('user_id', 'Preview user'),
        ('roles', '[student]'),
        ('context_id', 'Installation context'),
        ('lti_version', 'LTI-1p0'),
        ('oauth_nonce', 'oauth_nonce'),
        ('oauth_signature', 'oauth_signature'),
        ('oauth_timestamp', 'oauth_timestamp'),
        ('oauth_signature_method', 'oauth_signature_method'),
        ('oauth_version', 'oauth_version'),
    )
    @ddt.unpack
    def test_launch_context(self, key, value):
        context = lti_consumer.get_lti_context(self.edx_course, self.edx_usage_id)
        self.assertEqual(context[key], value)

    def test_launch_url(self):
        context = lti_consumer.get_lti_context(self.edx_course, self.edx_usage_id)
        self.assertEqual(context['lti_url'], self.launch_url)

    def test_signing_method_called(self):
        lti_consumer.get_lti_context(self.edx_course, self.edx_usage_id)
        self.sign_mock.assert_called_once_with(
            self.launch_url,
            http_method=u'POST',
            body=ANY,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
