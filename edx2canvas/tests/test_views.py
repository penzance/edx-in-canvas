import ddt
from django.contrib.auth.models import User
import django.http
import json
from lxml import etree
from mock import patch, ANY, DEFAULT, MagicMock
from canvas_sdk.exceptions import CanvasAPIError

import edx2canvas.views as views
import edx2canvas.models as models
import test_common

@ddt.ddt
class ToolConfigTests(test_common.TestBase):

    def setUp(self):
        super(ToolConfigTests, self).setUp()
        self.server_name = 'test.example.com'
        self.request = django.http.HttpRequest()
        self.request.method = 'GET'
        self.request.META = dict(
            SERVER_NAME=self.server_name,
            SERVER_PORT=443,
        )
        self.request.is_secure = MagicMock(return_value=True)
        self.deployment_path = '/path/to/app/lti_launch'
        self.setup_patch(
            'edx2canvas.views.reverse',
            self.deployment_path
        )

    def verify_response_value(self, response, xpath, expected):
        xml = etree.fromstring(response.content)
        result = xml.xpath(
            xpath,
            namespaces={'lti': 'http://www.imsglobal.org/xsd/imsbasiclti_v1p0',
                        'cm': 'http://www.imsglobal.org/xsd/imslticm_v1p0'}
        )
        self.assertEqual(
            len(result), 1,
            'Expected exactly one match for xpath {}. Found {}'.format(xpath, len(result))
        )
        if etree.iselement(result[0]):
            text = result[0].text
        else:
            text = result[0]
        self.assertEqual(
            text, expected,
            'Unexpected value {} for xpath {}. Expected {}'.format(
                text, xpath, expected
            )
        )

    def test_response_content_type(self):
        response = views.tool_config(self.request)
        self.assertEqual(
            response['Content-Type'], 'text/xml',
            'Expected tool config Content-Type header to be "text/xml"'
        )

    def test_response_status_code(self):
        response = views.tool_config(self.request)
        self.assertEqual(
            response.status_code, 200, 'Expected OK status code for tool config'
        )

    def test_insecure_config_request(self):
        self.request.is_secure = MagicMock(return_value=False)
        self.request.META['SERVER_PORT'] = 80
        response = views.tool_config(self.request)
        self.verify_response_value(
            response, 'lti:launch_url', 'http://{}{}'.format(
                self.server_name, self.deployment_path
            ))

    def test_secure_config_request(self):
        response = views.tool_config(self.request)
        self.verify_response_value(
            response, 'lti:launch_url', 'https://{}{}'.format(
                self.server_name, self.deployment_path
            ))

    @ddt.data(
        ('lti:title', 'Add edX Content'),
        ('lti:description', 'Import content from edX to Canvas'),
        ('lti:extensions/@platform', 'canvas.instructure.com'),
        ('lti:extensions/cm:property', 'public'),
        ('lti:extensions/cm:options/@name', 'course_navigation'),
        ('lti:extensions/cm:options/cm:property[@name="text"]', 'Add edX Content'),
        ('lti:extensions/cm:options/cm:property[@name="enabled"]', 'true'),
        ('lti:extensions/cm:options/cm:property[@name="visibility"]', 'admins'),
    )
    @ddt.unpack
    def test_xpaths(self, xpath, expected):
        response = views.tool_config(self.request)
        self.verify_response_value(response, xpath, expected)


