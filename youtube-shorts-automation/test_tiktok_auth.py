"""
Script de teste isolado para autenticação OAuth do TikTok.
Executa APENAS o fluxo de login, sem gerar vídeo.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.tiktok_uploader import _autenticar_tiktok
from modules.logger import get_logger

log = get_logger("test_tiktok_auth")

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("TESTE ISOLADO DE AUTENTICAÇÃO TIKTOK")
    log.info("=" * 60)
    
    from config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI
    log.info(f"Client Key: {TIKTOK_CLIENT_KEY[:8]}...")
    log.info(f"Client Secret: {'***configurado***' if TIKTOK_CLIENT_SECRET else 'NÃO CONFIGURADO'}")
    log.info(f"Redirect URI: {TIKTOK_REDIRECT_URI}")
    
    token = _autenticar_tiktok()
    
    if token:
        log.info(f"✅ SUCESSO! Token obtido: {token[:15]}...")
        log.info("O upload para o TikTok está pronto para uso.")
    else:
        log.error("❌ FALHA na autenticação. Verifique:")
        log.error("  1. A Redirect URI no TikTok Developer Portal corresponde ao .env")
        log.error("  2. O localtunnel está ativo e encaminhando para porta 8080")
        log.error("  3. A app TikTok está aprovada para os escopos necessários")
