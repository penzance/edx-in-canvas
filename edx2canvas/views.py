import json

from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from ims_lti_py.tool_config import ToolConfig
import django.http as http
from models import CanvasApiAuthorization, EdxCourse
from canvas_sdk.exceptions import CanvasAPIError
import canvas_api

TOOL_NAME = "edx2canvas"


@require_http_methods(['GET'])
def tool_config(request):
    """
    This produces a Canvas specific XML config that can be used to
    add this tool to the Canvas LMS
    """
    if request.is_secure():
        host = 'https://' + request.get_host()
    else:
        host = 'http://' + request.get_host()

    url = host + reverse('edx2canvas:lti_launch')

    lti_tool_config = ToolConfig(
        title='Add edX Content',
        launch_url=url,
        secure_launch_url=url,
    )
    account_nav_params = {
        'enabled': 'true',
        'text': 'Add edX Content',
        'visibility': 'admins',
    }
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')
    lti_tool_config.set_ext_param('canvas.instructure.com', 'course_navigation', account_nav_params)
    lti_tool_config.description = 'Import content from edX to Canvas'

    return http.HttpResponse(
        lti_tool_config.to_xml(), content_type='text/xml', status=200
    )

@login_required()
@require_http_methods(['POST'])
def lti_launch(request):
    if request.user.is_authenticated():
        return redirect('edx2canvas:main')
    else:
        return render(request, 'edx2canvas/error.html', {'message': 'Error: user is not authenticated!'})


@login_required()
@require_http_methods(['GET'])
def main(request):
    """
    Launch the main page of the authoring app. Create a context that includes
    all available edX courses and the module structure of the Canvas course from
    which the tool was launched.
    """
    try:
        canvas_course_id = request.session['LTI_LAUNCH']['custom_canvas_course_id']
        canvas_user_id = request.session['LTI_LAUNCH']['user_id']
    except KeyError:
        return http.HttpResponseBadRequest()

    edx_courses = EdxCourse.objects.all()
    try:
        canvas_auth = CanvasApiAuthorization.objects.get(lti_user_id=canvas_user_id)
    except CanvasApiAuthorization.DoesNotExist:
        return canvas_api.start_oauth(request, canvas_user_id)

    try:
        canvas_courses = canvas_api.get_courses(canvas_auth)
        canvas_modules = canvas_api.get_module_list(canvas_auth, canvas_course_id)
    except CanvasAPIError as e:
        if e.status_code == 401:
            return canvas_api.start_oauth(request, canvas_user_id)
        raise
    return render(request, 'edx2canvas/index.html', {
        'edx_courses': edx_courses,
        'canvas_modules': json.dumps({'id': canvas_course_id, 'modules': canvas_modules})
    })


@login_required()
@require_http_methods(['GET'])
def get_canvas_modules(request):
    """
    Fetch the list of modules available in the Canvas course that launched the
    tool.

    Returns a JSON object with:
    - id: the Canvas course ID.
    - modules: a list of Canvas module objects.
    """
    try:
        canvas_course_id = request.GET['course_id']
        canvas_user_id = request.session['LTI_LAUNCH']['user_id']
    except KeyError:
        return http.HttpResponseBadRequest()
    try:
        canvas_auth = CanvasApiAuthorization.objects.get(lti_user_id=canvas_user_id)
    except CanvasApiAuthorization.DoesNotExist:
        return http.HttpResponseForbidden()
    module_list = canvas_api.get_module_list(canvas_auth, canvas_course_id)
    return http.JsonResponse(
        {'id': request.GET['course_id'], 'modules': module_list}, safe=False
    )


@login_required()
@require_http_methods(['GET'])
def get_edx_course(request):
    """
    Load and parse an edX course.

    Returns a JSON representation of the edX course structure. Note that this
    JSON object is a direct parsing of the edX course XML structure, and may
    change with little or no warning if the edX export format is modified.
    """
    try:
        course_id = request.GET['edx_course_id']
    except KeyError:
        return http.HttpResponseBadRequest()
    try:
        edx_course = EdxCourse.objects.get(id=course_id)
    except EdxCourse.DoesNotExist:
        return http.HttpResponseNotFound()
    try:
        with open("courses/{}.json".format(edx_course.course)) as infile:
            parsed = json.load(infile)
            return http.JsonResponse(parsed, safe=False)
    except IOError:
        return http.HttpResponseNotFound()
