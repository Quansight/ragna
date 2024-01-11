import uuid

from starlette.middleware.base import BaseHTTPMiddleware


class Middleware(BaseHTTPMiddleware):
    ONE_WEEK = 60 * 60 * 24 * 7

    def __init__(self, app, cookie_name: str = "Ragna"):
        super().__init__(app)
        # TODO: allow this to also be redis
        self.sessions = {}
        self.cookie_name = cookie_name

    async def dispatch(self, request, call_next):
        session_id = request.cookies.get(self.cookie_name, uuid.uuid4().hex)
        request.state.session = self.sessions.setdefault(
            session_id, schema.SessionData()
        )
        response = await call_next(request)
        response.set_cookie(
            key=self.cookie_name,
            value=session_id,
            httponly=True,
            samesite="strict",
            expires=self.ONE_WEEK,
        )
        return response


@app.post("/token")
async def create_token(request: Request) -> str:
    return await authentication.create_token(request)


UserDependency = Annotated[str, Depends(authentication.get_user)]
