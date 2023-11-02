# Frequently asked questions

## How to use the GPT assistants in Ragna?

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
3. Configure Ragna to use the `Gpt35Turbo16k` or `Gpt4` assistants in the
   `ragna-s3.toml` file or with the `Rag.chat` function:

   ```python
   from ragna.source_storages import Gpt35Turbo16k

   ...

   async with rag.chat(assistant=Gpt35Turbo16k) as chat:
        prompt = "Is this a question?"
        answer = await chat.answer(prompt)

   ```

<!-- ## Where to share feedback with developers? -->