@ddt.ddt
class TestMainView(test_common.TestBase):

    def setUp(self):
        super(TestMainView, self).setUp()
        self.request = django.http.HttpRequest()
        self.request.method = 'GET'
        self.request.session = {
            'LTI_LAUNCH': {
                'custom_canvas_course_id': self.canvas_course_id,
                'user_id': self.canvas_user_id
            }
        }
        self.request.user = User()

    @patch('edx2canvas.views.render')
    def test_main_context(self, render_mock):
        views.main(self.request)
        context = dict(
            canvas_modules=json.dumps({
                'modules': self.module_list, 'id': self.canvas_course_id
            }),
            edx_courses=[self.edx_course]
        )
        render_mock.assert_called_once_with(
            self.request, self.get_template('index'), context
        )

    def test_main_status(self):
        response = views.main(self.request)
        self.assertEqual(
            response.status_code, 200,
            'Expected OK status code for launch of views.main'
        )

    def test_main_with_missing_launch_session(self):
        del self.request.session['LTI_LAUNCH']
        response = views.main(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status code when LTI_LAUNCH not in session'
        )

    @ddt.data(
        'custom_canvas_course_id',
        'user_id'
    )
    def test_main_with_missing_launch_session_param(self, param):
        del self.request.session['LTI_LAUNCH'][param]
        response = views.main(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status code when LTI_LAUNCH[{}] not in session'.format(param)
        )

    @patch('edx2canvas.canvas_api.start_oauth')
    def test_main_with_missing_auth(self, oauth_mock):
        with patch('edx2canvas.models.CanvasApiAuthorization.objects.get') as get_mock:
            get_mock.side_effect = models.CanvasApiAuthorization.DoesNotExist()
            views.main(self.request)
        oauth_mock.assert_called_once_with(self.request, self.canvas_user_id)

    @patch('edx2canvas.canvas_api.start_oauth')
    def test_redirect_on_API_auth_error(self, oauth_mock):
        with patch('edx2canvas.canvas_api.get_courses') as courses_mock:
            courses_mock.side_effect = CanvasAPIError(status_code=401)
            views.main(self.request)
        oauth_mock.assert_called_once_with(self.request, self.canvas_user_id)

class TestGetCanvasModules(test_common.TestBase):
    def setUp(self):
        super(TestGetCanvasModules, self).setUp()
        self.request = django.http.HttpRequest()
        self.request.method = 'GET'
        self.request.GET = {'course_id': self.canvas_course_id}
        self.request.session = {'LTI_LAUNCH': {'user_id': self.canvas_user_id}}
        self.request.user = User()

    def test_get_modules(self):
        response = views.get_canvas_modules(self.request)
        self.assertEqual(
            json.loads(response.content),
            {'id': self.canvas_course_id, 'modules': self.module_list}
        )

    def test_main_with_missing_launch_session(self):
        del self.request.session['LTI_LAUNCH']
        response = views.get_canvas_modules(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status code when LTI_LAUNCH not in session'
        )

    def test_main_with_missing_user_id(self):
        del self.request.session['LTI_LAUNCH']['user_id']
        response = views.get_canvas_modules(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status code when LTI_LAUNCH[user_id] not in session'
        )

    def test_main_with_missing_course_id(self):
        del self.request.GET['course_id']
        response = views.get_canvas_modules(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status code when LTI_LAUNCH not in session'
        )

    def test_main_with_missing_auth(self):
        with patch('edx2canvas.models.CanvasApiAuthorization.objects.get') as get_mock:
            get_mock.side_effect = models.CanvasApiAuthorization.DoesNotExist()
            response = views.get_canvas_modules(self.request)
        self.assertEqual(
            response.status_code, 403,
            'Expected Forbidden status code if no API key exists. Got: {}'.format(response.status_code)
        )

class TestGetEdxCourse(test_common.TestBase):
    def setUp(self):
        super(TestGetEdxCourse, self).setUp()
        self.request = django.http.HttpRequest()
        self.request.method = 'GET'
        self.request.GET = {'edx_course_id': self.canvas_course_id}
        self.request.user = User()
        self.parsed_course = 'A parsed edX course'

    def test_main_with_missing_course_id(self):
        del self.request.GET['edx_course_id']
        response = views.get_edx_course(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status code when LTI_LAUNCH not in session'
        )

    def test_main_with_missing_course(self):
        with patch('edx2canvas.models.EdxCourse.objects.get') as get_mock:
            get_mock.side_effect = models.EdxCourse.DoesNotExist()
            response = views.get_edx_course(self.request)
        self.assertEqual(
            response.status_code, 404,
            'Expected Not Found status code when edX course does not exist'
        )
