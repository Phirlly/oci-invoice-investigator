"""Keep database throttling without retaining login query or form bodies."""

from axes.handlers.database import AxesDatabaseHandler
from django.http import QueryDict


class PrivateLoginAttempts(AxesDatabaseHandler):
    def user_login_failed(self, sender, credentials, request=None, **kwargs):
        if request is None:
            return super().user_login_failed(sender, credentials, request, **kwargs)
        original_get, original_post = request.GET, request.POST
        try:
            # Username is already in credentials. Preserve Axes' attributes on the
            # original request so middleware still produces the lockout response.
            request.GET = QueryDict()
            request.POST = QueryDict()
            return super().user_login_failed(sender, credentials, request, **kwargs)
        finally:
            request.GET, request.POST = original_get, original_post
