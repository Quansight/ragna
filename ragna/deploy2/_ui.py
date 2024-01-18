from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse

from ragna._utils import as_awaitable

from ._session import Session, SessionDependency
from ._templates import TemplateResponse
from ._utils import redirect_response
from .schemas import User


def make_router(config):
    router = APIRouter()

    auth = config.authentication()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        return await as_awaitable(auth.login_page, request)

    async def _login(request: Request):
        result = await as_awaitable(auth.login, request)
        if not isinstance(result, User):
            return result

        request.state.session = Session(user=result)
        return redirect_response(
            "/ui", htmx=request, status_code=status.HTTP_303_SEE_OTHER
        )

    @router.post("/login")
    async def login(request: Request):
        return await _login(request)

    @router.get("/oauth-callback")
    async def oauth_callback(request: Request):
        return await _login(request)

    @router.post("/logout")
    async def logout(request: Request):
        request.state.session = None
        return redirect_response(
            "/ui/login", htmx=request, status_code=status.HTTP_303_SEE_OTHER
        )

    @router.get("")
    async def main_page(request: Request, session: SessionDependency):
        return TemplateResponse(
            name="main.html",
            context={"request": request, "user": session.user},
        )

    return router
