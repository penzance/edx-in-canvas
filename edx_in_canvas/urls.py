from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^edx2canvas/', include('edx2canvas.urls', namespace="edx2canvas")),
    url(r'^auth_error/', 'edx_in_canvas.views.lti_auth_error', name='lti_auth_error'),
)
