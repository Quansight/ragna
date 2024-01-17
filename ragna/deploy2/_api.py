from fastapi import APIRouter


def make_router(auth):
    router = APIRouter()

    @router.post("/token", response_class=HTMLResponse)
    async def token():
        # FIXME: async run
        return handle_page_output(auth.login_page())
