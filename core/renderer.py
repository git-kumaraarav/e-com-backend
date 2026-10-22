from rest_framework.renderers import JSONRenderer
from rest_framework import status

class CoreRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):

        if renderer_context is None: 
            return super().render(data, accepted_media_type, renderer_context) 

        status_code = renderer_context["response"].status_code
        is_success = status.is_success(status_code)

        response_data = {
            "status": is_success,
            "status_code": status_code,
            "timestamp": renderer_context["response"].headers.get("Date"),
        }

        if is_success:
            response_data["data"] = data
        else:
            response_data["error"] = data

        return super().render(response_data, accepted_media_type, renderer_context)
