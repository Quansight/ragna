from fastapi import APIRouter
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from ._utils import redirect_response


class SessionMiddleware(BaseHTTPMiddleware):
    _COOKIE_NAME = "Ragna"
    _ONE_WEEK = 60 * 60 * 24 * 7

    def __init__(self, app):
        super().__init__(app)
        self._sessions = {}

    def _add_session(self, response: Response, session_id: str, session):
        self._sessions[session_id] = session
        response.set_cookie(
            key=self._COOKIE_NAME,
            value=session_id,
            expires=self._ONE_WEEK,
            httponly=True,
            samesite="strict",
        )

    def _delete_session(
        self, response: Response, session_id: Optional[str] = None
    ) -> None:
        if session_id:
            del self._sessions[session_id]
        response.delete_cookie(key=self._COOKIE_NAME, httponly=True, samesite="strict")

    def _redirect_to_login(self, request: Request):
        return redirect_response("/login", htmx=request, status_code=303)

    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get(self._COOKIE_NAME)

        if session_id is None:
            if not request.url.path == "/login":
                return redirect_response("/login", htmx=request, status_code=303)

            session_id = str(uuid.uuid4())
        elif session_id not in self._sessions:
            response = self._redirect_to_login(request)
            self._delete_session(response)
            return response

        request.state.session = self._sessions.setdefault(session_id, None)

        response = await call_next(request)
        session = request.state.session

        if session is not None:
            self._add_session(response, session_id, session)
        else:
            self._delete_session(response, session_id)

        return response

def make_router():
    router = APIRouter()

    router.add_middleware(SessionMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=handle_localhost_origins(config.api.origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/login", response_class=HTMLResponse)
        async def login(request: Request):
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"session": request.state.session},
            )

        @app.post("/login")
        async def login(request: Request):
            form = await request.form()
            username = form.get("username")
            if not username:
                return HTMLResponse("No username provided! Try again.")

            request.state.session = schema.SessionData(username=username)

            return HTMLResponse("", headers={"HX-Redirect": "/"}, status_code=303)

        @app.post("/logout")
        def logout(request: Request):
            request.state.session = None
            return RedirectResponse(url="/", status_code=303)



def add_middleware()
