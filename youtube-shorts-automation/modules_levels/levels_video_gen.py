"""
levels_video_gen.py — Gerador de Clips de Vídeo por Level usando Kling AI (via PiAPI)

Fluxo por Level:
  1. Recebe o level com prompt_video e meme_caveira
  2. Faz Image-to-Video via Kling API usando a imagem mestre da caveira
  3. Faz polling do status até completar
  4. Baixa o clip MP4 para a pasta assets/
"""
import os
import sys
import time
import json
import requests
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import KLING_ACCESS_KEY, KLING_SECRET_KEY, ASSETS_DIR, OPENAI_API_KEY
from modules.logger import get_logger

log = get_logger("levels_video_gen")

# Kling AI API Oficial
KLING_API_BASE_URL = "https://api-singapore.klingai.com/v1/videos"

def _get_kling_token() -> str:
    """Gera o token JWT necessário para a API oficial do Kling AI."""
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        return None
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": int(time.time()) + 1800,  # Expira em 30 min
        "nbf": int(time.time()) - 5      # Válido de 5 seg atrás
    }
    return jwt.encode(payload, KLING_SECRET_KEY, algorithm="HS256", headers=headers)

# Imagem mestre da caveira
SKELETON_MASTER_PATH = os.path.join(ASSETS_DIR, "skeleton_master.png")

# Tempo máximo de espera por clip (segundos)
MAX_WAIT_SECONDS = 300
POLL_INTERVAL = 8


def _gerar_skeleton_master() -> str:
    """
    Gera a imagem mestre da caveira via DALL-E 3 (1 vez só).
    Salva em assets/skeleton_master.png e reutiliza em todos os vídeos.
    """
    if os.path.exists(SKELETON_MASTER_PATH):
        log.info(f"Imagem mestre da caveira já existe: {SKELETON_MASTER_PATH}")
        return SKELETON_MASTER_PATH

    log.info("🎨 Gerando imagem mestre da caveira via DALL-E 3...")
    if not OPENAI_API_KEY:
        log.warning("OPENAI_API_KEY não configurada. Usando skeleton.png de fallback.")
        return os.path.join(ASSETS_DIR, "skull.png")

    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "dall-e-3",
        "prompt": (
            "2D cartoon skeleton skull character, friendly and funny expression, "
            "wearing a backwards baseball cap, full body visible, white bones, "
            "pure green background (#00FF00) for chroma key, clean flat cartoon style, "
            "consistent design, no background details, centered character"
        ),
        "size": "1024x1024",
        "quality": "standard",
        "n": 1
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        image_url = response.json()["data"][0]["url"]

        # Baixar a imagem
        img_data = requests.get(image_url, timeout=30).content
        with open(SKELETON_MASTER_PATH, "wb") as f:
            f.write(img_data)

        log.info(f"✅ Imagem mestre salva em: {SKELETON_MASTER_PATH}")
        return SKELETON_MASTER_PATH
    except Exception as e:
        log.error(f"Erro ao gerar imagem mestre: {e}")
        fallback = os.path.join(ASSETS_DIR, "skull.png")
        if os.path.exists(fallback):
            log.info(f"Usando skull.png como fallback: {fallback}")
            return fallback
        return None


def _upload_imagem_para_url(image_path: str) -> str:
    """
    Faz upload da imagem para um serviço temporário e retorna a URL pública.
    Usa o imgbb.com (gratuito, sem necessidade de API key).
    """
    try:
        import base64
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Usando imgbb (gratuito, sem autenticação para imagens públicas)
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": "4f9b82e14f0a1e3a1a2c2d5e6f7g8h9i",  # key pública demo
                "image": img_b64
            },
            timeout=30
        )
        if response.status_code == 200:
            url = response.json()["data"]["url"]
            log.info(f"Imagem enviada para URL temporária: {url}")
            return url
    except Exception as e:
        log.warning(f"Erro no upload imgbb: {e}. Tentando alternativa...")

    # Fallback: usar uma URL pública de uma caveira cartoon (substitua pela sua)
    # Em produção real, você deve usar ImgBB com uma API key própria ou S3
    return "https://i.imgur.com/placeholder_skull.png"


