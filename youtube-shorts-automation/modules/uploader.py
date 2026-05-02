import os
import re
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import BASE_DIR, YOUTUBE_CLIENT_SECRET_FILE
from modules.logger import get_logger

log = get_logger("uploader")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = os.path.join(BASE_DIR, "token.pickle")


def _autenticar_youtube():
    """Autentica via OAuth 2.0. Na primeira vez, abre o navegador."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            log.warning("Token expirado e não renovável. Reautenticando...")
            creds = None

    if not creds or not creds.valid:
        secret_path = os.path.join(BASE_DIR, YOUTUBE_CLIENT_SECRET_FILE)
        if not os.path.exists(secret_path):
            log.error(
                f"Arquivo '{YOUTUBE_CLIENT_SECRET_FILE}' não encontrado em {BASE_DIR}. "
                "Baixe-o no Google Cloud Console > APIs & Services > Credentials."
            )
            return None

        flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
        creds = flow.run_local_server(port=8080)

        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)
        log.info("Autenticação YouTube concluída e salva.")

    return creds


def _gerar_metadata_short(roteiro: str, tema: str = "") -> dict:
    """Gera título, descrição e tags otimizados para YouTube Shorts."""
    palavras = roteiro.split()
    # Título: primeiras 8 palavras + emoji
    titulo_base = " ".join(palavras[:8])
    titulo = f"🔥 {titulo_base}... #shorts"

    # Garantir que o título não ultrapasse 100 caracteres
    if len(titulo) > 100:
        titulo = titulo[:97] + "..."

    # Descrição com roteiro completo + CTAs
    descricao = (
        f"{roteiro}\n\n"
        f"---\n"
        f"📌 Se esse vídeo te ajudou, DEIXA O LIKE e SE INSCREVE!\n"
        f"🔔 Ative o sininho para não perder nenhum Short!\n\n"
        f"#shorts #viral #fyp"
    )

    # Tags baseadas no tema
    tema_limpo = re.sub(r'[^\w\s]', '', tema or titulo_base).lower()
    palavras_tema = tema_limpo.split()
    tags = ["shorts", "viral", "fyp", "dicas", "curiosidades"]
    tags.extend(palavras_tema[:5])
    tags = list(dict.fromkeys(tags))[:15]  # Remove duplicatas, max 15

    return {
        "titulo": titulo,
        "descricao": descricao,
        "tags": tags
    }


def upload_youtube(video_path: str, thumb_path: str, roteiro: str, tema: str = ""):
    """Faz upload do vídeo como YouTube Short via Data API v3."""
    log.info("Iniciando upload para o YouTube...")
    log.info(f"  Vídeo: {video_path}")
    log.info(f"  Thumb: {thumb_path}")

    creds = _autenticar_youtube()
    if not creds:
        log.error("Upload cancelado: autenticação falhou.")
        return None

    try:
        youtube = build("youtube", "v3", credentials=creds)
        metadata = _gerar_metadata_short(roteiro, tema)

        body = {
            "snippet": {
                "title": metadata["titulo"],
                "description": metadata["descricao"],
                "tags": metadata["tags"],
                "categoryId": "22",  # People & Blogs (funciona bem para Shorts)
                "defaultLanguage": "pt-BR",
                "defaultAudioLanguage": "pt-BR"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
                "madeForKids": False
            }
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5  # 5MB chunks
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        log.info("Fazendo upload do vídeo (isso pode levar alguns minutos)...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                log.info(f"  Upload: {progress}%")

        video_id = response.get("id")
        log.info(f"Upload concluído! ID: {video_id}")
        log.info(f"URL: https://youtube.com/shorts/{video_id}")

        # Definir a thumbnail
        if thumb_path and os.path.exists(thumb_path):
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumb_path, mimetype="image/jpeg")
                ).execute()
                log.info("Thumbnail definida com sucesso.")
            except Exception as e:
                log.warning(f"Não foi possível definir thumbnail (requer conta verificada): {e}")

        return video_id

    except Exception as e:
        log.error(f"Erro durante upload: {e}")
        return None
