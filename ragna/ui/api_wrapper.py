import os
import re
from datetime import datetime

import emoji

import httpx


# The goal is this class is to provide ready-to-use functions to interact with the API
class ApiWrapper:
    def __init__(self, api_url):
        # FIXME: this should be an async client
        self.client = httpx.Client(base_url=api_url)
        self.client.get("/").raise_for_status()

        # FIXME: the token should come from a cookie that is set after UI login
        from ragna.core._rag import default_user  # noqa

        user = default_user()
        token = (
            self.client.post(
                "/token",
                data={
                    "username": user,
                    "password": os.environ.get(
                        "AI_PROXY_DEMO_AUTHENTICATION_PASSWORD", user
                    ),
                },
            )
            .raise_for_status()
            .json()
        )
        # FIXME: remove this as it should come from a cookie on the JS side as well
        self.token = token
        self.client.headers["Authorization"] = f"Bearer {token}"

    async def auth(self, username, password):
        async with httpx.AsyncClient(
            base_url=self.client.base_url, headers=self.client.headers
        ) as async_client:
            self.token = (
                (
                    await async_client.post(
                        "/token",
                        data={"username": username, "password": password},
                    )
                )
                .raise_for_status()
                .json()
            )

            self.client.headers["Authorization"] = f"Bearer {self.token}"

            print("token : ", self.token)

            return True

    def get_chats(self):
        json_data = self.client.get("/chats").raise_for_status().json()

        for chat in json_data:
            chat["messages"] = [self.improve_message(msg) for msg in chat["messages"]]

        return json_data

    def answer(self, chat_id, prompt):
        json_data = (
            self.client.post(f"/chats/{chat_id}/answer", params={"prompt": prompt})
            .raise_for_status()
            .json()
        )

        json_data["message"]["content"] = self.improve_message(
            json_data["message"]["content"]
        )
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
        print("start_chat", self.client.headers)
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

        _ = self.client.post(f"/chats/{chat['id']}/prepare")

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