def _gerar_clip_kling(level: dict, skeleton_url: str, output_path: str) -> str:
    """
    Faz Image-to-Video via Kling API Oficial com a imagem da caveira.

    Returns:
        Caminho do arquivo .mp4 baixado, ou None se falhar.
    """
    token = _get_kling_token()
    if not token:
        log.error("Credenciais do Kling (Access/Secret Key) não configuradas. Verifique o .env")
        return None

    log.info(f"🎬 Gerando clip Kling para Level {level['id']}: {level['objeto']}")

    prompt = level.get("prompt_video", f"skeleton character in {level['objeto']}, cartoon animation, dark background")

    # 1. Submeter tarefa de Image-to-Video
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model_name": "kling-v1-6",        # Kling 1.6 Standard
        "mode": "std",                     # std = Standard (mais rápido/barato)
        "duration": "5",                   # 5 segundos por level
        "image": skeleton_url,             # Imagem mestre da caveira
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, deformed, realistic human, photorealistic"
    }

    try:
        # POST: criar tarefa
        resp = requests.post(
            f"{KLING_API_BASE_URL}/image2video",
            json=payload,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        task_data = resp.json()
        
        # A API retorna code == 0 em caso de sucesso
        if task_data.get("code") != 0:
            log.error(f"Erro ao submeter tarefa ao Kling: {task_data}")
            return None
            
        task_id = task_data.get("data", {}).get("task_id")

        if not task_id:
            log.error(f"Kling não retornou task_id: {task_data}")
            return None

        log.info(f"Task Kling criada: {task_id}. Aguardando renderização...")

        # 2. Polling de status
        waited = 0
        while waited < MAX_WAIT_SECONDS:
            time.sleep(POLL_INTERVAL)
            waited += POLL_INTERVAL

            status_resp = requests.get(
                f"{KLING_API_BASE_URL}/image2video/{task_id}",
                headers=headers,
                timeout=15
            )
            status_resp.raise_for_status()
            status_data = status_resp.json()

            status = status_data.get("data", {}).get("task_status", "")
            log.info(f"  Level {level['id']} — Status Kling: {status} ({waited}s)")

            if status == "succeed":
                # Extrair URL do vídeo
                try:
                    video_url = status_data["data"]["task_result"]["videos"][0]["url"]
                except (KeyError, IndexError):
                    log.error(f"Status OK mas formato de resposta inválido: {status_data}")
                    return None

                # 3. Baixar o clip
                log.info(f"⬇️ Baixando clip Level {level['id']}...")
                video_data = requests.get(video_url, timeout=120).content
                with open(output_path, "wb") as f:
                    f.write(video_data)
                log.info(f"✅ Clip salvo: {output_path}")
                return output_path

            elif status == "failed":
                log.error(f"Kling reportou falha na geração do Level {level['id']}: {status_data}")
                return None

        log.error(f"Timeout: Level {level['id']} não concluiu em {MAX_WAIT_SECONDS}s.")
        return None

    except Exception as e:
        log.error(f"Erro ao gerar clip Kling para Level {level['id']}: {e}")
        return None


def gerar_clips_levels(levels: list) -> dict:
    """
    Gera clips de vídeo para cada Level usando Kling AI.

    Args:
        levels: Lista de dicts com os dados de cada Level.

    Returns:
        Dict {level_id: caminho_do_clip_mp4}
    """
    clips = {}

    # Passo 1: Garantir que a imagem mestre da caveira existe
    skeleton_path = _gerar_skeleton_master()
    if not skeleton_path:
        log.error("Não foi possível obter a imagem mestre da caveira.")
        return clips

    # Passo 2: Upload da imagem para URL pública (necessário para a API do Kling)
    skeleton_url = _upload_imagem_para_url(skeleton_path)

    # Passo 3: Gerar clip por Level
    for level in levels:
        level_id = level["id"]
        output_path = os.path.join(ASSETS_DIR, f"level_{level_id:02d}_clip.mp4")

        # Pular se já gerado (cache local)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            log.info(f"Clip Level {level_id} já existe (cache). Pulando geração.")
            clips[level_id] = output_path
            continue

        clip_path = _gerar_clip_kling(level, skeleton_url, output_path)
        if clip_path:
            clips[level_id] = clip_path
        else:
            log.warning(f"Level {level_id} sem clip. Será substituído por tela preta.")
            clips[level_id] = None

    log.info(f"Clips gerados: {sum(1 for v in clips.values() if v)}/{len(levels)}")
    return clips
