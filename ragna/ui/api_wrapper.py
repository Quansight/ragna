import re
from datetime import datetime

import emoji

import requests


# The goal is this class is to provide ready-to-use functions to interact with the API
class ApiWrapper:
    def __init__(self, api_url, user):
        self.api_url = api_url
        self.user = user

    def get_chats(self):
        # Make a GET request to the API endpoint
        response = requests.get(self.api_url + "/chats?user=" + self.user)

        if response.status_code == 200:
            json_data = response.json()

            for chat in json_data:
                for msg in chat["messages"]:
                    # convert timestamps to datetime
                    msg["timestamp"] = datetime.strptime(
                        msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"
                    )

                    msg["content"] = self.replace_emoji_shortcodes_with_emoji(
                        msg["content"]
                    )

            return json_data
        else:
            # If the request was not successful, raise an exception
            raise Exception(
                f"API request failed with status code {response.status_code}"
            )

    def answer(self, chat_id, prompt):
        requests.post(
            f"{self.api_url}/chat/{chat_id}/start",
            params={"user": self.user},
        )
        raw_result = requests.post(
            f"{self.api_url}/chat/{chat_id}/answer",
            params={"user": self.user, "prompt": prompt},
        )

        return raw_result.json()["message"]["content"]

    def get_components(self):
        response = requests.get(self.api_url + "/components?user=" + self.user)
        return response.json()

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
