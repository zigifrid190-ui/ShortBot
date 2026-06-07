import os
import time
import pickle
import requests
import webbrowser
import subprocess
import secrets
import hashlib
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_TOKEN_PATH, TIKTOK_REDIRECT_URI
from modules.logger import get_logger

log = get_logger("tiktok_uploader")


class TikTokOAuthHandler(BaseHTTPRequestHandler):
    """Handler HTTP para capturar o código de autenticação da URL de redirecionamento."""
    def do_GET(self):
        log.info(f"Requisição recebida: {self.path}")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            log.info(f"Código de autorização capturado com sucesso! (code={self.server.auth_code[:10]}...)")
            html = """
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px; background-color: #010101; color: #ffffff;">
                    <h1 style="color: #fe2c55;">Conexão com o TikTok bem-sucedida!</h1>
                    <p style="font-size: 18px;">O ShortBot obteve a autorização de publicação.</p>
                    <p style="color: #8a8a8a;">Você pode fechar esta aba do navegador agora.</p>
                </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        elif "error" in params:
            error_desc = params.get("error_description", ["Desconhecido"])[0]
            log.error(f"TikTok retornou erro: {params['error'][0]} - {error_desc}")
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px; background-color: #010101; color: #ffffff;">
                    <h1 style="color: #fe2c55;">Erro de Autenticação</h1>
                    <p style="font-size: 18px;">{error_desc}</p>
                </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
            self.server.auth_code = "__ERROR__"
        else:
            log.warning(f"Requisição recebida sem código. Params: {params}")
            html = """
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px; background-color: #010101; color: #ffffff;">
                    <h1 style="color: #fe2c55;">Aguardando...</h1>
                    <p style="font-size: 18px;">Código de autorização ainda não recebido.</p>
                </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        log.debug(f"HTTP: {format % args}")


