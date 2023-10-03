from datetime import datetime

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

            # convert timestamps to datetime
            # for idx_chat in range(len(json_data)):
            for chat in json_data:
                # for msg in json_data[idx_chat]['messages']:
                for msg in chat["messages"]:
                    msg["timestamp"] = datetime.strptime(
                        msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"
                    )

            return json_data
        else:
            # If the request was not successful, raise an exception
            raise Exception(
                f"API request failed with status code {response.status_code}"
            )

    def answer(self, chat_id, user, prompt):
        requests.post(
            f"{self.api_url}/chat/{chat_id}/start",
            params={"user": user},
        )
        raw_result = requests.post(
            f"{self.api_url}/chat/{chat_id}/answer",
            params={"user": user, "prompt": prompt},
        )

        return raw_result.json()["message"]["content"]
