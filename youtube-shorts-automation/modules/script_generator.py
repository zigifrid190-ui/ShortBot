import os
import time
from config import PROMPTS_DIR, OLLAMA_MODEL, MAX_RETRIES, RETRY_DELAY_SECONDS, GROQ_API_KEY
from ollama import Client as OllamaClient
from groq import Groq
from modules.logger import get_logger

log = get_logger("script_generator")


def _gerar_roteiro_groq(prompt: str) -> str:
    """Tenta gerar roteiro usando a API ultra rápida do Groq (Llama 3)."""
    if not GROQ_API_KEY or GROQ_API_KEY == "sua_chave_aqui":
        log.warning("GROQ_API_KEY não configurada. Pulando API do Groq.")
        return ""

    log.info("Tentando gerar roteiro via API do Groq...")
    client = Groq(api_key=GROQ_API_KEY)
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            temperature=0.7,
            max_tokens=300
        )
        roteiro = response.choices[0].message.content.strip()
        log.info("Roteiro gerado via Groq com sucesso!")
        return roteiro
    except Exception as e:
        log.error(f"Erro ao gerar roteiro no Groq: {e}")
        return ""


def _gerar_roteiro_ollama(prompt: str) -> str:
    """Tenta gerar roteiro localmente via Ollama como fallback."""
    log.info(f"Tentando gerar roteiro via Ollama local ({OLLAMA_MODEL})... (isso pode demorar)")
    client = OllamaClient()

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

            log.info(f"Roteiro gerado via Ollama com sucesso!")
            return roteiro

        except ConnectionError:
            log.error(f"Ollama offline (tentativa {attempt}/{MAX_RETRIES}). Verifique se o Ollama está rodando.")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
        except Exception as e:
            log.error(f"Erro inesperado no Ollama: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    return ""


def gerar_roteiro(tema: str) -> str:
    """Gera um roteiro usando Groq (Rápido) ou Ollama (Local/Fallback)."""
    prompt_path = os.path.join(PROMPTS_DIR, "roteiro_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    prompt = prompt_template.format(tema=tema)
    log.info(f"Gerando roteiro para o tema: {tema}")

    # 1. Tenta API do Groq primeiro
    roteiro = _gerar_roteiro_groq(prompt)
    
    # 2. Se falhar, tenta Ollama
    if not roteiro:
        log.warning("Iniciando fallback para Ollama local...")
        roteiro = _gerar_roteiro_ollama(prompt)

    if roteiro:
        log.info(f"Roteiro final obtido ({len(roteiro.split())} palavras)")
    else:
        log.error("Falha ao gerar roteiro em todas as APIs.")

    return roteiro


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
