import os
import requests
from config import PEXELS_API_KEY, ASSETS_DIR

def buscar_visuais(tema: str, num_videos: int = 1) -> list:
    """Busca vídeos verticais usando a Pexels API e faz o download."""
    if not PEXELS_API_KEY or PEXELS_API_KEY == "sua_chave_aqui":
        print("[!] Chave da Pexels API não configurada.")
        return []
        
    print(f"[*] Buscando stock videos para o tema: '{tema}'")
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": f"{tema} vertical",
        "orientation": "portrait",
        "per_page": 15,
        "size": "medium"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Erro ao buscar vídeos na Pexels API: {e}")
        return []
        
    data = response.json()
    videos = data.get("videos", [])
    if not videos:
        print("[!] Nenhum vídeo encontrado.")
        return []
        
    baixados = []
    for i, video in enumerate(videos[:num_videos]):
        video_files = video.get("video_files", [])
        if not video_files:
            continue
            
        # Pega a versão vertical com melhor qualidade até HD
        hd_files = [vf for vf in video_files if vf.get("quality") == "hd" and vf.get("width", 0) < vf.get("height", 0)]
        file_to_download = hd_files[0] if hd_files else video_files[0]
        
        link = file_to_download.get("link")
        if link:
            video_path = os.path.join(ASSETS_DIR, f"stock_video_{i}.mp4")
            print(f"[*] Baixando vídeo {i+1}/{num_videos} do Pexels...")
            try:
                r = requests.get(link, stream=True)
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                baixados.append(video_path)
            except Exception as e:
                print(f"[!] Erro ao baixar o vídeo: {e}")
            
    return baixados
