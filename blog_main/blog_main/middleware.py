from django.http import JsonResponse


class HealthCheckMiddleware:
    """Answer internal readiness probes without evaluating their Host header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and request.path_info == "/healthz/":
            return JsonResponse({"status": "ok", "service": "zaratech-blog"})

        return self.get_response(request)
