from django.conf import settings
from django.contrib.auth.decorators import login_required
import django.http as http
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from oauthlib.oauth1 import Client
import urllib

from models import EdxCourse

@login_required()
@require_http_methods(['GET'])
def launch_lti_preview(request):
    """
    Generate a page that performs an LTI launch for the required edX content.
    """
    try:
        usage_key = request.GET['usage_id']
        course_id = request.GET['course_id']
    except KeyError:
        return http.HttpResponseBadRequest()
    try:
        course = EdxCourse.objects.get(id=course_id)
    except EdxCourse.DoesNotExist:
        return http.HttpResponseNotFound()
    context = get_lti_context(course, usage_key)
    return render(request, 'edx2canvas/lti_launch.html', context)

def get_lti_context(course, usage_key):
    """
    Generate the context for the LTI preview launch page

    Returns a dict containing the necessary LTI launch fields
    """
    lti_settings = settings.EDX_LTI_PREVIEW_SETTINGS
    lti_url = "{}/{}/{}".format(lti_settings['url_base'], course.course_key(), usage_key)
    body = {
        'tool_consumer_instance_guid': lti_settings['tool_consumer_instance_guid'],
        'user_id': lti_settings['user_id'],
        'roles': lti_settings['roles'],
        'context_id': lti_settings['context_id'],
        'lti_version': lti_settings['lti_version'],
    }
    key = lti_settings['key']
    secret = lti_settings['secret']
    _sign_lti_message(body, key, secret, lti_url)
    return dict(
        lti_url=lti_url,

        oauth_consumer_key=key,
        tool_consumer_instance_guid=body['tool_consumer_instance_guid'],
        user_id=body['user_id'],
        roles=body['roles'],
        context_id=body['context_id'],
        lti_version=body['lti_version'],

        oauth_timestamp=body['oauth_timestamp'],
        oauth_nonce=body['oauth_nonce'],
        oauth_signature=urllib.unquote(body['oauth_signature']).decode('utf8'),
        oauth_signature_method=body['oauth_signature_method'],
        oauth_version=body['oauth_version'],
    )


def _sign_lti_message(body, key, secret, url):
    client = Client(
        client_key=key,
        client_secret=secret
    )

    __, headers, __ = client.sign(
        unicode(url),
        http_method=u'POST',
        body=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )

    auth_header = headers['Authorization'][len('OAuth '):]
    auth = dict([param.strip().replace('"', '').split('=') for param in auth_header.split(',')])

    body['oauth_nonce'] = auth['oauth_nonce']
    body['oauth_signature'] = auth['oauth_signature']
    body['oauth_timestamp'] = auth['oauth_timestamp']
    body['oauth_signature_method'] = auth['oauth_signature_method']
    body['oauth_version'] = auth['oauth_version']

