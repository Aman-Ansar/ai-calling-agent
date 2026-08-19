from config import NGROK_URL, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID_EN, ELEVENLABS_VOICE_ID_AR
ngrok_url = NGROK_URL
import os
import requests

def synthesize_speech(text, filename="answer", language="en"):
    """
    Converts text to speech using ElevenLabs and saves it as an MP3 file.
    Uses the multilingual model so Arabic text is pronounced correctly, and
    picks a voice based on the requested language ("ar" or "en").

    :param text: Text to be converted to speech.
    :param filename: Name of the file to save the audio to.
    :param language: "ar" or "en" — selects the right voice for that language.
    :return: Path to the saved audio file, or None on failure.
    """
    try:
        CHUNK_SIZE = 1024
        voice_id = ELEVENLABS_VOICE_ID_AR if language == "ar" else ELEVENLABS_VOICE_ID_EN
        if not voice_id:
            print(f"[TTS ERROR] No ElevenLabs voice ID configured for language='{language}'. "
                  f"Check ELEVENLABS_VOICE_ID_EN / ELEVENLABS_VOICE_ID_AR in .env")
            return None

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY,
        }

        data = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",  # much faster than multilingual_v2, still supports Arabic + English
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        response = None
        last_err = None
        for attempt in range(2):
            try:
                response = requests.post(url, json=data, headers=headers, timeout=20)
                if response.ok:
                    break
                last_err = f"HTTP {response.status_code}: {response.text[:300]}"
            except Exception as req_err:
                last_err = str(req_err)
            print(f"[TTS RETRY] Attempt {attempt + 1} failed: {last_err}")
        if response is None or not response.ok:
            print(f"[TTS ERROR] ElevenLabs failed after retries: {last_err}")
            return None

        os.makedirs("./static", exist_ok=True)
        with open(f"./static/{filename}.mp3", 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return filename
    except Exception as e:
        print(f"[TTS ERROR] Exception generating speech: {e}")
        return None
