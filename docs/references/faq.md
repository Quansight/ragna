# Frequently asked questions

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

### [MosaicML](https://mosaicml.com)

1. MosaicML currently has a waitlist for new users:
   > We are currently experiencing very high demand and have a waitlist. Please stay
   > tuned for when we open for broader access.
   >
   > ~ [MosaicML console](https://console.mosaicml.com/)
2. Set the `MOSAICML_API_KEY` environment variable with your MosaicML API key:
   ```bash
   export MOSAICML_API_KEY="XXXXX"
   ```
