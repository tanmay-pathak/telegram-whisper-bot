import logging
import os
import glob
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from openai import OpenAI
from pydub import AudioSegment

# Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Environment variables
TOKEN = os.environ.get("TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ALLOWED_USERNAMES = [
    username.strip("'[ ]") for username in os.environ.get("USERNAMES").split(",")
]

if OPENAI_KEY:
    client = OpenAI()


# Functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(
        logging.INFO, f"Command /start entered by {update.effective_chat.username}"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hi, I am Voice2Text bot. I can translate and transcribe voice notes for you. Send a voice note to start!",
    )


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(
        logging.INFO, f"Command /summary entered by {update.effective_chat.username}"
    )

    replied_message = update.message.reply_to_message.text
    prompt = f"You are an expert in summarizing given transcripts."

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": f'Please summarize the following text: "{replied_message}"',
            },
        ],
    )

    summary = completion.choices[0].message.content.strip()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Summary: {summary}",
    )


async def handle_supported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(
        logging.INFO, f"Audio/Video received from  {update.effective_chat.username}."
    )
    await update.message.chat.send_action(action="typing")
    try:
        await process_voice_note(update, context)
    except Exception as e:
        logging.error("An error occurred: %s", e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Oops! An error occurred while transcribing. Please try again. {e}",
            reply_to_message_id=update.message.message_id,
        )


async def process_voice_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.effective_attachment.file_id
    file = await context.bot.get_file(file_id)

    # Download file
    os.chdir("/app/temp/")
    downloaded_filename = await file.download_to_drive()
    path_to_downloaded_file = "/app/temp/{}".format(downloaded_filename)
    logging.log(logging.INFO, f"Downloaded file at {path_to_downloaded_file}")

    # Convert downloaded file to wav
    audio = AudioSegment.from_file(path_to_downloaded_file)
    wav_filename = downloaded_filename.stem + ".wav"
    path_to_wav_file = "/app/temp/{}".format(wav_filename)
    audio.export(path_to_wav_file, format="wav")
    logging.log(logging.INFO, f"Converted to wav {path_to_wav_file}")

    # Split audio into 1-minute chunks
    audio_chunks = split_audio_into_chunks(path_to_wav_file)

    # Transcribe each chunk and save the text together
    transcriptions = []
    for i, chunk in enumerate(audio_chunks):
        chunk.export(f"/app/temp/chunk{i}.wav", format="wav")
        audio_file = open(f"/app/temp/chunk{i}.wav", "rb")
        transcript = client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, response_format="text"
        )
        transcriptions.append(transcript)

    transcript_text = " ".join(transcriptions)

    await delete_temp_files()

    await send_transcription_to_user(transcript_text, update, context)


def split_audio_into_chunks(path_to_wav_file):
    audio = AudioSegment.from_wav(path_to_wav_file)
    length_audio = len(audio)
    start = 0
    # In milliseconds, this is approximately equal to 1 minute.
    threshold = 60000
    audio_chunks = []

    while start < length_audio:
        chunk = audio[start : start + threshold]
        audio_chunks.append(chunk)
        start += threshold

    return audio_chunks


async def delete_temp_files():
    files = glob.glob("/app/temp/*")
    for f in files:
        os.remove(f)
        logging.log(logging.INFO, f"Deleted file {f}")


async def send_transcription_to_user(
    text, update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not text:
        text = "Could not transcribe. Please try again."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_to_message_id=update.message.message_id,
    )


async def handle_unsupported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(
        logging.INFO,
        f"Unsupported file received from {update.effective_chat.username}.",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Oops! I can only accept voice notes, videos or audio files. Please try again! :)",
    )


async def handle_non_allowed_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(
        logging.INFO,
        f"Message received from non-allowed user = {update.effective_chat.username}",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="You are not allowed to use this bot. Sorry!",
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    # Commands
    start_handler = CommandHandler("start", start)
    summary_handler = CommandHandler("summary", summary)

    # add handlers
    application.add_handler(start_handler)
    application.add_handler(summary_handler)

    if len(ALLOWED_USERNAMES) > 0:
        user_filter = filters.ALL
        usernames = [x for x in ALLOWED_USERNAMES if isinstance(x, str)]
        any_ids = [x for x in ALLOWED_USERNAMES if isinstance(x, int)]
        user_ids = [x for x in any_ids if x > 0]
        group_ids = [x for x in any_ids if x < 0]
        user_filter = (
            filters.User(username=usernames)
            | filters.User(user_id=user_ids)
            | filters.Chat(chat_id=group_ids)
        )

        # Handlers
        application.add_handler(
            MessageHandler(
                (filters.VOICE | filters.AUDIO | filters.VIDEO) & user_filter,
                handle_supported_files,
            )
        )
        application.add_handler(
            MessageHandler(
                filters.ALL & user_filter,
                handle_unsupported_files,
            )
        )

    application.add_handler(MessageHandler(filters.ALL, handle_non_allowed_users))
    application.run_polling()
