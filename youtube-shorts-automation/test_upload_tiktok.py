import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.tiktok_uploader import upload_tiktok
from modules.logger import get_logger

log = get_logger("test_upload")

if __name__ == "__main__":
    video_path = os.path.join("output", "short_tecnologias_futuristas_que_já__1.mp4")
    roteiro = "tecnologias futuristas que já existem e são incríveis"
    
    if os.path.exists(video_path):
        log.info(f"Testando upload de {video_path}")
        sucesso = upload_tiktok(video_path, roteiro, tema="tecnologias", publish_at=None)
        if sucesso:
            log.info("Upload para o TikTok concluído com sucesso!")
        else:
            log.error("Falha no upload para o TikTok.")
    else:
        log.error("Arquivo de vídeo não encontrado.")
