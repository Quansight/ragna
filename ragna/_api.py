from fastapi import FastAPI, Request
from pydantic import BaseModel


class Input(BaseModel):
    prompt: str
    sources: list[str]


app = FastAPI()

import contextlib


class Rag:
    pass


@contextlib.contextmanager
def lifespan(app):
    yield {"rag": Rag()}


@app.post("/upload-document")
async def upload_document(request: Request):
    rag = request.state.rag
    rag.upload_document()
    print(f"{request._receive = }")
    async for foo in request.stream():
        print(len(foo))
        print("#" * 100)


@app.post("/start-chat")
def start_chat(request: Request):
    rag = request.state.rag
    rag.start_chat(document_ids, **chat_config)


@app.get("/answer")
def answer(request: Request, prompt: str, chat_id: str):
    rag = request.state.rag
    return rag.answer(prompt, chat_id=chat_id)


if __name__ == "__main__":
    import uvicorn
    import uvicorn.protocols.http.httptools_impl

    uvicorn.run(app)
