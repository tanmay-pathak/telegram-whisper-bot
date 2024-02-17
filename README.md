# Voice2Text Telegram Bot

A telegram bot that transcribes voice to text. It also supports further processing of the transcript.

## Features

- Transcribe speech to text
- Summarize a transcript
- Extract important points from a transcript
- Create action items from a transcript
- Generate follow up questions from a transcript
- Determine next steps
- Translate text to Hinglish
- Translate text to English

## Environment Variables

To run this project, you will need to add the following environment variables in docker

`TOKEN` = API token for your bot. More details [here](https://core.telegram.org/bots/tutorial).

`USERNAMES` = Usernames and/or UserIDs that are allowed to use this bot in an array format. Example: `['@ExampleUser1', '@ExampleUser2', 12345678]`

`OPENAI_API_KEY` = OpenAI's API key to use Whisper to convert speech to text and process transcript with `gpt-3.5-turbo` model.

## Run by building an image locally

Clone this project and then use Docker for deployment

```bash
  git clone https://github.com/tanmay-pathak/telegram-whisper-bot.git
  docker-compose up -d
```

## Run by using an already built image

Use the following `docker-compose.yaml`

```yaml
version: "3.8"
services:
  bot:
    image: tanmaypathak/telegram-whisper-bot:latest
    restart: always
    environment:
      - TOKEN="YOUR_BOT_TOKEN"
      - USERNAMES=[]
      - OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
```

Now send a message to your bot. Enjoy!!
