import ddt
from django.contrib.auth.models import User
import django.http
import json
from mock import patch

import test_common
import edx2canvas.populate as populate
import edx2canvas.models as models

def create_request(canvas_user_id, post_params):
    session = {'LTI_LAUNCH': {
        'user_id': canvas_user_id
    }}
    request = django.http.HttpRequest()
    request.POST = post_params
    request.method = 'POST'
    request.session = session
    request.user = User()
    return request

@ddt.ddt
class AddToCanvasTests(test_common.TestBase):
    def setUp(self):
        super(AddToCanvasTests, self).setUp()
        self.module_position = 5
        post_params = dict(
            edx_course_id=self.edx_course_id,
            canvas_course_id=self.canvas_course_id,
            module_id=self.canvas_module_id,
            title=self.content_title,
            usage_id=self.edx_usage_id,
            position=self.module_position,
            graded='false',
        )
        self.request = create_request(self.canvas_user_id, post_params)
        self.setup_patch(
            'edx2canvas.canvas_api.get_external_tool_id',
            self.canvas_external_tool_id
        )

    def check_response(self, response):
        body = json.loads(response.content)
        expected_response = {
            'modules': self.module_list,
            'id': self.canvas_course_id
        }
        self.assertEqual(
            response.status_code, 200,
            'Incorrect status code from call to populate.add_to_canvas'
        )
        self.assertEqual(
            body, expected_response,
            'populate.add_to_canvas returned incorrect JSON content'
        )

    @patch('edx2canvas.canvas_api.create_canvas_module_item')
    def test_add_module_item(self, create_module_item):
        response = populate.add_to_canvas(self.request)
        create_module_item.assert_called_with(
            self.canvas_api_authorization, self.content_title, self.canvas_course_id,
            self.canvas_module_id, self.module_position,
            self.canvas_external_tool_id, '{}/lti_provider/courses/{}/{}'.format(
                self.edx_url_base, self.edx_course_key, self.edx_usage_id
            )
        )
        self.check_response(response)

    @patch('edx2canvas.canvas_api.create_assignment_with_module_item')
    def test_add_assignment(self, create_assignment):
        self.request.POST['graded'] = 'true'
        response = populate.add_to_canvas(self.request)
        create_assignment.assert_called_with(
            self.canvas_api_authorization, self.content_title, self.canvas_course_id,
            self.canvas_module_id, self.module_position,
            self.canvas_external_tool_id, '{}/lti_provider/courses/{}/{}'.format(
                self.edx_url_base, self.edx_course_key, self.edx_usage_id
            )
        )
        self.check_response(response)

    @ddt.data(
        'edx_course_id',
        'canvas_course_id',
        'module_id',
        'title',
        'position',
        'usage_id',
        'graded',
    )
    def test_missing_post_parameter(self, param):
        del self.request.POST[param]
        response = populate.add_to_canvas(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status when parameter {} missing'.format(param)
        )

    def test_missing_edx_course(self):
        with patch('edx2canvas.models.EdxCourse.objects.get') as get_mock:
            get_mock.side_effect = models.EdxCourse.DoesNotExist()
            response = populate.add_to_canvas(self.request)
            self.assertEqual(
                response.status_code, 400,
                'Expected Bad Request status when edX course does not exist'
            )

    def test_missing_canvas_api_record(self):
        with patch('edx2canvas.models.CanvasApiAuthorization.objects.get') as get_mock:
            get_mock.side_effect = models.CanvasApiAuthorization.DoesNotExist()
            response = populate.add_to_canvas(self.request)
            self.assertEqual(
                response.status_code, 403,
                'Expected Bad Request status when Canvas authorization key does not exist'
            )

@ddt.ddt
class CreateCanvasModuleTests(test_common.TestBase):
    def setUp(self):
        super(CreateCanvasModuleTests, self).setUp()
        self.module_position = 5
        post_params = dict(
            canvas_course_id=self.canvas_course_id,
            module_name=self.content_title,
            position=self.module_position,
        )
        self.request = create_request(self.canvas_user_id, post_params)
        self.module = dict(
            id=self.canvas_module_id
        )
        self.create_module_mock = self.setup_patch(
            'edx2canvas.canvas_api.create_canvas_module',
            self.module
        )

    def check_response(self, response):
        body = json.loads(response.content)
        expected_response = {
            'modules': self.module_list,
            'module_id': self.canvas_module_id
        }
        self.assertEqual(
            response.status_code, 200,
            'Incorrect status code from populate.create_canvas_module'
        )
        self.assertEqual(
            body, expected_response,
            'populate.create_canvas_module returned incorrect JSON body'
        )

    def test_create_module(self):
        response = populate.create_canvas_module(self.request)
        self.check_response(response)

    def test_create_module_calls_api(self):
        populate.create_canvas_module(self.request)
        self.create_module_mock.assert_called_once_with(
            self.canvas_api_authorization, self.canvas_course_id,
            self.content_title, self.module_position
        )

    @ddt.data(
        'canvas_course_id',
        'module_name',
        'position',
    )
    def test_missing_post_parameter(self, param):
        del self.request.POST[param]
        response = populate.create_canvas_module(self.request)
        self.assertEqual(
            response.status_code, 400,
            'Expected Bad Request status when parameter {} is missing'.format(param)
        )

    def test_missing_canvas_api_record(self):
        with patch('edx2canvas.models.CanvasApiAuthorization.objects.get') as get_mock:
            get_mock.side_effect = models.CanvasApiAuthorization.DoesNotExist()
            response = populate.create_canvas_module(self.request)
            self.assertEqual(
                response.status_code, 403,
                'Expected Bad Request status when Canvas authorization key does not exist'
            )

@ddt.ddt
class AutoPopulateTests(test_common.TestBase):
    def setUp(self):
        super(AutoPopulateTests, self).setUp()
        post_params = dict(
            canvas_course_id=self.canvas_course_id,
            module_name=self.content_title,
            position=self.module_position,
        )
        self.request = create_request(self.canvas_user_id, post_params)
        self.module = dict(
            id=self.canvas_module_id
        )
        self.create_module_mock = self.setup_patch(
            'edx2canvas.canvas_api.create_canvas_module',
            self.module
        )
