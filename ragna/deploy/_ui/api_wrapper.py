import json
from datetime import datetime

import emoji
import httpx
import param


class RagnaAuthTokenExpiredException(Exception):
    """Just a wrapper around Exception"""

    pass


# The goal is this class is to provide ready-to-use functions to interact with the API
class ApiWrapper(param.Parameterized):
    auth_token = param.String(default=None)

    def __init__(self, api_url, **params):
        self.client = httpx.AsyncClient(base_url=api_url, timeout=60)

        super().__init__(**params)

        try:
            # If no auth token is provided, we use the API base URL and only test the API is up.
            # else, we test the API is up *and* the token is valid.
            endpoint = (
                api_url + "/components" if self.auth_token is not None else api_url
            )
            httpx.get(
                endpoint, headers={"Authorization": f"Bearer {self.auth_token}"}
            ).raise_for_status()

        except httpx.HTTPStatusError as e:
            # unauthorized - the token is invalid
            if e.response.status_code == 401:
                raise RagnaAuthTokenExpiredException("Unauthorized")
            else:
                raise e

    async def auth(self, username, password):
        self.auth_token = (
            (
                await self.client.post(
                    "/token",
                    data={"username": username, "password": password},
                )
            )
            .raise_for_status()
            .json()
        )

        return True

    @param.depends("auth_token", watch=True, on_init=True)
    def update_auth_header(self):
        self.client.headers["Authorization"] = f"Bearer {self.auth_token}"

    async def get_chats(self):
        json_data = (await self.client.get("/chats")).raise_for_status().json()
        for chat in json_data:
            chat["messages"] = [self.improve_message(msg) for msg in chat["messages"]]
        return json_data

    def create_document_content_js(self, document_id, document_name, page_numbers):
        anchor = page_numbers[0] if page_numbers else ""
        return f"""
              fetch(
                "{self.client.base_url}/documents/{document_id}/content",
                {{ headers: {{"Authorization": "Bearer {self.auth_token}"}} }}
              ).then((response) => {{
                  return response.blob().then((blob) => {{
                      return {{
                        blob: blob,
                        headers: response.headers,
                      }};
                   }});
              }}).then(({{ blob, headers }}) => {{
                  var mimetype = headers.get("content-type"); 
                  var file = new File([blob], "{document_id}", {{ type: mimetype }});
                  var _url = window.URL.createObjectURL(file);
                  window.open(_url + "#{anchor}", "_blank").focus();
              }}).catch((err) => {{
                console.log(err);
              }});
        """

    async def answer(self, chat_id, prompt):
        async with self.client.stream(
            "POST",
            f"/chats/{chat_id}/answer",
            json={"prompt": prompt, "stream": True},
        ) as response:
            async for data in response.aiter_lines():
                yield self.improve_message(json.loads(data))

    async def get_components(self):
        return (await self.client.get("/components")).raise_for_status().json()

    # Upload and related functions
    def upload_endpoints(self):
        return {
            "informations_endpoint": f"{self.client.base_url}/document",
        }

    async def start_and_prepare(
        self, name, documents, source_storage, assistant, params
    ):
        response = await self.client.post(
            "/chats",
            json={
                "name": name,
                "input": documents,
                "source_storage": source_storage,
                "assistant": assistant,
                "params": params,
            },
        )
        chat = response.raise_for_status().json()

        response = await self.client.post(f"/chats/{chat['id']}/prepare", timeout=None)
        response.raise_for_status()

        return chat["id"]

    def improve_message(self, msg):
        msg["timestamp"] = datetime.strptime(msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
        msg["content"] = emoji.emojize(msg["content"], language="alias")
        return msg
