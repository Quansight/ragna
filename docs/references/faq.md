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
