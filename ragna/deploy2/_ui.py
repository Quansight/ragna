from fastapi import APIRouter, Request

from . import _constants as constants
from ._session import Session
from ._utils import redirect_response
from .schemas import User


def make_router(auth):
    router = APIRouter()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        # FIXME: async run
        return auth.login_page()

    @router.post("/login")
    async def login(request: Request):
        result = auth.login(request)
        if not isinstance(result, User):
            return auth.failed_login_page(result)

        request.state.session = Session(user=result)
        return redirect_response(constants.UI_PREFIX)

    @router.post("/logout")
    async def logout(request: Request):
        request.state.session = None
        return redirect_response(constants.UI_LOGIN_ENDPOINT)


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
