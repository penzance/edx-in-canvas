from django.conf import settings
from unittest import TestCase
from mock import patch, MagicMock
from edx2canvas.models import CanvasApiAuthorization, EdxCourse

class TestBase(TestCase):

    def setUp(self):
        super(TestBase, self).setUp()
        self.edx_course_id = 42
        self.edx_course = EdxCourse(
            title='EdX Course Title',
            org='edX_course_org',
            course='edX_course_course',
            run='edX_course_run',
            key_version=1
        )
        self.edx_course_key = self.edx_course.course_key()
        self.edx_usage_id = 'edx_content_usage_id'
        self.content_title = 'content item title'
        self.edx_url_base = 'https://edx.example.com'
        settings.EDX_URL_BASE = self.edx_url_base

        self.canvas_course_id = 256
        self.canvas_module_id = 123
        self.canvas_user_id = 'value of the LTI user_id field'
        self.canvas_api_token = 'Token to access the Canvas API'
        self.canvas_api_authorization = CanvasApiAuthorization(
            lti_user_id=self.canvas_user_id,
            canvas_api_token=self.canvas_api_token,
        )
        self.canvas_external_tool_id = 12
        self.module_list = ['Module 1', 'Module 2']
        self.canvas_course = dict(
            id=234,
        )

        self.authorization_mock = self.setup_patch(
            'edx2canvas.models.CanvasApiAuthorization.objects.get',
            self.canvas_api_authorization
        )
        self.setup_patch(
            'edx2canvas.models.EdxCourse.objects.get',
            self.edx_course
        )
        self.setup_patch(
            'edx2canvas.models.EdxCourse.objects.all',
            [self.edx_course]
        )
        self.setup_patch(
            'edx2canvas.canvas_api.get_module_list',
            self.module_list
        )
        self.setup_patch(
            'edx2canvas.canvas_api.get_courses',
            [self.canvas_course]
        )

    def setup_patch(self, function_name, return_value):
        """
        Patch a method with a given return value, and return the mock
        """
        mock = MagicMock(return_value=return_value)
        new_patch = patch(function_name, new=mock)
        new_patch.start()
        self.addCleanup(new_patch.stop)
        return mock

    def get_template(self, template):
        return 'edx2canvas/{}.html'.format(template)
