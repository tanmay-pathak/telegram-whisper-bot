
# Voice2Type Telegram Bot

A telegram bot that transcribes and translates voice notes. 


## Environment Variables

To run this project, you will need to add the following environment variables in docker

`TOKEN` = API token for your bot. More details [here](https://core.telegram.org/bots/tutorial).

`USERNAMES` = Usernames that are allowed to use this bot in an array format. Example: `['@ExampleUser1', '@ExampleUser2']`

`OPENAI_API_KEY` (optional) = OpenAI's API key if you would like to use their new TTS service instead of the free gTTS.


## Features

- Transcribes (Speech to Text)
- Translates

## Installation

Clone this project and then use Docker for deployment

```bash
  docker-compose up
```

Now send a message to your bot. Enjoy!!

## Acknowledgements

 - [Whisper.cpp - Amazing tool originally used for transcriptions](https://github.com/ggerganov/whisper.cpp)
 - [Faster-Whisper - Amazing + faster - used now for transcriptions](https://github.com/guillaumekln/faster-whisper)
 - [Tony Mamacos - Inspiration](https://github.com/matiassingers/awesome-readme)

