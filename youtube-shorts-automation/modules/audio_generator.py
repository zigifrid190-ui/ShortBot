import os
import asyncio
import json
import edge_tts
import whisper
import imageio_ffmpeg
from config import DEFAULT_VOICE, ASSETS_DIR
from modules.logger import get_logger

log = get_logger("audio_generator")

# Adiciona o ffmpeg ao PATH para o Whisper encontrar
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())


def gerar_audio(roteiro: str, filename: str = "audio.mp3") -> str:
    """Gera áudio a partir do texto usando edge-tts (principal) ou gTTS (fallback)."""
    audio_path = os.path.join(ASSETS_DIR, filename)
    log.info("Tentando gerar áudio com voz neural (edge-tts)...")

    try:
        async def _gerar():
            communicate = edge_tts.Communicate(roteiro, DEFAULT_VOICE)
            await communicate.save(audio_path)

        asyncio.run(_gerar())
        log.info(f"Áudio gerado com edge-tts e salvo em: {audio_path}")
        return audio_path
    except Exception as e:
        log.error(f"Erro no edge-tts: {e}. Iniciando fallback para gTTS...")
        try:
            from gtts import gTTS
            tts = gTTS(text=roteiro, lang='pt', tld='com.br')
            tts.save(audio_path)
            log.info(f"Áudio gerado com sucesso via gTTS (fallback) em: {audio_path}")
            return audio_path
        except Exception as e_fallback:
            log.error(f"Erro no fallback (gTTS): {e_fallback}")
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
