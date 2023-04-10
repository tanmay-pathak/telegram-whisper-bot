import logging
import os
import glob
from subprocess import Popen, PIPE
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Environment variables
TOKEN = os.environ.get('TOKEN')
ALLOWED_USERNAMES = [username.strip("'[ ]") for username in os.environ.get('USERNAMES').split(',')]

# Functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, f'Command /start entered by {update.effective_chat.username}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi, I am Voice2Type bot. I can translate and transcribe voice notes for you. Send a voice note to start!")

async def handle_supported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, f'File received from  {update.effective_chat.username}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="File received. Converting, translating and transcribing...")
    await process_voice_note(update, context)

async def process_voice_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.effective_attachment.file_id
    file = await context.bot.get_file(file_id)

    downloaded_filename = await file.download_to_drive()
    path_to_downloaded_file = './{}'.format(downloaded_filename)
    logging.log(logging.INFO, f'Downloaded file at {path_to_downloaded_file}')

    await transcribe_voice_note(path_to_downloaded_file)
    await send_transcription_to_user(path_to_downloaded_file, update, context)
    await delete_temp_files()

async def transcribe_voice_note(path_to_file):
    cmd = 'bash ./convert.sh ' + path_to_file
    process = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
    process.wait()

async def send_transcription_to_user(path_to_file, update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = open(path_to_file + ".wav.txt", "r")
    text = result.read()
    result.close()
    if not text:
        text = 'Could not transcribe. Please try again.'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def delete_temp_files():
    for file in glob.glob('file_*.oga*'):
        logging.log(logging.INFO, f'Deleting temp file: {file}')
        os.remove(file)


async def handle_unsupported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, f'Unsupported file received from  {update.effective_chat.username}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Oops! I can only accept voice notes, videos or audio files. Please try again! :)")

async def handle_non_allowed_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, f'Message received from non-allowed user = {update.effective_chat.username}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not allowed to use this bot. Sorry!")
    
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Commands
    start_handler = CommandHandler('start', start)

    # Handlers
    application.add_handler(start_handler)
    application.add_handler(MessageHandler((filters.VOICE | filters.AUDIO | filters.VIDEO) & filters.Chat(username=ALLOWED_USERNAMES), handle_supported_files))
    application.add_handler(MessageHandler(filters.ALL & filters.Chat(username=ALLOWED_USERNAMES), handle_unsupported_files))
    application.add_handler(MessageHandler(filters.ALL, handle_non_allowed_users))

    application.run_polling()
