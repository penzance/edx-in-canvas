import json
import logging
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from ims_lti_py.tool_config import ToolConfig
import django.http as http
from models import CanvasApiAuthorization, EdxCourse
from canvas_sdk.exceptions import CanvasAPIError
import canvas_api
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.conf import settings
import os

TOOL_NAME = "edx2canvas"

log = logging.getLogger("edx2canvas.log")

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
        with open("courses/{}.json".format(course_id)) as infile:
            parsed = json.load(infile)
            parsed['id'] = course_id
            return http.JsonResponse(parsed, safe=False)
    except IOError:
        return http.HttpResponseNotFound()


@require_http_methods(['POST'])
def create_edx_course(request):
    try:
        data = json.loads(request.body)
        title = data['title']
        org = data['org']
        course = data['course']
        run = data['run']
        key_version = data['key_version']
        body = json.loads(data['body'])

        edx_course, __ = EdxCourse.objects.get_or_create(
            title=title,
            org=org,
            course=course,
            run=run,
            key_version=key_version
        )

        output_filename = '%s.json' % edx_course.id
        output = json.dumps(body, indent=4)

        utf8_output = output.encode('utf-8')
        courses_bucket_name = getattr(settings, 'COURSES_BUCKET', None)
        if courses_bucket_name:
            # get the bucket
            log.info("writing file to s3")
            conn = S3Connection()
            courses_bucket = conn.get_bucket(courses_bucket_name)
            path = getattr(settings, 'COURSES_FOLDER', None)
            full_key_name = os.path.join(path, output_filename)
            log.info(full_key_name)
            k = Key(courses_bucket)
            k.key = full_key_name
            k.content_type = 'text/html'
            k.content_encoding = 'UTF-8'
            k.set_contents_from_string(utf8_output)
            k.close()

        else:
            log.info("writing file locally")
            outfile = open(output_filename, 'w+')
            outfile.write(utf8_output)
            outfile.close()

    except Exception as e:
        log.info("{}".format(e))
        return http.HttpResponseBadRequest()
    return HttpResponse(status=201)
