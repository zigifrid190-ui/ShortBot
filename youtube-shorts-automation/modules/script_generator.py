import os
import time
import json
import requests
from config import PROMPTS_DIR, OLLAMA_MODEL, MAX_RETRIES, RETRY_DELAY_SECONDS, GROQ_API_KEY, OPENAI_API_KEY
from modules.logger import get_logger

log = get_logger("script_generator")

def _parse_json(text: str) -> dict:
    try:
        # Tenta extrair o json caso venha com markdown ```json
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Erro ao parsear JSON: {e}")
        return {}

def _gerar_roteiro_openai(prompt: str) -> dict:
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_aqui":
        return {}
    log.info("Tentando gerar roteiro via OpenAI (GPT-4o-mini)...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "response_format": { "type": "json_object" },
        "messages": [
            {"role": "system", "content": "You are a viral YouTube Shorts scriptwriter. You must output only raw JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        log.info("Roteiro gerado via OpenAI com sucesso!")
        return _parse_json(content)
    except Exception as e:
        log.error(f"Erro no OpenAI: {e}")
        return {}

def _gerar_roteiro_groq(prompt: str) -> dict:
    if not GROQ_API_KEY or GROQ_API_KEY == "sua_chave_aqui":
        return {}
    log.info("Tentando gerar roteiro via Groq (Llama 3)...")
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You must output only raw JSON without markdown."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        log.info("Roteiro gerado via Groq com sucesso!")
        return _parse_json(content)
    except Exception as e:
        log.error(f"Erro no Groq: {e}")
        return {}

def _gerar_roteiro_ollama(prompt: str) -> dict:
    log.info(f"Tentando gerar via Ollama local ({OLLAMA_MODEL})...")
    try:
        from ollama import Client as OllamaClient
        client = OllamaClient()
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You must output only raw valid JSON."},
                {"role": "user", "content": prompt}
            ],
            format="json"
        )
        content = response.get('message', {}).get('content', '').strip()
        log.info("Roteiro gerado via Ollama com sucesso!")
        return _parse_json(content)
    except Exception as e:
        log.error(f"Erro no Ollama: {e}")
        return {}

def gerar_roteiro(tema: str) -> dict:
    """Gera roteiro com fallback: OpenAI -> Groq -> Ollama. Retorna dict."""
    prompt_path = os.path.join(PROMPTS_DIR, "roteiro_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Injeta instruções JSON no prompt
    json_instructions = """
    \n\nIMPORTANTE: Você deve retornar EXATAMENTE UM JSON com o seguinte formato:
    {
      "roteiro_texto": "O texto completo para a narração de voz (hook, corpo e CTA tudo junto)",
      "prompts_imagem": [
        "Prompt descritivo em ingles para IA gerar imagem 1",
        "Prompt descritivo em ingles para IA gerar imagem 2",
        "Prompt descritivo em ingles para IA gerar imagem 3"
      ],
      "clima_da_musica": "lofi hip hop calmo"
    }
    """
    prompt = prompt_template.format(tema=tema) + json_instructions
    log.info(f"Gerando roteiro JSON para o tema: {tema}")

    resultado = _gerar_roteiro_openai(prompt)
    if not resultado:
        resultado = _gerar_roteiro_groq(prompt)
    if not resultado:
        resultado = _gerar_roteiro_ollama(prompt)

    if resultado and "roteiro_texto" in resultado:
        return resultado
    else:
        log.error("Falha ao gerar roteiro JSON estruturado.")
        # Fallback de emergência caso tudo falhe e não venha JSON
        return {
            "roteiro_texto": f"Você sabia que {tema} é incrível? Curta e se inscreva para mais!",
            "prompts_imagem": [f"beautiful cinematic shot of {tema}"],
            "clima_da_musica": "calm ambient"
        }

def carregar_roteiro_arquivo(caminho: str) -> dict:
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
        # Tenta parsear como JSON se o arquivo for json, senão encapsula
        if conteudo.startswith("{"):
            return json.loads(conteudo)
        return {
            "roteiro_texto": conteudo,
            "prompts_imagem": ["aesthetic background"],
            "clima_da_musica": "lofi"
        }
    except Exception as e:
        log.error(f"Erro ao ler arquivo de roteiro: {e}")
        return None
