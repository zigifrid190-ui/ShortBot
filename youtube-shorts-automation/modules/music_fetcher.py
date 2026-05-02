import os
import random
import requests
import glob
from config import PIXABAY_API_KEY, ASSETS_DIR
from modules.logger import get_logger

log = get_logger("music_fetcher")

def buscar_musica_fundo(tema: str) -> str:
    """Busca uma música instrumental na Pixabay API ou usa uma música de fallback local."""
    log.info(f"Buscando música de fundo para o tema: '{tema}'")
    
    # Pasta de fallback para músicas locais
    music_dir = os.path.join(ASSETS_DIR, "music")
    os.makedirs(music_dir, exist_ok=True)
    
    # 1. Tentar Pixabay Audio API
    if PIXABAY_API_KEY and PIXABAY_API_KEY != "sua_chave_aqui":
        try:
            url = "https://pixabay.com/api/audio/"
            params = {
                "key": PIXABAY_API_KEY,
                "q": "lofi beat instrumental", # Sempre busca um lofi calmo para fundo
                "per_page": 10
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                hits = response.json().get("hits", [])
                if hits:
                    hit = random.choice(hits)
                    download_url = hit.get("audio")
                    if download_url:
                        music_path = os.path.join(music_dir, "bg_music.mp3")
                        log.info("Baixando música de fundo da Pixabay...")
                        
                        r = requests.get(download_url, stream=True, timeout=30)
                        r.raise_for_status()
                        with open(music_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                                
                        log.info(f"Música de fundo baixada: {music_path}")
                        return music_path
            else:
                log.warning("Falha ao buscar música na Pixabay API (Status: %s)", response.status_code)
        except Exception as e:
            log.error(f"Erro ao buscar música na Pixabay: {e}")

    # 2. Fallback: procurar qualquer .mp3 na pasta assets/music/
    log.warning("Tentando encontrar música local de fallback em assets/music/...")
    local_musics = glob.glob(os.path.join(music_dir, "*.mp3"))
    if local_musics:
        music_path = random.choice(local_musics)
        log.info(f"Música local encontrada: {music_path}")
        return music_path

    log.warning("Nenhuma música de fundo encontrada. O vídeo será gerado sem fundo musical.")
    return None
