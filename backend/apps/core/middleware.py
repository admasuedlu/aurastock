import threading

_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, "user", None)


class CurrentUserMiddleware:
    """Stashes the authenticated user in thread-local storage so audit
    fields (created_by, updated_by) can be set from model signals without
    threading `request` through every service function."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        try:
            return self.get_response(request)
        finally:
            _thread_locals.user = None