def _autenticar_tiktok():
    """Realiza autenticação via OAuth 2.0 Oficial do TikTok."""
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET:
        log.error("TIKTOK_CLIENT_KEY ou TIKTOK_CLIENT_SECRET não configurados no arquivo .env.")
        return None

    token_data = None

    # 1. Carregar token existente se houver
    if os.path.exists(TIKTOK_TOKEN_PATH):
        try:
            with open(TIKTOK_TOKEN_PATH, "rb") as f:
                token_data = pickle.load(f)
        except Exception as e:
            log.warning(f"Erro ao carregar token do TikTok: {e}. Reautenticando...")

    # 2. Verificar expiração e tentar refresh
    if token_data:
        expires_at = token_data.get("expires_at", 0)
        refresh_token = token_data.get("refresh_token")
        
        # Se expira nos próximos 5 minutos, faz refresh
        if time.time() + 300 >= expires_at and refresh_token:
            log.info("Renovando token de acesso do TikTok...")
            try:
                url = "https://open.tiktokapis.com/v2/oauth/token/"
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                data = {
                    "client_key": TIKTOK_CLIENT_KEY,
                    "client_secret": TIKTOK_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
                r = requests.post(url, data=data, headers=headers, timeout=15)
                r.raise_for_status()
                res_json = r.json()
                
                # Se obtivemos novo token com sucesso
                if "access_token" in res_json:
                    token_data = {
                        "access_token": res_json["access_token"],
                        "refresh_token": res_json.get("refresh_token", refresh_token),
                        "expires_at": time.time() + res_json.get("expires_in", 86400),
                        "open_id": res_json.get("open_id")
                    }
                    with open(TIKTOK_TOKEN_PATH, "wb") as f:
                        pickle.dump(token_data, f)
                    log.info("Token do TikTok renovado com sucesso.")
                    return token_data["access_token"]
                else:
                    log.warning(f"Erro ao renovar token (resposta inválida): {res_json}. Solicitando novo login...")
                    token_data = None
            except Exception as e:
                log.error(f"Erro na requisição de refresh token: {e}. Tentando novo login...")
                token_data = None
        else:
            # Token ainda é válido
            return token_data["access_token"]

    # 3. Fluxo de Autorização Completo (Primeira Vez ou Token Expirado/Inválido)
    if not token_data:
        log.info("Iniciando fluxo de login OAuth 2.0 do TikTok...")
        redirect_uri = TIKTOK_REDIRECT_URI
        log.info(f"Redirect URI configurada: {redirect_uri}")
        
        # Gerar par PKCE (code_verifier e code_challenge)
        code_verifier = secrets.token_urlsafe(64)
        sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')
        
        # Montar URL de autorização do TikTok
        # Escopos: user.info.basic, video.upload, video.publish
        scope = "user.info.basic,video.upload,video.publish"
        state = "shortbot_csrf_state"
        auth_url = (
            f"https://www.tiktok.com/v2/auth/authorize/?"
            f"client_key={TIKTOK_CLIENT_KEY}&scope={scope}&response_type=code"
            f"&redirect_uri={redirect_uri}&state={state}"
            f"&code_challenge={code_challenge}&code_challenge_method=S256"
        )

        # Iniciar servidor local na porta 8080 (0.0.0.0 para aceitar conexões externas/localtunnel)
        server = HTTPServer(("0.0.0.0", 8080), TikTokOAuthHandler)
        server.auth_code = None
        server.timeout = 300  # timeout de 5 minutos

        log.info(f"Servidor HTTP escutando em 0.0.0.0:8080")
        log.info("Abrindo o Brave Browser para autorização do TikTok. Aguardando login...")
        log.info(f"URL de autorização: {auth_url}")
        
        # Abrir no Brave Browser (preferência do usuário)
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        try:
            if os.path.exists(brave_path):
                subprocess.Popen([brave_path, auth_url])
                log.info("Brave Browser aberto com sucesso.")
            else:
                log.warning("Brave não encontrado, usando navegador padrão.")
                webbrowser.open(auth_url)
        except Exception as e:
            log.warning(f"Erro ao abrir Brave: {e}. Usando navegador padrão.")
            webbrowser.open(auth_url)

        # Aguardar requisição com o código de autorização
        timeout_at = time.time() + 300  # 5 minutos de timeout
        while server.auth_code is None:
            try:
                if time.time() > timeout_at:
                    log.error("Timeout de 5 minutos atingido aguardando autorização do TikTok.")
                    server.server_close()
                    return None
                server.handle_request()
            except KeyboardInterrupt:
                log.info("Autenticação cancelada pelo usuário.")
                server.server_close()
                return None

        if server.auth_code == "__ERROR__":
            log.error("Autenticação falhou — TikTok retornou um erro.")
            server.server_close()
            return None

        code = server.auth_code
        server.server_close()

        # Trocar código de autorização pelo token de acesso
        log.info("Trocando código de autorização pelo token final...")
        try:
            url = "https://open.tiktokapis.com/v2/oauth/token/"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier
            }
            r = requests.post(url, data=data, headers=headers, timeout=15)
            r.raise_for_status()
            res_json = r.json()

            if "access_token" in res_json:
                token_data = {
                    "access_token": res_json["access_token"],
                    "refresh_token": res_json.get("refresh_token"),
                    "expires_at": time.time() + res_json.get("expires_in", 86400),
                    "open_id": res_json.get("open_id")
                }
                with open(TIKTOK_TOKEN_PATH, "wb") as f:
                    pickle.dump(token_data, f)
                log.info("Login do TikTok realizado e token salvo com sucesso.")
                return token_data["access_token"]
            else:
                log.error(f"Erro na resposta do token do TikTok: {res_json}")
                return None
        except Exception as e:
            log.error(f"Falha ao solicitar token do TikTok: {e}")
            return None


