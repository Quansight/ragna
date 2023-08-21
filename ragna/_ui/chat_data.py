from datetime import datetime, timedelta, timezone

import param

from ragna._ui import AppComponents, AppConfig


def get_default_chat_name(timezone_offset=None):
    if timezone_offset is None:
        return f"Chat {datetime.now():%m/%d/%Y %I:%M %p}"
    else:
        tz = timezone(offset=timedelta(minutes=timezone_offset))
        return f"Chat {datetime.now().astimezone(tz=tz):%m/%d/%Y %I:%M %p}"


class ChatData(param.Parameterized):
    # user? remove any objects that are large etc?
    #  chunk_size etc won't always exist (extra key.. chroma looks for certain keys here or uses defaults
    # middle of modal is customizable
    #  add chat_name
    # DB: user_name and chat name are sufficient to index
    chat_id = param.String()
    app_config = param.ClassSelector(AppConfig)
    components = param.ClassSelector(AppComponents)
    llm = param.Selector()
    source_storage = param.Selector()
    document_metadata = param.Selector()
    page_extractor = param.Selector()
    chat_log = param.List(item_type=str)
    extra = param.Parameterized()

    sources_info = param.Dict(default={})
    chat_log = param.List(
        default=[{"Model": "How can I help you with the selected sources?"}]
    )

    def __init__(
        self,
        **params,
        # llm: Llm,
        # source_storage: SourceStorage,
        # document_metadatas: list[DocumentMetadata],
    ):
        super().__init__(**params)

    @param.depends("components", watch=True, on_init=True)
    def _init_from_components(self):
        for comp, comp_options in vars(self.components).items():
            setattr(self, comp[:-1], comp_options)

            # getattr(self.param,component) = getattr(self.components, "llms")
        # self.llm = self.param.llm.objects[next(iter(self.param.llm.objects))]
        # self.param.source_storage.objects = getattr(self.components, "source_storages")
        # self.source_storage = self.param.source_storage.objects[next(iter(self.param.source_storage))]
        # self.param.document_metadata.objects = getattr(self.components, "document_metadatas")
        # self.document_metadata = self.param.document_metadata.objects[next(iter(self.param.document_metadata))]
        # self.param.page_extractor.objects = getattr(self.components, "page_extractors")
        # self.page_extractor = self.param.page_extractor.objects[next(iter(self.param.page_extractor))]


#################################################################################

# class ChatData(param.Parameterized):
#     documents = param.List(default=[], item_type=Document)
#     document_names = param.List(default=[], item_type=str)
#     supported_document_dbs = get_supported_document_dbs()
#     document_db_name = param.Selector(
#         objects=supported_document_dbs,
#         allow_None=False,
#         default=supported_document_dbs[0],
#     )
#     document_db = param.ClassSelector(DocumentDB)


#     llm_name = param.Selector(
#         objects=[
#             f"{organization}/{model}"
#             for organization, models in get_supported_models().items()
#             for model in models
#         ],
#         allow_None=False,
#     )
#     llm = param.ClassSelector(LLM)


#     @param.depends("documents", watch=True)
#     def update_document_names(self):
#         new_docs = [document.name for document in self.documents]
#         self.document_names = new_docs + self.document_names


#     @param.depends("document_db_name", watch=True, on_init=True)
#     def load_document_db(self):
#         self.document_db = load_document_db(self.document_db_name)

#     @param.depends("document_names", watch=True)
#     def store_documents(self):
#         self.document_db.store(
#             self.documents, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
#         )

#     @param.depends("llm_name", watch=True, on_init=True)
#     def load_llm(self):
#         self.llm = load_llm(*self.llm_name.split("/"))

#     @param.depends("llm", watch=True, on_init=True)
#     def update_max_context_tokens(self):
#         # 1. We limit the default value to 8_000 tokens, because otherwise the response
#         #    time is really high for a default setting
#         # 2. We reserve at least 1_000 tokens for prompt and instruction
#         self.max_context_tokens = min(
#             (self.llm.max_context_size - 1_000) // 1_000 * 1_000, 8_000
#         )
#         # We set the bound to the actual maximum
#         self.param.max_context_tokens.bounds = (0, self.llm.max_context_size)


#     # TODO: when the value of pn.widgets.ChatBox can be properly bound to a param,
#     #  remove the return values and decorate this method with
#     #  @param.depends("chat_log", watch=True)
#     async def complete_prompt(self):
#         last_message = self.chat_log[-1]
#         prompt = last_message.get("You")
#         if not prompt:
#             return False

#         logger.info(f"User asked: {prompt}")
#         if self.document_db.contains_docs():
#             relevant_document_chunks = self.document_db.retrieve(
#                 prompt, max_tokens=self.max_context_tokens
#             )
#             logger.info(
#                 json.dumps(
#                     {
#                         "relevant_document_chunks": summarize_chunk_metadata(
#                             relevant_document_chunks
#                         )
#                     }
#                 )
#             )
#             source_info, context = zip(*relevant_document_chunks)

#             answer = self.llm(
#                 prompt,
#                 context=context,
#                 max_new_tokens=self.max_new_tokens,
#                 instructize=True,
#             )

#             self.sources_info[(len(self.chat_log), answer)] = source_info
#         else:
#             answer = "Please choose documents"
#         logger.info(f"Model responded: {answer}")

#         self.chat_log.append({self.llm_name: answer})
#         return True
