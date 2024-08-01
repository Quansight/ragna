import json
import random

import sse_starlette
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.get("/health")
async def health():
    return Response(b"", status_code=status.HTTP_200_OK)


@app.post("/sse")
async def sse(request: Request):
    data = await request.json()

    async def stream():
        for obj in data:
            yield sse_starlette.ServerSentEvent(json.dumps(obj))

    return sse_starlette.EventSourceResponse(stream())


@app.post("/jsonl")
async def jsonl(request: Request):
    data = await request.json()

    async def stream():
        for obj in data:
            yield f"{json.dumps(obj)}\n"

    return StreamingResponse(stream())


@app.post("/json")
async def json_(request: Request):
    data = await request.body()

    async def stream():
        start = 0
        while start < len(data):
            end = start + random.randint(1, 10)
            yield data[start:end]
            start = end

    return StreamingResponse(stream())
