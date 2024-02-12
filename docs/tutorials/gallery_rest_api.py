"""
# REST API

Ragna was designed to help you quickly build custom RAG powered web
applications. For this you can leverage the built-in
[REST API](../../references/rest-api.md).

This tutorial walks you through basic steps of using Ragnas REST API.
"""

# %%
# Before we start this tutorial, we import some helpers.

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import documentation_helpers

# %%
# ## Step 1: Start the REST API
#
# Ragnas REST API is normally started from a terminal with
#
# ```bash
# $ ragna api
# ```
#
# For this tutorial we use our helper that does the equivalent just from Python.
#
# !!! note
#
#     By default, the REST API is started from the `ragna.toml` configuration file in
#     the current working directory. If you don't have a configuration file yet, you can
#     run
#
#     ```bash
#     $ ragna init
#     ```
#
#     to start an interactive wizard that helps you create one. The config that we'll
#     be using for this tutorial is equivalent of picking the first option the wizard
#     offers you, i.e. using only demo components.

from ragna.deploy import Config

config = Config()

rest_api = documentation_helpers.RestApi(config)
rest_api.start()

# %%

rest_api.stop()
