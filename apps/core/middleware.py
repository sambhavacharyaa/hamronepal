from django.conf import settings

NOINDEX_PATH_PREFIXES = (
    "/accounts/",
    "/dashboard/",
    "/tasks/",
    "/tourism/trips/",
    "/tourism/saved/",
)


class RobotsHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        for code, _label in settings.LANGUAGES:
            prefix = f"/{code}/"
            if path.startswith(prefix):
                path = path[len(prefix) - 1 :]
                break
        if path.startswith(NOINDEX_PATH_PREFIXES):
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
