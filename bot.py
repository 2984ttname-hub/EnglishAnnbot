
import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from openai import OpenAI

# Read tokens from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Add it in your hosting environment variables.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it in your hosting environment variables.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("english-bot")

# Init Telegram + OpenAI clients
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
client = OpenAI(api_key=OPENAI_API_KEY)

# Helper: generate a tutor-style reply in English
def ask_tutor(message_text: str) -> str:
    try:
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly English tutor. Always reply in clear, simple English (B1-B2). If there are grammar mistakes, correct them and explain briefly in 1 sentence."},
                {"role": "user", "content": message_text},
            ],
            temperature=0.6,
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("Chat completion error: %s", e)
        return "Sorry, I had trouble generating a reply."

# Text handler
@dp.message_handler(content_types=types.ContentType.TEXT)
async def text_handler(message: types.Message):
    answer = ask_tutor(message.text)
    await message.answer(answer)

    # Also send audio (mp3) with the same answer
    try:
        audio_path = "reply.mp3"
        # Stream TTS to file
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=answer,
        ) as response:
            response.stream_to_file(audio_path)

        # Telegram will show this as regular audio (not a voice bubble)
        with open(audio_path, "rb") as f:
            await bot.send_audio(message.chat.id, f, title="Answer (TTS)")
    except Exception as e:
        logger.warning("TTS failed: %s", e)

# Voice handler (OGG Opus from Telegram)
@dp.message_handler(content_types=types.ContentType.VOICE)
async def voice_handler(message: types.Message):
    try:
        file = await bot.get_file(message.voice.file_id)
        voice_bytes = await bot.download_file(file.file_path)

        local_path = "voice.ogg"
        with open(local_path, "wb") as f:
            f.write(voice_bytes.read())

        # Transcribe with Whisper
        with open(local_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )

        user_text = transcript.text.strip() if hasattr(transcript, "text") else ""
        if not user_text:
            await message.answer("I couldn't hear that clearly. Could you repeat in English?")
            return

        answer = ask_tutor(user_text)
        await message.answer(f"You said: {user_text}\n\n{answer}")

        # TTS to MP3 (sent as regular audio)
        try:
            audio_path = "reply.mp3"
            with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=answer,
            ) as response:
                response.stream_to_file(audio_path)
            with open(audio_path, "rb") as f:
                await bot.send_audio(message.chat.id, f, title="Answer (TTS)")
        except Exception as e:
            logger.warning("TTS failed: %s", e)

    except Exception as e:
        logger.exception("Voice handler error: %s", e)
        await message.answer("Oops, something went wrong with the voice message.")

if __name__ == "__main__":
    # Long polling keeps the bot running on hosts like Render Worker
    executor.start_polling(dp, skip_updates=True)
