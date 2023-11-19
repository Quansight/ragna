import re
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
        self.client = httpx.AsyncClient(base_url=api_url)

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

    async def answer(self, chat_id, prompt):
        json_data = (
            (
                await self.client.post(
                    f"/chats/{chat_id}/answer",
                    params={"prompt": prompt},
                    timeout=None,
                )
            )
            .raise_for_status()
            .json()
        )

        json_data["message"] = self.improve_message(json_data["message"])
        json_data["chat"]["messages"] = [
            self.improve_message(msg) for msg in json_data["chat"]["messages"]
        ]

        return json_data

    async def get_components(self):
        return (await self.client.get("/components")).raise_for_status().json()

    # Upload and related functions
    def upload_endpoints(self):
        return {
            "informations_endpoint": f"{self.client.base_url}/document",
        }

    async def start_chat(self, name, documents, source_storage, assistant, params={}):
        return (
            (
                await self.client.post(
                    "/chats",
                    json={
                        "name": name,
                        "documents": documents,
                        "source_storage": source_storage,
                        "assistant": assistant,
                        "params": params,
                    },
                )
            )
            .raise_for_status()
            .json()
        )

    async def start_and_prepare(
        self, name, documents, source_storage, assistant, params={}
    ):
        chat = await self.start_chat(name, documents, source_storage, assistant, params)

        (
            await self.client.post(f"/chats/{chat['id']}/prepare", timeout=None)
        ).raise_for_status()

        return chat["id"]

    # Helpers

    def improve_message(self, msg):
        # convert timestamps to datetime

        msg["timestamp"] = datetime.strptime(msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")

        msg["content"] = self.replace_emoji_shortcodes_with_emoji(msg["content"])

        return msg

    def replace_emoji_shortcodes_with_emoji(self, markdown_string):
        # Define a regular expression pattern to find emoji shortcodes
        shortcode_pattern = r":\w+:"

        # Find all matches of emoji shortcodes in the input string
        shortcodes = re.findall(shortcode_pattern, markdown_string)

        # Iterate through the found shortcodes and replace them with emojis
        for shortcode in shortcodes:
            emoji_name = shortcode.strip(":")
            emoji_unicode = emoji.emojize(f":{emoji_name}:", language="alias")
            markdown_string = markdown_string.replace(shortcode, emoji_unicode)

        return markdown_string
