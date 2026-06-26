from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class ForceCORSAlwaysMiddleware(BaseHTTPMiddleware):
    """Ensures CORS headers exist on *all* responses.

    Some runtime failures (e.g., exceptions handled outside Starlette's normal
    CORSMiddleware path) can yield responses without CORS headers.
    This middleware makes CORS headers explicit so browsers can read the body.
    """

    async def dispatch(self, request, call_next: Callable):
        response: Response = await call_next(request)

        # Mirror the app's local-dev permissive CORS policy.
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault("Access-Control-Allow-Methods", "*")
        response.headers.setdefault("Access-Control-Allow-Headers", "*")
        return response

