from fastapi import APIRouter
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from ._utils import redirect_response


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
