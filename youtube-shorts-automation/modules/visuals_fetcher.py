import os
import time
import requests
from config import PEXELS_API_KEY, PIXABAY_API_KEY, OPENAI_API_KEY, LEONARDO_API_KEY, ASSETS_DIR, MAX_RETRIES, RETRY_DELAY_SECONDS
from modules.logger import get_logger

log = get_logger("visuals_fetcher")

def _baixar_arquivo(url: str, destino: str) -> bool:
    """Baixa um arquivo (vídeo ou imagem) de uma URL para o destino local."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            with open(destino, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            log.warning(f"Erro ao baixar arquivo (tentativa {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return False

def _gerar_imagem_openai(prompt: str) -> str:
    """Gera uma imagem vertical usando OpenAI DALL-E 3."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_aqui":
        return ""
        
    log.info(f"Gerando imagem DALL-E 3 para o prompt: '{prompt[:50]}...'")
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "dall-e-3",
        "prompt": f"Vertical 9:16 aspect ratio. {prompt}",
        "n": 1,
        "size": "1024x1792"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=45)
        response.raise_for_status()
        image_url = response.json()["data"][0]["url"]
        log.info("Imagem gerada via OpenAI com sucesso!")
        return image_url
    except Exception as e:
        log.error(f"Erro na OpenAI DALL-E: {e}")
        return ""

def _buscar_pexels(tema: str, num_videos: int) -> list:
    if not PEXELS_API_KEY or PEXELS_API_KEY == "sua_chave_aqui":
        return []
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": f"{tema} vertical",
        "orientation": "portrait",
        "per_page": 15,
        "size": "medium"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        videos = response.json().get("videos", [])
        links = []
        for video in videos[:num_videos * 2]:
            video_files = video.get("video_files", [])
            hd_vertical = [vf for vf in video_files if vf.get("quality") == "hd" and vf.get("width", 0) < vf.get("height", 0)]
            best = hd_vertical[0] if hd_vertical else (video_files[0] if video_files else None)
            if best and best.get("link"):
                links.append(best["link"])
            if len(links) >= num_videos:
                break
        return links
    except Exception as e:
        log.error(f"Erro Pexels: {e}")
        return []

def buscar_visuais(tema: str, num_videos: int = 2, prompts_imagem: list = None) -> list:
    """Busca ou gera visuais (Prioridade: IA Imagens DALL-E -> Pexels Videos)."""
    baixados = []
    
    # 1. Tenta Gerar Imagens com IA usando os prompts gerados pelo LLM
    if prompts_imagem and (OPENAI_API_KEY and OPENAI_API_KEY != "sua_chave_aqui"):
        log.info(f"Iniciando geração de {len(prompts_imagem)} imagens via IA...")
        for i, prompt in enumerate(prompts_imagem):
            img_url = _gerar_imagem_openai(prompt)
            if img_url:
                caminho = os.path.join(ASSETS_DIR, f"visual_ia_{i}.jpg")
                if _baixar_arquivo(img_url, caminho):
                    baixados.append(caminho)
                    log.info(f"Visual IA {i+1} salvo: {caminho}")
                    
    # Se conseguiu gerar as imagens IA para cobrir os prompts, retorna.
    if len(baixados) > 0:
        return baixados

    # 2. Fallback: Se não tem IA ou falhou, busca vídeos no Pexels
    log.warning("Fallback Visuals: Buscando vídeos em banco de imagens (Pexels)...")
    links_pexels = _buscar_pexels(tema, num_videos)
    
    if not links_pexels:
        log.error("Nenhum vídeo encontrado no Fallback.")
        return []

    for i, link in enumerate(links_pexels[:num_videos]):
        video_path = os.path.join(ASSETS_DIR, f"stock_video_{i}.mp4")
        if _baixar_arquivo(link, video_path):
            baixados.append(video_path)
            log.info(f"Stock Vídeo {i+1} salvo em: {video_path}")
            
    return baixados
