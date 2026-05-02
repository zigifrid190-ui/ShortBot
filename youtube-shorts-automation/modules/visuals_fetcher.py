import os
import time
import requests
from config import PEXELS_API_KEY, PIXABAY_API_KEY, ASSETS_DIR, MAX_RETRIES, RETRY_DELAY_SECONDS
from modules.logger import get_logger

log = get_logger("visuals_fetcher")


def _baixar_video(url: str, destino: str) -> bool:
    """Baixa um vídeo de uma URL para o destino local com retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            with open(destino, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            log.warning(f"Erro ao baixar vídeo (tentativa {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return False


def _buscar_pexels(tema: str, num_videos: int) -> list:
    """Busca vídeos verticais na Pexels API."""
    if not PEXELS_API_KEY or PEXELS_API_KEY == "sua_chave_aqui":
        log.warning("Chave da Pexels API não configurada. Pulando Pexels.")
        return []

    log.info(f"Buscando vídeos na Pexels para: '{tema}'")
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
    except Exception as e:
        log.error(f"Erro na API Pexels: {e}")
        return []

    videos = response.json().get("videos", [])
    if not videos:
        log.warning("Nenhum vídeo encontrado na Pexels.")
        return []

    links = []
    for video in videos[:num_videos * 2]:  # Pega o dobro para ter margem
        video_files = video.get("video_files", [])
        hd_vertical = [
            vf for vf in video_files
            if vf.get("quality") == "hd" and vf.get("width", 0) < vf.get("height", 0)
        ]
        best = hd_vertical[0] if hd_vertical else (video_files[0] if video_files else None)
        if best and best.get("link"):
            links.append(best["link"])
        if len(links) >= num_videos:
            break

    return links


def _buscar_pixabay(tema: str, num_videos: int) -> list:
    """Busca vídeos na Pixabay API (fonte alternativa gratuita)."""
    if not PIXABAY_API_KEY or PIXABAY_API_KEY == "sua_chave_aqui":
        log.warning("Chave da Pixabay API não configurada. Pulando Pixabay.")
        return []

    log.info(f"Buscando vídeos na Pixabay para: '{tema}'")
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": tema,
        "video_type": "all",
        "per_page": 10,
        "safesearch": "true",
        "lang": "pt"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
    except Exception as e:
        log.error(f"Erro na API Pixabay: {e}")
        return []

    hits = response.json().get("hits", [])
    if not hits:
        log.warning("Nenhum vídeo encontrado na Pixabay.")
        return []

    links = []
    for hit in hits[:num_videos]:
        video_data = hit.get("videos", {})
        # Prioriza large > medium > small
        for quality in ["large", "medium", "small"]:
            video_url = video_data.get(quality, {}).get("url")
            if video_url:
                links.append(video_url)
                break

    return links


def buscar_visuais(tema: str, num_videos: int = 2) -> list:
    """
    Busca vídeos verticais usando múltiplas APIs (Pexels + Pixabay).
    Retorna lista de caminhos dos vídeos baixados.
    """
    log.info(f"Buscando {num_videos} stock videos para o tema: '{tema}'")

    # Tenta Pexels primeiro, depois complementa com Pixabay
    links = _buscar_pexels(tema, num_videos)

    if len(links) < num_videos:
        faltam = num_videos - len(links)
        log.info(f"Complementando com Pixabay ({faltam} vídeos faltantes)...")
        links_pixabay = _buscar_pixabay(tema, faltam)
        links.extend(links_pixabay)

    if not links:
        log.error("Nenhum vídeo encontrado em nenhuma fonte.")
        return []

    # Baixar os vídeos
    baixados = []
    for i, link in enumerate(links[:num_videos]):
        video_path = os.path.join(ASSETS_DIR, f"stock_video_{i}.mp4")
        log.info(f"Baixando vídeo {i+1}/{min(num_videos, len(links))}...")

        if _baixar_video(link, video_path):
            baixados.append(video_path)
            log.info(f"Vídeo {i+1} salvo em: {video_path}")
        else:
            log.error(f"Falha ao baixar vídeo {i+1}.")

    log.info(f"Total de vídeos baixados: {len(baixados)}/{num_videos}")
    return baixados
