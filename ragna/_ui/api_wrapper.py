import re
from datetime import datetime

import emoji
import httpx
import param


# The goal is this class is to provide ready-to-use functions to interact with the API
class ApiWrapper(param.Parameterized):
    auth_token = param.String(default=None)

    def __init__(self, api_url, **params):
        # FIXME: this should be an async client
        self.client = httpx.Client(base_url=api_url)

        super().__init__(**params)

        self.client.get("/").raise_for_status()

    async def auth(self, username, password):
        async with httpx.AsyncClient(
            base_url=self.client.base_url, headers=self.client.headers
        ) as async_client:
            self.auth_token = (
                (
                    await async_client.post(
                        "/token",
                        data={"username": username, "password": password},
                    )
                )
                .raise_for_status()
                .json()
            )

            return True

    @param.depends("auth_token", watch=True)
    def update_auth_header(self):
        self.client.headers["Authorization"] = f"Bearer {self.auth_token}"

    def get_chats(self):
        json_data = self.client.get("/chats").raise_for_status().json()

        for chat in json_data:
            chat["messages"] = [self.improve_message(msg) for msg in chat["messages"]]

        return json_data

    def answer(self, chat_id, prompt):
        json_data = (
            self.client.post(
                f"/chats/{chat_id}/answer", params={"prompt": prompt}, timeout=None
            )
            .raise_for_status()
            .json()
        )

        json_data["message"] = self.improve_message(json_data["message"])
        json_data["chat"]["messages"] = [
            self.improve_message(msg) for msg in json_data["chat"]["messages"]
        ]

        return json_data

    async def get_components_async(self):
        async with httpx.AsyncClient(
            base_url=self.client.base_url, headers=self.client.headers
        ) as async_client:
            return (await async_client.get("/components")).raise_for_status().json()

    # Upload and related functions
    def upload_endpoints(self):
        return {
            "informations_endpoint": f"{self.client.base_url}/document",
        }

    def start_chat(self, name, documents, source_storage, assistant, params={}):
        return (
            self.client.post(
                "/chats",
                json={
                    "name": name,
                    "documents": documents,
                    "source_storage": source_storage,
                    "assistant": assistant,
                    "params": params,
                },
            )
            .raise_for_status()
            .json()
        )

    def start_and_prepare(self, name, documents, source_storage, assistant, params={}):
        chat = self.start_chat(name, documents, source_storage, assistant, params)

        _ = self.client.post(
            f"/chats/{chat['id']}/prepare", timeout=None
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
