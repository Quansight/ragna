# Frequently asked questions

## Why should I use Ragna and not X?

!!! tip "TL;DR"

    Ragna is the only tool out there that specializes in orchestrating RAG use cases
    with arbitrary components, as well as offering a Python API, a REST API, and a web
    UI for that.

!!! note

    Although we try to be objective as possible, this section is inheritly biased. If
    you are the author of a package we don't mention below but think we should or your
    package is mentiond but you feel we have mischaracterized it, please
    [get in touch](https://github.com/Quansight/ragna/discussions).

After the emergence of ChatGPT in November of 2022, the field of LLMs exploded. Today,
there are many providers for LLM REST APIs out there. With these, we also have a
plethora of Python packages to build applications around the provided APIs. We cannot
summarize the whole field here, so we stick to large projects in the Python ecosystem
for comparison.

| library or application                                |        RAG         | arbitrary components |     Python API     |      REST API      |       web UI       |
| ----------------------------------------------------- | :----------------: | :------------------: | :----------------: | :----------------: | :----------------: |
| Ragna                                                 | :heavy_check_mark: |  :heavy_check_mark:  | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| [LangChain](https://www.langchain.com/)               | :heavy_check_mark: |  :heavy_check_mark:  | :heavy_check_mark: |        :x:         |        :x:         |
| [Langroid](https://langroid.github.io/langroid/)      | :heavy_check_mark: |  :heavy_check_mark:  | :heavy_check_mark: |        :x:         |        :x:         |
| [LlamaIndex](https://www.llamaindex.ai/)              | :heavy_check_mark: |  :heavy_check_mark:  | :heavy_check_mark: |        :x:         |        :x:         |
| [Ollama](https://ollama.com/)                         |        :x:         |         :x:          | :heavy_check_mark: | :heavy_check_mark: |        :x:         |
| [vLLM](https://github.com/vllm-project/vllm)          |        :x:         |         :x:          | :heavy_check_mark: | :heavy_check_mark: |        :x:         |
| [PrivateGPT](https://privategpt.dev)                  | :heavy_check_mark: |         :x:          |        :x:         | :heavy_check_mark: | :heavy_check_mark: |
| [LocalGPT](https://github.com/PromtEngineer/localGPT) | :heavy_check_mark: |         :x:          |        :x:         | :heavy_check_mark: | :heavy_check_mark: |

## Where do I get API keys for the builtin assistants?

### [OpenAI](https://openai.com/)

1. Get an OpenAI API key following these instructions:
   > First, create an OpenAI account or sign in. Next, navigate to the API key page and
   > "Create new secret key", optionally naming the key. Make sure to save this
   > somewhere safe and do not share it with anyone.
   >
   > ~
   > [OpenAI platform documentation](https://platform.openai.com/docs/quickstart/account-setup)
2. Set the `OPENAI_API_KEY` environment variable with your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="XXXXX"
   ```

### [Anthropic](https://www.anthropic.com)

1. Anthropic currently only provides API keys to business customers:
   > Our API is currently being offered to a limited set of users. We hope to expand
   > access in the future. Please fill out the form below to indicate your interest
   >
   > ~ [Claude API Access](https://www.anthropic.com/earlyaccess)
2. Set the `ANTHROPIC_API_KEY` environment variable with your Anthropic API key:
   ```bash
   export ANTHROPIC_API_KEY="XXXXX"
   ```

### [Google](https://ai.google.dev/)

1. > To use the API, you need an API key. You can create a key with one click in Google
   > AI Studio.
   >
   > ~ [Google AI API](https://ai.google.dev/tutorials/setup)
2. Set the `GOOGLE_API_KEY` environment variable with your Google API key:
   ```bash
   export GOOGLE_API_KEY="XXXXX"
   ```

### [Cohere](https://cohere.com/)

1. > To use the API, you need an API key. You can create a key in the Cohere dashboard
   > using your Cohere account.
   >
   > ~ [Cohere Dashboard](https://dashboard.cohere.com/api-keys)
2. Set the `COHERE_API_KEY` environment variable with your Cohere API key:
   ```bash
   export COHERE_API_KEY="XXXXX"
   ```

### [AI21 Labs](https://www.ai21.com/)

1. To use the API, you need an API key. You can create one in AI21 Studio
   > [Create your account on AI21 Studio](https://studio.ai21.com/sign-up) and start
   > building with Jurassic-2. We offer flexible pay-as-you-go plans as well as a free
   > trial with a generous amount of free credits to get you started.
   >
   > ~ [AI21 Labs API key creation page](https://studio.ai21.com/account/api-key)
2. Set the `AI21_API_KEY` environment variable with your AI21 Labs API key:
   ```bash
   export AI21_API_KEY="XXXXX"
   ```
