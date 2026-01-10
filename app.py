"""
Voice2Text Telegram Bot

A Telegram bot that transcribes voice notes with speaker diarization and supports
various transcript processing operations including translation, summarization, and
action item extraction.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import glob
import logging
import os
from dataclasses import dataclass
from typing import Any, List, Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
from openai import AsyncOpenAI
from pydub import AudioSegment
from pydantic import BaseModel


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class Config:
    """Centralized configuration for the Voice2Text bot."""

    # Environment Variables
    token: str
    openai_api_key: str
    allowed_usernames: List[str]
    openai_model: str

    # Paths
    temp_dir: str = "/app/temp/"
    transcription_model: str = "gpt-4o-transcribe-diarize"

    # Messages
    help_message: str = """I am Voice2Text bot. I transcribe voice notes with speaker labels and timestamps. Send a voice note to start!

You can reply to a transcript with the following commands:
⚪ /important – Get the Title, Summary, Important Points, Follow Up Questions, Next Steps and Action Items from a transcript.
⚪ /summary – Get the Summary from a transcript.
⚪ /todo – Get the TODO items from a transcript.
⚪ /english – Translate a transcript to English.
"""

    error_messages: dict = None

    def __post_init__(self):
        """Initialize default error messages after dataclass creation."""
        if self.error_messages is None:
            self.error_messages = {
                "no_reply": "Please reply to a message with {command} to process the transcript.",
                "processing_error": "Oops! An error occurred while {action}. Please try again. {error}",
                "unsupported_file": "Oops! I can only accept voice notes, videos or audio files. Please try again! :)",
                "not_allowed": "You are not allowed to use this bot. Sorry!",
            }

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config instance from environment variables."""
        token = os.environ.get("TOKEN")
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        usernames_str = os.environ.get("USERNAMES", "")
        openai_model = os.environ.get("OPENAI_MODEL")

        # Validate required environment variables
        if not token:
            raise ValueError("TOKEN environment variable is required")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not openai_model:
            raise ValueError("OPENAI_MODEL environment variable is required")

        # Parse allowed usernames
        allowed_usernames = [
            username.strip("'\"[ ]")
            for username in usernames_str.split(",")
            if username.strip()
        ]

        return cls(
            token=token,
            openai_api_key=openai_api_key,
            allowed_usernames=allowed_usernames,
            openai_model=openai_model,
        )


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class Summary(BaseModel):
    """Pydantic model for summary response from OpenAI."""

    summary: str


class Translation(BaseModel):
    """Pydantic model for translation response from OpenAI."""

    translation: str


class Important(BaseModel):
    """Pydantic model for comprehensive transcript analysis."""

    title: str
    summary: str
    importantPoints: List[str]
    followUpQuestions: List[str]
    nextSteps: List[str]
    actionItems: List[str]


class Todo(BaseModel):
    """Pydantic model for action items extraction from transcript."""

    actionItems: List[str]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.WARNING,
    )


def log_command(username: Optional[str], command: str) -> None:
    """Log a command execution.

    Args:
        username: Username of the user who executed the command
        command: Command that was executed
    """
    if username:
        logging.warning(f"Command {command} entered by {username}")


def format_list_items(items: List[str], title: str) -> str:
    """Format a list of items into a bullet-pointed string.

    Args:
        items: List of items to format
        title: Title to display above the list

    Returns:
        Formatted string with title and bullet points
    """
    if not items:
        return ""
    return f"\n\n**{title}:**\n" + "\n".join(f"- {item}" for item in items)


def format_diarized_transcript(transcript: Any) -> str:
    """Format diarized JSON response into readable text with speaker labels.

    Args:
        transcript: OpenAI transcript response with diarization

    Returns:
        Formatted transcript with speaker labels and timestamps
    """
    lines = []
    for segment in transcript.segments:
        speaker_line = (
            f"Speaker: {segment.speaker} ({segment.start:.1f}s - {segment.end:.1f}s)"
        )
        lines.append(speaker_line)
        lines.append(segment.text)
        lines.append("")  # Empty line for spacing
    return "\n".join(lines).strip()


async def delete_temp_files(temp_dir: str) -> None:
    """Delete all files from the temporary directory.

    Args:
        temp_dir: Path to the temporary directory
    """
    files = glob.glob(f"{temp_dir}*")
    for file_path in files:
        try:
            os.remove(file_path)
            logging.info(f"Deleted file {file_path}")
        except OSError as e:
            logging.error(f"Failed to delete file {file_path}: {e}")


# ============================================================================
# VOICE2TEXT BOT APPLICATION CLASS
# ============================================================================


