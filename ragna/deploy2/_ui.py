from fastapi import APIRouter, Request

from . import _constants as constants
from ._session import Session
from ._utils import redirect_response


def make_router(auth):
    router = APIRouter()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        # FIXME: async run
        return auth.login_page()

    @router.post("/login")
    async def login(request: Request):
        user = auth.login(request)
        if user:
            request.state.session = Session(user=user)
        # we only define the happy path here. if the login request comes back without a session,
        # the middleware handles the redirect to the login page
        return redirect_response(constants.UI_PREFIX)


# def add_auth(app, *, auth: Auth, prefix: str):
#     @app.get(f"{prefix}/login")
#     async def login() -> Response:
#         return auth.login_page()
#
#     @app.post(f"{prefix}/login")
#     async def login(request: Request):
#         user_data = auth.login(request)
#         # put it into the session
#         return redirect_response(prefix, status_code=303)
