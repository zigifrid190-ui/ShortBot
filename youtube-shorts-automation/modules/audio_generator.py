import os
import asyncio
import json
import edge_tts
import whisper
import imageio_ffmpeg
from config import DEFAULT_VOICE, ASSETS_DIR

# Adiciona o ffmpeg (instalado pelo moviepy/imageio) ao PATH para o Whisper encontrar
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

def gerar_audio(roteiro: str, filename: str = "audio.mp3") -> str:
    """Gera áudio a partir do texto usando edge-tts."""
    audio_path = os.path.join(ASSETS_DIR, filename)
    print("[*] Gerando áudio com voz neural...")
    
    async def _gerar():
        communicate = edge_tts.Communicate(roteiro, DEFAULT_VOICE)
        await communicate.save(audio_path)
    
    asyncio.run(_gerar())
    print(f"[*] Áudio salvo em: {audio_path}")
    return audio_path

def gerar_legendas_whisper(audio_path: str) -> list:
    """Gera timestamps das palavras usando o OpenAI Whisper."""
    print("[*] Transcrevendo áudio com Whisper para sincronização...")
    # Usa o modelo 'base' (mais leve) ou 'small'
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True, language="pt")
    
    palavras = []
    for segment in result.get('segments', []):
        for word_info in segment.get('words', []):
            palavras.append({
                "word": word_info["word"].strip(),
                "start": word_info["start"],
                "end": word_info["end"]
            })
            
    # Salvar em JSON para debug/reuso
    json_path = audio_path.replace('.mp3', '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(palavras, f, ensure_ascii=False, indent=4)
        
    return palavras
