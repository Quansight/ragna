from typing import Union

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from . import _constants as constants
from ._session import Session, SessionDependency
from ._utils import redirect_response
from .schemas import User


def handle_page_output(page: Union[str, HTMLResponse]) -> HTMLResponse:
    if isinstance(page, str):
        page = HTMLResponse(page)

    return page


def make_router(config):
    router = APIRouter()

    auth = config.authentication()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page():
        # FIXME: async run
        return handle_page_output(auth.login_page())

    @router.post("/login")
    async def login(request: Request):
        result = auth.login(request)
        if not isinstance(result, User):
            # FIXME: async run
            return handle_page_output(auth.failed_login_page(result))

        request.state.session = Session(user=result)
        return redirect_response(constants.UI_PREFIX, htmx=request)

    @router.post("/logout")
    async def logout(request: Request):
        request.state.session = None
        return redirect_response(constants.UI_LOGIN_ENDPOINT, htmx=request)

    @router.get("/")
    async def main_page(session: SessionDependency):
        pass
