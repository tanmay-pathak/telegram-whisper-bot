
# Voice2Type Telegram Bot

A telegram bot that transcribes and translates voice notes. 


## Environment Variables

To run this project, you will need to add the following environment variables in docker

`TOKEN` = API token for your bot. More details [here](https://core.telegram.org/bots/tutorial).

`USERNAMES` = Usernames that are allowed to use this bot in an array format. Example: `['@ExampleUser1', '@ExampleUser2']`


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

 - [Whisper.cpp - Amazing tool](https://github.com/ggerganov/whisper.cpp)
 - [Tony Mamacos - Inspiration](https://github.com/matiassingers/awesome-readme)

