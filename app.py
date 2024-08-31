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
from openai import AsyncOpenAI
from pydub import AudioSegment
from telegram.constants import ParseMode
import json

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

# Environment variables
TOKEN = os.environ.get("TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ALLOWED_USERNAMES = [
    username.strip("'\"[ ]") for username in os.environ.get("USERNAMES").split(",")
]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")

if OPENAI_KEY:
    client = AsyncOpenAI()

HELP_MESSAGE = """I am Voice2Text bot. I can transcribe, translate, and summarize voice notes for you. Send a voice note to start!

You can reply to a transcript with the following commands:
⚪ /important – Get the Title, Summary, Important Points, Follow Up Questions, Next Steps and Action Items from a transcript.
⚪ /summary – Get the Summary from a transcript.
⚪ /todo – Get the TODO items from a transcript.
"""


# Function to handle /start command. It sends a welcome message to the user.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"Command /start entered by {update.effective_chat.username}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=HELP_MESSAGE,
    )


# Function to handle /summary command. It sends a summary of the transcript being replied to, to the user.
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"Command /summary entered by {update.effective_chat.username}")

    replied_message = update.message.reply_to_message
    if not replied_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please reply to a message with /summary to get a summary of the transcript.",
        )
        return
    replied_message = update.message.reply_to_message.text

    await update.message.chat.send_action(action="typing")
    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "The following is a transcript of a voice message. Extract a title and summary from it.",
            },
            {"role": "user", "content": replied_message},
        ],
        max_tokens=1000,
        temperature=0.6,
    )

    summary = completion.choices[0].message.content.strip()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{summary}",
        reply_to_message_id=update.message.message_id,
    )


# Function to handle /important command. It extracts the important points from the transcript being replied to, to the user.
async def handle_important_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(
        f"Command /important entered by {update.effective_chat.username}",
    )

    replied_message = update.message.reply_to_message
    if not replied_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please reply to a message with /important to run this command.",
        )
        return

    placeholder_message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"...",
        reply_to_message_id=update.message.message_id,
    )
    await update.message.chat.send_action(action="typing")

    try:
        await get_imporant_details(update, context, placeholder_message)
    except Exception as e:
        logging.error("An error occurred: %s", e)
        await context.bot.edit_message_text(
            chat_id=placeholder_message.chat_id,
            text=f"Oops! An error occurred while handling important command. Please try again. {e}",
            message_id=placeholder_message.message_id,
        )


async def get_imporant_details(
    update: Update, context: ContextTypes.DEFAULT_TYPE, placeholder_message: Update
):
    replied_message = update.message.reply_to_message.text

    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "The following is a transcript of a voice message. Extract a title, a short summary, any important points (if present), any follow up questions to ask the speaker (if present), any next steps for both parties and action items from it and answer in JSON in this format: {title: string, summary: string, importantPoints: [string, string, ...] | NULL, followUpQuestions: [string, string, ...] | NULL, nextSteps: [string, string, ...] | NULL, actionItems: [string, string, ...] | NULL}",
            },
            {"role": "user", "content": replied_message},
        ],
        max_tokens=1000,
        temperature=0.6,
    )

    response_content = completion.choices[0].message.content.strip()
    response_dict = json.loads(response_content)

    title = response_dict.get("title")
    summary = response_dict.get("summary")
    important_points = response_dict.get("importantPoints")
    follow_up_questions = response_dict.get("followUpQuestions")
    next_steps = response_dict.get("nextSteps")
    action_items = response_dict.get("actionItems")

    message = f"**Title:** {title}\n\n**Summary:** {summary}\n"

    if important_points:
        message += "\n\n**Important Points:**\n" + "\n".join(
            f"- {point}" for point in important_points
        )

    if follow_up_questions:
        message += "\n\n**Follow Up Questions:**\n" + "\n".join(
            f"- {question}" for question in follow_up_questions
        )

    if next_steps:
        message += "\n\n**Next Steps:**\n" + "\n".join(
            f"- {step}" for step in next_steps
        )

    if action_items:
        message += "\n\n**Action Items:**\n" + "\n".join(
            f"- {item}" for item in action_items
        )

    await context.bot.edit_message_text(
        chat_id=placeholder_message.chat_id,
        message_id=placeholder_message.message_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
    )


