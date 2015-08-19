Configuration

The tricky part of configuring the tool centers around OAuth credentials. This is an LTI provider that previews content
using a built-in LTI consumer, and then configures Canvas (a separate LTI consumer) to make calls to edX (an LTI
provider). As such, there are several different sets of credentials that need to be kept straight in the secure.py
file:
* The user launches this tool using LTI. The 'lti_oauth_credentials' field in secure.py contains the key and secret
that an admin must use to connect this tool to Canvas.
* The first thing that the tool does is connect back to the Canvas server in order to obtain an API token to make calls
on the user's behalf. This requires executing the Canvas OAuth2 Token Request Flow (from
https://canvas.instructure.com/doc/api/file.oauth.html). The 'canvas_oauth_client_id' and 'canvas_oauth_client_key'
fields in secure.py contain the app ID and key obtained from the Canvas site administrator (normally Instructure).
* When a user selects some edX content, the tool brings up a preview of that content in the central iframe. This is
implemented using an LTI call to the edX LTI provider. To make this call, we need four fields in secure.py:
** 'preview_tool_consumer_guid': a globally-unique identifier for this installation of the edx-in-canvas LTI provider
** 'preview_user_id': a user identifier for the LTI launch. Since the consumer_guid is globally unique, this value can
be anything. You may want to make it distinctive in order to recognize it in server logs if necessary.
** 'edx_lti_preview_key': an LTI key for the preview consumer. This key must be in the edX LTI provider database.
** 'edx_lti_preview_secret': a matching secret for the LTI key. This must also be in the edX LTI provider database.
* Finally, the tool uses the Canvas API creates new external tool assignments and module items in the Canvas course.
It automatically creates the External Tool app at the Canvas course scope. To do this, it requires the LTI key and
secret that Canvas will use to launch LTI content (it is recommended that this is different from the preview consumer's
key and secret. These values are stored in 'edx_lti_provider_key' and 'edx_lti_provider_secret'.

Course Structures

Since there is currently no edX course API, we need to work out the course structure and content identifiers outselves.
Starting with the .tgz file generated by the edX course export feature, we use the bin/parse_course.py script to
generate a summary of the course structure and upload it to the edx-in-canvas tool. Once a course has been parsed,
it will be available in the edX content menu on the top left of the app display.