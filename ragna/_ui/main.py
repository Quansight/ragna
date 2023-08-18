import panel as pn
import param

from ragna._backend import Document
from .chat_config import ChatConfig


class Page(param.Parameterized):
    source_storage_name = param.Selector()
    llm_name = param.Selector()

    chat_config = param.ClassSelector(ChatConfig)

    # This cannot be on the main page, since that would mean we persist the document
    # in memory. It has to be on a modal class which is destroyed together with the
    # modal
    documents = param.List(item_type=Document)

    def __init__(self, app_config, components):
        self.file_input = pn.widgets.FileInput(multiple=True)

        super().__init__()

        self.app_config = app_config
        self.components = components

        source_storage_names = list(components.source_storages.keys())
        self.param.source_storage_name.objects = source_storage_names
        self.source_storage_name = source_storage_names[0]

        llm_names = list(components.llms.keys())
        self.param.llm_name.objects = llm_names
        self.llm_name = llm_names[0]

        self.question = pn.widgets.TextInput()

        self.fake_chat_box = pn.layout.Column()

    def __panel__(self):
        start_conversation_button = pn.widgets.Button(name="Start conversation")
        start_conversation_button.on_click(self.start_conversation)

        ask_button = pn.widgets.Button(name="Send")
        ask_button.on_click(self.ask)

        return pn.layout.Column(
            pn.widgets.Select.from_param(self.param.source_storage_name),
            pn.widgets.Select.from_param(self.param.llm_name),
            self.file_input,
            start_conversation_button,
            pn.layout.Row(self.question, ask_button),
            self.fake_chat_box,
        )

    @param.depends("file_input.param", watch=True)
    def upload_documents(self):
        if not self.file_input.value:
            return

        self.documents = [
            Document._from_name_and_content(
                name, content, page_extractors=self.components.page_extractors.values()
            )
            for name, content in zip(self.file_input.filename, self.file_input.value)
        ]

    def start_conversation(self, event):
        if not self.documents:
            return

        source_storage = self.components.source_storages[self.source_storage_name]
        chat_config = ChatConfig(
            source_storage=source_storage,
            llm=self.components.llms[self.llm_name],
            document_metadatas=[document.metadata for document in self.documents],
        )

        source_storage.store(self.documents, chat_config=chat_config)

        chat_config.chat_log.append(f"A: Hi, I'm {self.llm_name}!")
        self.chat_config = chat_config

    @param.depends("chat_config.chat_log", watch=True)
    def answer(self):
        last = self.chat_config.chat_log[-1]
        self.fake_chat_box.append(pn.pane.HTML(last))

        if last.startswith("A"):
            return

        prompt = last.removeprefix("Q: ")

        sources = self.chat_config.source_storage.retrieve(
            prompt, num_tokens=1_000, chat_config=self.chat_config
        )
        answer = self.chat_config.llm.complete(
            prompt, sources, chat_config=self.chat_config
        )

        self.chat_config.chat_log.append(f"A: {answer}")
        self.chat_config.param.trigger("chat_log")

    def ask(self, event):
        self.chat_config.chat_log.append(f"Q: {self.question.value}")
        self.chat_config.param.trigger("chat_log")


def app(*, app_config, components):
    pn.serve(
        {"/": Page(app_config, components)},
        port=app_config.port,
        start=True,
        show=False,
        location=True,
        allow_websocket_origin=[app_config.url, f"{app_config.url}:{app_config.port}"],
    )
