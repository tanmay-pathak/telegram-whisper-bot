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

# Functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, 'Command /start entered.')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi, I'm a bot. Send me voice notes and I will transcribe them for you!")

async def handle_voicenotes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, 'Voice note received.')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice note sent. Transcribing...")
    await process_voice_note(update, context)

async def process_voice_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.effective_attachment.file_id
    file = await context.bot.get_file(file_id)

    downloaded_filename = await file.download_to_drive()
    path_to_downloaded_file = './{}'.format(downloaded_filename)

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
        os.remove(file)


async def handle_non_voice_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, 'Non-voice note message received.')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Oops! I can only accept voice notes. Please try again! :)")
    
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Commands
    start_handler = CommandHandler('start', start)

    # Handlers
    application.add_handler(start_handler)
    application.add_handler(MessageHandler(filters.VOICE, handle_voicenotes))
    application.add_handler(MessageHandler(filters.ALL, handle_non_voice_notes))

    application.run_polling()