def upload_tiktok(video_path: str, roteiro: str, tema: str = "", publish_at: str = None, legenda_personalizada: str = None) -> bool:
    """
    Envia o vídeo para o TikTok via API Oficial v2 de forma resiliente.
    """
    log.info("Iniciando processo de upload para o TikTok...")
    if not os.path.exists(video_path):
        log.error(f"Arquivo de vídeo não encontrado para upload: {video_path}")
        return False

    access_token = _autenticar_tiktok()
    if not access_token:
        log.error("Cancelando upload para o TikTok: falha na autenticação.")
        return False

    # Preparar legenda do vídeo (máximo 2200 caracteres no TikTok)
    if legenda_personalizada:
        legenda = legenda_personalizada
    else:
        palavras = roteiro.split()
        titulo_base = " ".join(palavras[:8])
        legenda = f"🔥 {titulo_base}...\n\n#shorts #fyp #viral"
        if tema:
            legenda += f" #{tema.lower().replace(' ', '')}"

    if len(legenda) > 2200:
        legenda = legenda[:2195] + "..."

    video_size = os.path.getsize(video_path)

    # 1. Inicializar Post (Tentando como Público primeiro)
    init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }

    # Tentativas de níveis de privacidade
    # Se a conta não for auditada/aprovada, PUBLIC_TO_EVERYONE falhará com erro de escopo.
    # O fallback automático para SELF_ONLY (Rascunho Privado) garante que o upload funcione de qualquer forma.
    privacy_levels = ["PUBLIC_TO_EVERYONE", "SELF_ONLY"]
    upload_url = None
    publish_id = None

    # Calcular tamanho do chunk e quantidade de chunks de acordo com as especificações do TikTok
    import math
    MIN_CHUNK_SIZE = 5 * 1024 * 1024       # 5 MB
    DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB

    if video_size < MIN_CHUNK_SIZE:
        resolved_chunk_size = video_size
        total_chunk_count = 1
    else:
        resolved_chunk_size = DEFAULT_CHUNK_SIZE
        total_chunk_count = max(1, math.floor(video_size / resolved_chunk_size))

    for privacy in privacy_levels:
        body = {
            "post_info": {
                "title": legenda,
                "privacy_level": privacy,
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": resolved_chunk_size,
                "total_chunk_count": total_chunk_count
            }
        }

        try:
            log.info(f"Tentando inicializar post no TikTok com privacidade: {privacy}...")
            r = requests.post(init_url, json=body, headers=headers, timeout=15)
            res_json = r.json()
            
            # Verificar erros
            error_code = res_json.get("error", {}).get("code", "ok")
            if error_code == "ok" or error_code == "spam_warning":  # spam_warning às vezes é retornado mas permite o post
                upload_url = res_json.get("data", {}).get("upload_url")
                publish_id = res_json.get("data", {}).get("publish_id")
                log.info(f"Post inicializado com sucesso (Privacidade definida: {privacy})")
                break
            else:
                log.warning(f"Falha ao iniciar post como {privacy} (Erro: {error_code} - {res_json.get('error', {}).get('message')})")
        except Exception as e:
            log.error(f"Erro na requisição de inicialização ({privacy}): {e}")

    if not upload_url:
        log.error("Falha fatal na inicialização do post do TikTok em todos os níveis de privacidade.")
        return False

    # 2. Upload do binário via PUT em chunks sequenciais
    log.info(f"Iniciando envio do arquivo binário em {total_chunk_count} chunk(s) para a CDN do TikTok...")
    try:
        with open(video_path, "rb") as f:
            for i in range(total_chunk_count):
                start_byte = i * resolved_chunk_size
                if i == total_chunk_count - 1:
                    # O último chunk lê todo o restante do arquivo
                    chunk_data = f.read()
                    end_byte = video_size - 1
                else:
                    chunk_data = f.read(resolved_chunk_size)
                    end_byte = start_byte + len(chunk_data) - 1

                chunk_length = len(chunk_data)
                put_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(chunk_length),
                    "Content-Range": f"bytes {start_byte}-{end_byte}/{video_size}"
                }
                
                log.info(f"Enviando chunk {i+1}/{total_chunk_count} ({chunk_length} bytes, range: {start_byte}-{end_byte})...")
                r = requests.put(upload_url, data=chunk_data, headers=put_headers, timeout=120)
                
                if not (200 <= r.status_code < 300):
                    log.error(f"Falha ao enviar o chunk {i+1} para a CDN. Status HTTP: {r.status_code}. Resposta: {r.text}")
                    return False

        log.info("Todos os chunks do vídeo foram enviados com sucesso para a CDN do TikTok!")
        log.info(f"Upload concluído! ID de Publicação: {publish_id}")
        return True
    except Exception as e:
        log.error(f"Erro durante o envio binário do vídeo do TikTok: {e}")
        return False
