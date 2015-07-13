from django.conf.urls import patterns, url

urlpatterns = patterns('',

    url(r'^lti_launch$', 'edx2canvas.views.lti_launch', name='lti_launch'),
    url(r'^main$', 'edx2canvas.views.main', name='main'),
    url(r'^canvas_modules$', 'edx2canvas.views.get_canvas_modules', name='canvas_modules'),
    url(r'^edx_course$', 'edx2canvas.views.get_edx_course', name='edx_course'),
    url(r'^tool_config$', 'edx2canvas.views.tool_config', name='tool_config'),

    url(r'^add_to_canvas$', 'edx2canvas.populate.add_to_canvas', name='add_to_canvas'),
    url(r'^create_canvas_module$', 'edx2canvas.populate.create_canvas_module', name='create_canvas_module'),

    url(r'^lti_preview', 'edx2canvas.lti_consumer.launch_lti_preview', name='launch_lti_preview'),

    url(r'^start_oauth$', 'edx2canvas.canvas_api.start_oauth', name='start_oauth'),
    url(r'^oauth_redirect$', 'edx2canvas.canvas_api.oauth_redirect', name='oauth_redirect'),

)