# Function to handle the /todo command. It creates action items from the text being replied to.
async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"Command /todo entered by {update.effective_chat.username}")

    replied_message = update.message.reply_to_message
    if not replied_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please reply to a message with /todo to get the TODO items from the transcript.",
        )
        return
    replied_message = update.message.reply_to_message.text

    await update.message.chat.send_action(action="typing")
    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "The following is a transcript of a voice message. Extract action items from it. Respond with a list of action items, separated by commas.",
            },
            {"role": "user", "content": replied_message},
        ],
        max_tokens=1000,
        temperature=0.6,
    )

    action_items = completion.choices[0].message.content.split(",")
    action_items_text = "\n".join(action_items)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Action Items:\n{action_items_text}",
        reply_to_message_id=update.message.message_id,
    )


async def handle_supported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"Audio/Video received from  {update.effective_chat.username}.")
    placeholder_message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"...",
        reply_to_message_id=update.message.message_id,
    )
    await update.message.chat.send_action(action="typing")
    try:
        await process_voice_note(update, context, placeholder_message)
    except Exception as e:
        logging.error("An error occurred: %s", e)
        await context.bot.edit_message_text(
            chat_id=placeholder_message.chat_id,
            text=f"Oops! An error occurred while transcribing. Please try again. {e}",
            message_id=placeholder_message.message_id,
        )


async def process_voice_note(
    update: Update, context: ContextTypes.DEFAULT_TYPE, placeholder_message: Update
):
    file_id = update.message.effective_attachment.file_id
    file = await context.bot.get_file(file_id)

    # Download file
    os.chdir("/app/temp/")
    downloaded_filename = await file.download_to_drive()
    path_to_downloaded_file = "/app/temp/{}".format(downloaded_filename)
    logging.info(f"Downloaded file at {path_to_downloaded_file}")

    # Convert downloaded file to wav
    audio = AudioSegment.from_file(path_to_downloaded_file)
    wav_filename = downloaded_filename.stem + ".wav"
    path_to_wav_file = "/app/temp/{}".format(wav_filename)
    audio.export(path_to_wav_file, format="wav")
    logging.info(f"Converted to wav {path_to_wav_file}")

    # Split audio into 1-minute chunks
    audio_chunks = split_audio_into_chunks(path_to_wav_file)

    # Transcribe each chunk and save the text together
    transcriptions = []
    for i, chunk in enumerate(audio_chunks):
        chunk.export(f"/app/temp/chunk{i}.wav", format="wav")
        audio_file = open(f"/app/temp/chunk{i}.wav", "rb")
        transcript = await client.audio.translations.create(
            model="whisper-1", file=audio_file, response_format="text"
        )
        transcriptions.append(transcript)

    transcript_text = " ".join(transcriptions)

    await delete_temp_files()
    await context.bot.edit_message_text(
        transcript_text,
        chat_id=placeholder_message.chat_id,
        message_id=placeholder_message.message_id,
    )


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
        logging.info(f"Deleted file {f}")


async def send_transcription_to_user(
    text, update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not text:
        text = "Could not transcribe. Please try again."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"<i>{text}</i>",
        reply_to_message_id=update.message.message_id,
        parse_mode=ParseMode.HTML,
    )


async def handle_unsupported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(
        f"Unsupported file received from {update.effective_chat.username}.",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Oops! I can only accept voice notes, videos or audio files. Please try again! :)",
    )


async def handle_non_allowed_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(
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
    help_handler = CommandHandler("help", start)
    summary_handler = CommandHandler("summary", summary)
    todo_handler = CommandHandler("todo", todo)
    important_handler = CommandHandler("important", handle_important_command)

    # add handlers
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(summary_handler)
    application.add_handler(todo_handler)
    application.add_handler(important_handler)

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