class Voice2TextBot:
    """Main application class for the Voice2Text Telegram bot."""

    def __init__(self, config: Config):
        """Initialize the bot with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)

    # -------------------------------------------------------------------------
    # Command Handlers
    # -------------------------------------------------------------------------

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start and /help commands.

        Sends a welcome message with instructions on how to use the bot.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        log_command(username, "/start")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self.config.help_message,
        )

    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /summary command.

        Extracts and returns a summary of the transcript being replied to.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        log_command(username, "/summary")

        replied_message = self._check_reply_message(update, context, "/summary")
        if not replied_message:
            return

        await update.message.chat.send_action(action="typing")

        try:
            summary_obj = await self._call_openai_parse(
                messages=[
                    {
                        "role": "system",
                        "content": "The following is a transcript of a voice message. Extract a title and summary from it.",
                    },
                    {"role": "user", "content": replied_message},
                ],
                response_format=Summary,
            )

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{summary_obj.summary}",
                reply_to_message_id=update.message.message_id,
            )
        except Exception as e:
            logging.error("An error occurred in summary: %s", e)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=self.config.error_messages["processing_error"].format(
                    action="generating summary", error=e
                ),
            )

    async def handle_important_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle the /important command.

        Extracts comprehensive details (title, summary, important points, follow-up
        questions, next steps, and action items) from the transcript.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        log_command(username, "/important")

        replied_message = self._check_reply_message(update, context, "/important")
        if not replied_message:
            return

        placeholder = await self._send_placeholder(update, context)

        try:
            await self._get_important_details(
                update, context, placeholder, replied_message
            )
        except Exception as e:
            logging.error("An error occurred in important command: %s", e)
            await self._update_placeholder_with_error(
                context, placeholder, "running important command", e
            )

    async def todo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /todo command.

        Extracts and returns action items from the transcript being replied to.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        log_command(username, "/todo")

        replied_message = self._check_reply_message(update, context, "/todo")
        if not replied_message:
            return

        await update.message.chat.send_action(action="typing")

        try:
            todo_obj = await self._call_openai_parse(
                messages=[
                    {
                        "role": "system",
                        "content": "The following is a transcript of a voice message. Extract action items from it.",
                    },
                    {"role": "user", "content": replied_message},
                ],
                response_format=Todo,
            )

            action_items_text = "\n".join(todo_obj.actionItems)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Action Items:\n{action_items_text}",
                reply_to_message_id=update.message.message_id,
            )
        except Exception as e:
            logging.error("An error occurred in todo: %s", e)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=self.config.error_messages["processing_error"].format(
                    action="extracting TODOs", error=e
                ),
            )

    async def english(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /english command.

        Translates the transcript being replied to into English.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        log_command(username, "/english")

        replied_message = self._check_reply_message(update, context, "/english")
        if not replied_message:
            return

        placeholder = await self._send_placeholder(update, context)

        try:
            translation_obj = await self._call_openai_parse(
                messages=[
                    {
                        "role": "system",
                        "content": "Translate the following text to English. Only return the translation, nothing else.",
                    },
                    {"role": "user", "content": replied_message},
                ],
                response_format=Translation,
            )

            await context.bot.edit_message_text(
                chat_id=placeholder.chat_id,
                message_id=placeholder.message_id,
                text=f"{translation_obj.translation}",
            )
        except Exception as e:
            logging.error("An error occurred in translation: %s", e)
            await self._update_placeholder_with_error(
                context, placeholder, "translating", e
            )

    # -------------------------------------------------------------------------
    # Message Handlers
    # -------------------------------------------------------------------------

    async def handle_supported_files(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle supported file types (voice, audio, video).

        Processes the media file and transcribes it with speaker diarization.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        logging.warning(f"Audio/Video received from {username}.")

        placeholder = await self._send_placeholder(update, context)

        try:
            await self._process_voice_note(update, context, placeholder)
        except Exception as e:
            logging.error("An error occurred while transcribing: %s", e)
            await self._update_placeholder_with_error(
                context, placeholder, "transcribing", e
            )

    async def handle_unsupported_files(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle unsupported file types.

        Sends an error message when a user uploads an unsupported file type.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        logging.warning(f"Unsupported file received from {username}.")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self.config.error_messages["unsupported_file"],
        )

    async def handle_non_allowed_users(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle messages from non-allowed users.

        Sends a message indicating the user is not authorized to use the bot.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        username = update.effective_chat.username
        logging.warning(f"Message received from non-allowed user = {username}")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self.config.error_messages["not_allowed"],
        )

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _check_reply_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, command: str
    ) -> Optional[str]:
        """Check if the message has a replied-to message and return its text.

        Args:
            update: Telegram update object
            context: Telegram context object
            command: Command name for error message

        Returns:
            Text of the replied message, or None if no reply
        """
        replied_message = update.message.reply_to_message
        if not replied_message:
            import asyncio

            asyncio.create_task(
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=self.config.error_messages["no_reply"].format(command=command),
                )
            )
            return None
        return replied_message.text

    async def _send_placeholder(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Update:
        """Send a placeholder message while processing.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            The placeholder message object
        """
        placeholder = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="...",
            reply_to_message_id=update.message.message_id,
        )
        await update.message.chat.send_action(action="typing")
        return placeholder

    async def _update_placeholder_with_error(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder: Update,
        action: str,
        error: Exception,
    ) -> None:
        """Update placeholder message with error text.

        Args:
            context: Telegram context object
            placeholder: Placeholder message to update
            action: Description of the action being performed
            error: Exception that occurred
        """
        await context.bot.edit_message_text(
            chat_id=placeholder.chat_id,
            text=self.config.error_messages["processing_error"].format(
                action=action, error=error
            ),
            message_id=placeholder.message_id,
        )

    async def _call_openai_parse(
        self,
        messages: List[dict],
        response_format: BaseModel,
    ) -> Any:
        """Call OpenAI API with structured output parsing.

        Args:
            messages: List of message dictionaries for the API call
            response_format: Pydantic model for structured output

        Returns:
            Parsed response object

        Raises:
            Exception: If the API call fails
        """
        completion = await self.client.beta.chat.completions.parse(
            model=self.config.openai_model,
            messages=messages,
            response_format=response_format,
        )
        return completion.choices[0].message.parsed

    async def _get_important_details(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder: Update,
        transcript_text: str,
    ) -> None:
        """Extract and format important details from a transcript.

        Args:
            update: Telegram update object
            context: Telegram context object
            placeholder: Placeholder message to update
            transcript_text: Transcript text to analyze
        """
        important_obj = await self._call_openai_parse(
            messages=[
                {
                    "role": "system",
                    "content": "The following is a transcript of a voice message. Extract the title, summary, important points, follow up questions, next steps and action items from it.",
                },
                {"role": "user", "content": transcript_text},
            ],
            response_format=Important,
        )

        message = (
            f"**Title:** {important_obj.title}\n\n**Summary:** {important_obj.summary}"
        )

        message += format_list_items(important_obj.importantPoints, "Important Points")
        message += format_list_items(
            important_obj.followUpQuestions, "Follow Up Questions"
        )
        message += format_list_items(important_obj.nextSteps, "Next Steps")
        message += format_list_items(important_obj.actionItems, "Action Items")

        await context.bot.edit_message_text(
            chat_id=placeholder.chat_id,
            message_id=placeholder.message_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _process_voice_note(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder: Update,
    ) -> None:
        """Download, convert, and transcribe a voice note.

        Args:
            update: Telegram update object
            context: Telegram context object
            placeholder: Placeholder message to update
        """
        # Download file
        file_id = update.message.effective_attachment.file_id
        file = await context.bot.get_file(file_id)

        original_wd = os.getcwd()
        try:
            os.chdir(self.config.temp_dir)
            downloaded_filename = await file.download_to_drive()
            path_to_downloaded_file = f"{self.config.temp_dir}{downloaded_filename}"
            logging.info(f"Downloaded file at {path_to_downloaded_file}")

            # Convert to WAV
            audio = AudioSegment.from_file(path_to_downloaded_file)
            wav_filename = downloaded_filename.stem + ".wav"
            path_to_wav_file = f"{self.config.temp_dir}{wav_filename}"
            audio.export(path_to_wav_file, format="wav")
            logging.info(f"Converted to WAV {path_to_wav_file}")

            # Transcribe with speaker diarization
            with open(path_to_wav_file, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model=self.config.transcription_model,
                    file=audio_file,
                    response_format="diarized_json",
                    chunking_strategy="auto",
                )

            transcript_text = format_diarized_transcript(transcript)

            # Cleanup
            await delete_temp_files(self.config.temp_dir)

            await context.bot.edit_message_text(
                transcript_text,
                chat_id=placeholder.chat_id,
                message_id=placeholder.message_id,
                parse_mode=ParseMode.MARKDOWN,
            )
        finally:
            os.chdir(original_wd)


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main() -> None:
    """Main entry point for the bot application."""
    # Setup logging
    setup_logging()

    # Load configuration
    config = Config.from_env()

    # Initialize bot
    bot = Voice2TextBot(config)

    # Build application
    application = ApplicationBuilder().token(config.token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.start))
    application.add_handler(CommandHandler("summary", bot.summary))
    application.add_handler(CommandHandler("todo", bot.todo))
    application.add_handler(CommandHandler("important", bot.handle_important_command))
    application.add_handler(CommandHandler("english", bot.english))

    # Message handlers based on allowed usernames
    if config.allowed_usernames:
        # Build user filter
        usernames = [x for x in config.allowed_usernames if isinstance(x, str)]
        any_ids = [x for x in config.allowed_usernames if isinstance(x, (int, float))]
        user_ids = [int(x) for x in any_ids if x > 0]
        group_ids = [int(x) for x in any_ids if x < 0]

        user_filter = (
            filters.User(username=usernames)
            | filters.User(user_id=user_ids)
            | filters.Chat(chat_id=group_ids)
        )

        # Add file handlers
        application.add_handler(
            MessageHandler(
                (filters.VOICE | filters.AUDIO | filters.VIDEO) & user_filter,
                bot.handle_supported_files,
            )
        )
        application.add_handler(
            MessageHandler(
                filters.ALL & user_filter,
                bot.handle_unsupported_files,
            )
        )

    # Handler for non-allowed users
    application.add_handler(MessageHandler(filters.ALL, bot.handle_non_allowed_users))

    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
