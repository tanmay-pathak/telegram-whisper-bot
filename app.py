import logging
import os
import glob
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from gtts import gTTS
from faster_whisper import WhisperModel

# Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Faster-whisper setup
model_size = "large-v2"
model = WhisperModel(model_size, device="cpu", compute_type="int8")

# Environment variables
TOKEN = os.environ.get('TOKEN')
ALLOWED_USERNAMES = [username.strip("'[ ]") for username in os.environ.get('USERNAMES').split(',')]

# Functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, f'Command /start entered by {update.effective_chat.username}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi, I am Voice2Type bot. I can translate and transcribe voice notes for you. Send a voice note to start!")

async def handle_supported_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, f'File received from  {update.effective_chat.username}')
    await update.message.chat.send_action(action="typing")
    await process_voice_note(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logging.log(logging.INFO, f'Text {text} received from {update.effective_chat.username}')
    await update.message.chat.send_action(action="record_audio")
    gTTS(text).save("./file_elevenlabs.mp3")
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice="./file_elevenlabs.mp3", reply_to_message_id=update.message.message_id)

async def process_voice_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.effective_attachment.file_id
    file = await context.bot.get_file(file_id)

    downloaded_filename = await file.download_to_drive()
    path_to_downloaded_file = './{}'.format(downloaded_filename)
    logging.log(logging.INFO, f'Downloaded file at {path_to_downloaded_file}')

    segments, _ = model.transcribe(path_to_downloaded_file, beam_size=5)
    segments = list(segments)
    logging.log(logging.INFO, f'Transcription info: {segments}')
    transcription = ""
    for segment in segments:
        transcription += "%s" % (segment.text)
    await send_transcription_to_user(transcription, update, context)
    await delete_temp_files()

async def send_transcription_to_user(text, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not text:
        text = 'Could not transcribe. Please try again.'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_to_message_id=update.message.message_id)

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
    application.add_handler(MessageHandler((filters.TEXT) & filters.Chat(username=ALLOWED_USERNAMES), handle_text))
    application.add_handler(MessageHandler(filters.ALL & filters.Chat(username=ALLOWED_USERNAMES), handle_unsupported_files))
    application.add_handler(MessageHandler(filters.ALL, handle_non_allowed_users))

    application.run_polling()
