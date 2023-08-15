import pluggy

from ora._backend import (
    Doc,
    DocDB,
    DocMeta,
    EnvironmentVariableRequirement,
    LLM,
    PackageRequirement,
    Page,
    Requirement,
    Source,
)

hookimpl = pluggy.HookimplMarker("ora")
del pluggy


from .demo import ora_demo_doc_db, ora_demo_llm
from .doc_db import chroma
from .doc_meta import txt_doc
from .llm import (
    anthropic_claude_1_instant,
    anthropic_claude_2,
    mosaic_mpt_30b_instruct,
    mosaic_mpt_7b_instruct,
    openai_gpt_35_turbo_16k,
    openai_gpt_4,
)
