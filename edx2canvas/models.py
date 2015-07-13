from django.db import models


class EdxCourse(models.Model):
    title = models.CharField(max_length=255)
    org = models.CharField(max_length=128)
    course = models.CharField(max_length=32)
    run = models.CharField(max_length=32)
    key_version = models.IntegerField()

    def course_key(self):
        if self.key_version == 0:
            return "{}/{}/{}".format(self.org, self.course, self.run)
        if self.key_version == 1:
            return "course-v1:{}+{}+{}".format(self.org, self.course, self.run)
        raise NotImplementedError()


class CanvasApiAuthorization(models.Model):
    lti_user_id = models.CharField(max_length=255, unique=True, db_index=True)
    canvas_api_token = models.CharField(max_length=255)

    def __unicode__(self):
        return "user: {}, token: {}".format(self.lti_user_id, self.canvas_api_token)
