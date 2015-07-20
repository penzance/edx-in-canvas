from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_http_methods

from models import CanvasApiAuthorization, EdxCourse
import canvas_api

@login_required
@require_http_methods(['POST'])
def add_to_canvas(request):
    """
    Create a new module item in Canvas that launches one piece of edX content.
    There are two possibilities:
     - For a graded exercise (where 'graded' is 'true'), a new Canvas assignment
       is created (worth one point), and a module item is created that points to
       the new assignment.
     - For a non-graded piece of content (when 'graded' is 'false'), a new
       module item is created that launches the content directly.
    In both cases, if the Open edX LTI tool is not installed on the course, it
    is created. Any subsequently-created items will use that external tool (i.e.
    there will only be one instance of the Open edX LTI tool installed).

    The method expects the following POST parameters:
     - edx_course_id: an ID into the EdxCourse model.
     - canvas_course_id: a Canvas-defined course identifier.
     - module_id: a Canvas-defined module identifier.
     - title: the title for the new module item (and assignment, if necessary).
     - position: the zero-based index of the new item in the module list.
     - usage_id: an edX-defined identifier for the content to import.
     - graded: 'true' if an assignment should be created, 'false' if not.
    """
    try:
        edx_course_id = request.POST['edx_course_id']
        canvas_course_id = request.POST['canvas_course_id']
        module_id = request.POST['module_id']
        title = request.POST['title']
        position = request.POST['position']
        usage_id = request.POST['usage_id']
        graded = request.POST['graded'].lower() not in ('false', '0')
        points = request.POST['points']
        canvas_user_id = request.session['LTI_LAUNCH']['user_id']
    except KeyError:
        return HttpResponseBadRequest()

    try:
        edx_course = EdxCourse.objects.get(id=edx_course_id)
    except EdxCourse.DoesNotExist:
        return HttpResponseBadRequest()
    edx_course_key = edx_course.course_key()

    try:
        canvas_auth = CanvasApiAuthorization.objects.get(lti_user_id=canvas_user_id)
    except CanvasApiAuthorization.DoesNotExist:
        return HttpResponseForbidden()

    external_tool_id = canvas_api.get_external_tool_id(canvas_auth, canvas_course_id)

    if graded:
        canvas_api.create_assignment_with_module_item(
            canvas_auth, title, canvas_course_id, module_id, position,
            external_tool_id, get_lti_url_for_usage_id(edx_course_key, usage_id),
            points
        )
    else:
        canvas_api.create_canvas_module_item(
            canvas_auth, title, canvas_course_id, module_id, position,
            external_tool_id, get_lti_url_for_usage_id(edx_course_key, usage_id)
        )

    module_list = canvas_api.get_module_list(canvas_auth, canvas_course_id)
    return JsonResponse({'id': canvas_course_id, 'modules': module_list}, safe=False)

@login_required
@require_http_methods(['POST'])
def create_canvas_module(request):
    """
    Create a new module in a Canvas course.

    This method expects the following POST parameters:
    - 'canvas_course_id': The ID of the course in which to create the module.
      The currently-authenticated user must have write access to the course.
    - 'module_name': A name to give to the newly-created module.
    - 'position': A zero-based index into the module list, indicating where to
      insert the new module.
    """
    try:
        canvas_course_id = request.POST['canvas_course_id']
        name = request.POST['module_name']
        position = request.POST['position']
        canvas_user_id = request.session['LTI_LAUNCH']['user_id']
    except KeyError:
        return HttpResponseBadRequest()

    try:
        canvas_auth = CanvasApiAuthorization.objects.get(lti_user_id=canvas_user_id)
    except CanvasApiAuthorization.DoesNotExist:
        return HttpResponseForbidden()
    module = canvas_api.create_canvas_module(
        canvas_auth, canvas_course_id, name, position
    )
    module_list = canvas_api.get_module_list(canvas_auth, canvas_course_id)
    return JsonResponse({'module_id': module['id'], 'modules': module_list}, safe=False)

def get_lti_url_for_usage_id(edx_course_key, usage_id):
    return "{}/lti_provider/courses/{}/{}".format(
        settings.EDX_URL_BASE, edx_course_key, usage_id
    )
