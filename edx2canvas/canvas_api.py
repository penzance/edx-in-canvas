import json
import requests

from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.shortcuts import (render, redirect)
from django.conf import settings

from canvas_sdk.methods import assignments, courses, modules, external_tools
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
from models import CanvasApiAuthorization

@require_http_methods(['GET'])
def start_oauth(request, canvas_user_id):
    redirect_url = request.build_absolute_uri(reverse('edx2canvas:oauth_redirect'))
    context = {
        'redirect_url': redirect_url,
        'state': canvas_user_id,
        'oauth_url': '{}/login/oauth2/auth'.format(settings.CANVAS_DOMAIN),
        'client_id': settings.CANVAS_OAUTH_CLIENT_ID,
    }
    return render(request, 'edx2canvas/start_oauth.html', context)

@require_http_methods(['GET'])
def oauth_redirect(request):
    code = request.GET['code']
    state = request.GET['state']
    data = {
        'client_id': settings.CANVAS_OAUTH_CLIENT_ID,
        'redirect_uri': request.build_absolute_uri(reverse('edx2canvas:oauth_redirect')),
        'client_secret': settings.CANVAS_OAUTH_CLIENT_KEY,
        'code': code
    }
    url = '{}/login/oauth2/token'.format(settings.CANVAS_DOMAIN)
    headers = {
        'Content-Type': 'application/json',
    }
    response = requests.post(url, json.dumps(data), headers=headers)
    token = response.json().get('access_token', None)

    auth, created = CanvasApiAuthorization.objects.get_or_create(lti_user_id=state)
    auth.canvas_api_token = token
    auth.save()

    return redirect('edx2canvas:main')

def get_courses(api_auth):
    context = _get_context(api_auth)
    get_all_list_data(context, courses.list_your_courses, 'term')

def get_module_list(api_token, canvas_course_id):
    context = _get_context(api_token)
    return get_all_list_data(context, modules.list_modules, canvas_course_id, 'items')

def get_external_tool_id(api_auth, canvas_course_id):
    context = _get_context(api_auth)
    tools = get_all_list_data(context, external_tools.list_external_tools_courses, canvas_course_id)
    domain = settings.EXTERNAL_TOOL_DOMAIN
    tool_id = next((x['id'] for x in tools if x.get('domain', None) == domain), None)
    if not tool_id:
        tool = external_tools.create_external_tool_courses(
            context, canvas_course_id, 'Open edX at Harvard', 'anonymous',
            settings.EDX_LTI_KEY, settings.EDX_LTI_SECRET, domain=domain
        )
        tool_id = tool.json().get('id', None)

    return tool_id

def create_canvas_module(api_auth, canvas_course_id, module_name, position):
    context = _get_context(api_auth)
    response = modules.create_module(context, canvas_course_id, module_name, module_position=position)
    return response.json()

def create_canvas_module_item(
        api_auth, title, canvas_course_id,
        module_id, position, external_tool_id, external_url
):
    context = _get_context(api_auth)
    modules.create_module_item(
        context, canvas_course_id, module_id, 'ExternalTool', external_tool_id,
        module_item_external_url=external_url, module_item_title=title,
        module_item_position=position
    )

def create_assignment_with_module_item(
        api_auth, title, canvas_course_id,
        module_id, position, external_tool_id, external_url
):
    context = _get_context(api_auth)
    response = assignments.create_assignment(
        context, canvas_course_id, title, 'external_tool',
        assignment_external_tool_tag_attributes={'url': external_url},
        assignment_integration_id=external_tool_id,
        assignment_points_possible=1
    )
    assignment_id = response.json()['id']

    modules.create_module_item(
        context, canvas_course_id, module_id, 'Assignment', assignment_id,
        module_item_title=title, module_item_position=position
    )

def _get_context(api_auth):
    api_config = settings.CANVAS_SDK_SETTINGS.copy()
    api_config['auth_token'] = api_auth.canvas_api_token
    return RequestContext(**api_config)
