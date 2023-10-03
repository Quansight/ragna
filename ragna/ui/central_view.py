from pprint import pprint

import panel as pn
import param


class CentralView(pn.viewable.Viewer):
    current_chat = param.ClassSelector(class_=dict, default=None)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.api_wrapper = api_wrapper

    def set_current_chat(self, chat):
        print("set current chat", chat["id"])
        self.current_chat = chat

    def custom_chat_entry(self, value):
        return pn.pane.HTML(
            f"""
                     <div style='background-color:red;'>{value}</div>
                     
                     """
        )

    @pn.depends("current_chat", watch=True)
    def chat_interface(self):
        print("chat interface", self.current_chat["id"])
        pprint(self.current_chat)

        ragna_stylesheet = """
                            :host {
                                
                            }
                                """

        user_stylesheet = """
                    :host {
                            flex-direction:row-reverse;
                            }

                    .right {
                            width:fit-content;
                    }
                    """

        chat_entries = []

        for m in self.current_chat["messages"]:
            chat_entry = pn.widgets.ChatEntry(
                value=m["content"],
                user="Pierrot" if m["role"] == "user" else "Ragna",
                timestamp=m["timestamp"],
                show_reaction_icons=False,
                # show_user=False,
                # renderers=[self.custom_chat_entry],
                stylesheets=[
                    """
                                                :host {  background-color:aliceblue; }
                                                """,
                    user_stylesheet if m["role"] == "user" else ragna_stylesheet,
                ],
            )

            # print(chat_entry._composite)
            # chat_entry._composite is a row
            # chat_entry._composite[1] is a Column containing the username, the text+reactions, and the timestamp
            # chat_entry._composite[1][1] is the row containing the text+reactions
            # print(chat_entry._composite[1][1][0])
            chat_entry._composite[1][1][0].stylesheets = [
                """ :host { 
                                                            background-color: #F3F3F3 !important;
                                                            border-radius: 10px !important;
                                                            border: 1px solid #EEEEEE !important;
                                                          
                                                          } """
            ]

            chat_entries.append(chat_entry)

        ARM_BOT = "Arm Bot"
        LEG_BOT = "Leg Bot"

        def callback_test(contents: str, user: str, instance: pn.widgets.ChatInterface):
            # message = f"Echoing {user}: {contents}"
            # return message
            print(user, contents)
            if user == "User":
                yield {
                    "user": ARM_BOT,
                    "avatar": "🦾",
                    "value": f"Hey, {LEG_BOT}! Did you hear the user?",
                }
                instance.respond()
            elif user == ARM_BOT:
                user_entry = instance.value[-3]
                user_contents = user_entry.value
                yield {
                    "user": LEG_BOT,
                    "avatar": "🦿",
                    "value": f'Yeah! They said "{user_contents}".',
                }

        async def callback(
            contents: str, user: str, instance: pn.widgets.ChatInterface
        ):
            # message = f"Echoing {user}: {contents}"
            # return message
            print(user, contents)
            if user == "User":
                yield {
                    "user": LEG_BOT,
                    "avatar": "🦿",
                    "value": self.api_wrapper.answer(
                        self.current_chat["id"], "Ragna", contents
                    ),
                }
                instance.respond()

        chat_interface = pn.widgets.ChatInterface(
            callback=callback,
            callback_user="System",
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            value=chat_entries,
            view_latest=True,
            sizing_mode="stretch_width",
            stylesheets=[
                """
                                                               :host {  
                                                                background-color:pink; 
                                                                margin-left: 18% !important;
                                                                margin-right: 18% !important;
                                                                min-width:45%;
                                                               }
                                                               """
            ],
        )

        chat_interface._composite.objects = [pn.layout.spacer.VSpacer()] + [
            w
            for w in chat_interface._composite.objects
            if not isinstance(w, pn.layout.spacer.VSpacer)
        ]

        chat_interface._chat_log.stylesheets.append(
            """ :host .chat-feed-log {  
                                                            height: unset; max-height: 90%; }
                                                                 """
        )

        return chat_interface

    def __panel__(self):
        print("current_chat", self.current_chat["id"])

        result = pn.Column(
            pn.pane.Markdown("# main_content"),
            self.chat_interface,
            sizing_mode="stretch_width",
            stylesheets=[
                """   
                                       :host { 
                                            background-color: orange;
                                            height:100%;
                                            max-width: 100%;
                                        }
                                """
            ],
        )

        return result
