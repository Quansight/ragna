from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ragna._utils import as_awaitable

from ._session import Session, SessionDependency
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
        return redirect_response("/ui", htmx=request)

    @router.post("/login")
    async def login(request: Request):
        return await _login(request)

    @router.get("/oauth-callback")
    async def oauth_callback(request: Request):
        return await _login(request)

    @router.post("/logout")
    async def logout(request: Request):
        request.state.session = None
        return redirect_response("/ui/login", htmx=request)

    @router.get("/")
    async def main_page(session: SessionDependency):
        return HTMLResponse(f"Hello {session.user.username}!")

    return router
