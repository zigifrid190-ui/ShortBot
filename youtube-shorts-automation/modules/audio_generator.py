import os
import asyncio
import json
import edge_tts
import whisper
import imageio_ffmpeg
from config import (
    DEFAULT_VOICE, ASSETS_DIR, ELEVENLABS_API_KEY, 
    OPENAI_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_VOICE
)
from modules.logger import get_logger
import requests

log = get_logger("audio_generator")

# Adiciona o ffmpeg ao PATH para o Whisper encontrar
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

def _gerar_audio_elevenlabs(roteiro: str, audio_path: str) -> bool:
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "sua_chave_aqui":
        log.warning("Chave da ElevenLabs não configurada.")
        return False
        
    log.info("Tentando gerar áudio com ElevenLabs...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": roteiro,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        with open(audio_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        log.info(f"Áudio gerado via ElevenLabs com sucesso em: {audio_path}")
        return True
    except Exception as e:
        log.error(f"Erro na ElevenLabs API: {e}")
        return False

def _gerar_audio_openai(roteiro: str, audio_path: str) -> bool:
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_aqui":
        log.warning("Chave da OpenAI não configurada.")
        return False
        
    log.info("Tentando gerar áudio com OpenAI TTS...")
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "tts-1",
        "input": roteiro,
        "voice": OPENAI_VOICE
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        with open(audio_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        log.info(f"Áudio gerado via OpenAI TTS com sucesso em: {audio_path}")
        return True
    except Exception as e:
        log.error(f"Erro na OpenAI TTS API: {e}")
        return False

def _gerar_audio_edgetts(roteiro: str, audio_path: str) -> bool:
    log.info("Tentando gerar áudio com voz neural (edge-tts)...")
    try:
        async def _gerar():
            communicate = edge_tts.Communicate(roteiro, DEFAULT_VOICE)
            await communicate.save(audio_path)
        asyncio.run(_gerar())
        log.info(f"Áudio gerado via edge-tts em: {audio_path}")
        return True
    except Exception as e:
        log.error(f"Erro no edge-tts: {e}")
        return False

def gerar_audio(roteiro: str, filename: str = "audio.mp3") -> str:
    """Gera áudio com fallback: ElevenLabs -> OpenAI -> Edge-TTS."""
    audio_path = os.path.join(ASSETS_DIR, filename)
    
    # Tentativa 1: ElevenLabs
    if _gerar_audio_elevenlabs(roteiro, audio_path):
        return audio_path
        
    # Tentativa 2: OpenAI TTS
    log.warning("Iniciando Fallback 1: OpenAI TTS...")
    if _gerar_audio_openai(roteiro, audio_path):
        return audio_path
        
    # Tentativa 3: Edge-TTS
    log.warning("Iniciando Fallback 2: Edge-TTS...")
    if _gerar_audio_edgetts(roteiro, audio_path):
        return audio_path
        
    # Fallback Final: gTTS
    log.error("Todas as APIs principais falharam. Iniciando Fallback Final para gTTS...")
    try:
        from gtts import gTTS
        tts = gTTS(text=roteiro, lang='pt', tld='com.br')
        tts.save(audio_path)
        log.info(f"Áudio gerado com sucesso via gTTS (fallback) em: {audio_path}")
        return audio_path
    except Exception as e_fallback:
        log.error(f"Erro crítico no fallback (gTTS): {e_fallback}")
        raise


def gerar_legendas_whisper(audio_path: str) -> list:
    """Gera timestamps das palavras usando o OpenAI Whisper."""
    log.info("Transcrevendo áudio com Whisper para sincronização...")

    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True, language="pt")

        palavras = []
        for segment in result.get('segments', []):
            for word_info in segment.get('words', []):
                word = word_info["word"].strip()
                if word:
                    palavras.append({
                        "word": word,
                        "start": word_info["start"],
                        "end": word_info["end"]
                    })

        json_path = audio_path.replace('.mp3', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(palavras, f, ensure_ascii=False, indent=4)

        log.info(f"Transcrição concluída: {len(palavras)} palavras detectadas")
        return palavras

    except Exception as e:
        log.error(f"Erro na transcrição Whisper: {e}")
        raise
