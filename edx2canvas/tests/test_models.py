from unittest import TestCase

from edx2canvas.models import EdxCourse

class TestEdxCourseModel(TestCase):

    def setUp(self):
        super(TestEdxCourseModel, self).setUp()
        self.course = EdxCourse(
            title='title',
            org='org',
            course='course',
            run='run',
        )

    def test_v0_course_key(self):
        self.course.key_version = 0
        self.assertEqual(self.course.course_key(), 'org/course/run')

    def test_v1_course_key(self):
        self.course.key_version = 1
        self.assertEqual(self.course.course_key(), 'course-v1:org+course+run')
