"""
Shared authentication helper for core/api/ views (JSON responses and file
downloads alike).
"""

from __future__ import annotations

from functools import wraps

from django.http import JsonResponse


def login_required_json(view_func):
    """
    Like django.contrib.auth.decorators.login_required, but returns a
    JSON 401 instead of redirecting to an HTML login page — appropriate
    for any core/api/ response, whether it returns JSON or a downloadable
    file (CSV/PDF/JSON export).
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapped
