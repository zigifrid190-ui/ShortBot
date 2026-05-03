import os
import random
import time
import requests
from config import PEXELS_API_KEY, PIXABAY_API_KEY, ASSETS_DIR, MAX_RETRIES, RETRY_DELAY_SECONDS
from modules.logger import get_logger

log = get_logger("visuals_fetcher")


def _baixar_arquivo(url: str, destino: str) -> bool:
    """Baixa um arquivo de uma URL para o destino local."""
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


def _buscar_videos_pexels(termo: str, quantidade: int = 3) -> list:
    """Busca vídeos verticais no Pexels usando um termo de busca específico."""
    if not PEXELS_API_KEY or PEXELS_API_KEY == "sua_chave_aqui":
        return []

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": f"{termo} vertical",
        "orientation": "portrait",
        "per_page": 15,
        "size": "medium"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        videos = response.json().get("videos", [])

        links = []
        for video in videos:
            video_files = video.get("video_files", [])
            # Prioriza HD vertical
            hd_vertical = [
                vf for vf in video_files
                if vf.get("quality") == "hd" and vf.get("width", 0) < vf.get("height", 0)
            ]
            # Fallback para SD vertical
            sd_vertical = [
                vf for vf in video_files
                if vf.get("width", 0) < vf.get("height", 0)
            ]
            best = hd_vertical[0] if hd_vertical else (sd_vertical[0] if sd_vertical else None)
            if best and best.get("link"):
                links.append(best["link"])

        # Embaralha para não repetir sempre os mesmos clipes
        random.shuffle(links)
        return links[:quantidade]

    except Exception as e:
        log.error(f"Erro Pexels ({termo}): {e}")
        return []


def _buscar_videos_pixabay(termo: str, quantidade: int = 3) -> list:
    """Busca vídeos no Pixabay como fallback."""
    if not PIXABAY_API_KEY or PIXABAY_API_KEY == "sua_chave_aqui":
        return []

    url = "https://pixabay.com/api/videos/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": termo,
        "per_page": 10,
        "safesearch": "true",
        "video_type": "film"
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        hits = response.json().get("hits", [])

        links = []
        for hit in hits:
            video_data = hit.get("videos", {}).get("medium", {})
            if video_data.get("url"):
                links.append(video_data["url"])

        random.shuffle(links)
        return links[:quantidade]

    except Exception as e:
        log.error(f"Erro Pixabay ({termo}): {e}")
        return []


def buscar_visuais(tema: str, num_videos: int = 3, prompts_imagem: list = None, busca_videos: list = None) -> list:
    """
    Busca B-Roll em VÍDEO (não imagens estáticas) usando termos inteligentes.
    
    Prioridade:
    1. Termos de busca gerados pelo LLM (campo 'busca_videos' do JSON)
    2. Fallback: usa o tema como termo de busca genérico
    
    Fontes: Pexels (principal) -> Pixabay (fallback)
    """
    # Define os termos de busca
    termos = busca_videos or prompts_imagem or [tema]
    baixados = []

    log.info(f"Buscando {len(termos)} B-Rolls dinâmicos no Pexels...")

    for i, termo in enumerate(termos):
        log.info(f"  Buscando vídeo para: '{termo}'")

        # Tenta Pexels primeiro
        links = _buscar_videos_pexels(termo, quantidade=1)

        # Fallback Pixabay
        if not links:
            log.warning(f"  Pexels sem resultados para '{termo}'. Tentando Pixabay...")
            links = _buscar_videos_pixabay(termo, quantidade=1)

        # Fallback com tema genérico
        if not links:
            log.warning(f"  Pixabay também falhou. Buscando com tema genérico: '{tema}'")
            links = _buscar_videos_pexels(tema, quantidade=1)

        if links:
            video_path = os.path.join(ASSETS_DIR, f"broll_{i}.mp4")
            if _baixar_arquivo(links[0], video_path):
                baixados.append(video_path)
                log.info(f"  ✅ B-Roll {i+1} salvo: {video_path}")
            else:
                log.warning(f"  Falha ao baixar B-Roll {i+1}")
        else:
            log.warning(f"  Nenhum vídeo encontrado para '{termo}'")

    if not baixados:
        log.error("Nenhum B-Roll encontrado em nenhuma fonte!")

    return baixados
