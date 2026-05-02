import os
import time
from config import PROMPTS_DIR, OLLAMA_MODEL, MAX_RETRIES, RETRY_DELAY_SECONDS
from ollama import Client
from modules.logger import get_logger

log = get_logger("script_generator")


def gerar_roteiro(tema: str) -> str:
    """Gera um roteiro para YouTube Shorts usando um modelo local no Ollama."""
    prompt_path = os.path.join(PROMPTS_DIR, "roteiro_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    prompt = prompt_template.format(tema=tema)
    log.info(f"Gerando roteiro para o tema: {tema}")

    client = Client()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            roteiro = response.get('message', {}).get('content', '').strip()

            if not roteiro:
                log.warning(f"Roteiro vazio retornado (tentativa {attempt}/{MAX_RETRIES})")
                continue

            log.info(f"Roteiro gerado com sucesso ({len(roteiro.split())} palavras)")
            return roteiro

        except ConnectionError:
            log.error(f"Ollama offline (tentativa {attempt}/{MAX_RETRIES}). Verifique se o Ollama está rodando.")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
        except Exception as e:
            log.error(f"Erro inesperado ao gerar roteiro: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    log.error("Falha ao gerar roteiro após todas as tentativas.")
    return ""


def carregar_roteiro_arquivo(caminho: str) -> str:
    """Carrega um roteiro a partir de um arquivo de texto."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            roteiro = f.read().strip()
        log.info(f"Roteiro carregado do arquivo: {caminho} ({len(roteiro.split())} palavras)")
        return roteiro
    except FileNotFoundError:
        log.error(f"Arquivo de roteiro não encontrado: {caminho}")
        return ""
    except Exception as e:
        log.error(f"Erro ao ler arquivo de roteiro: {e}")
        return ""
