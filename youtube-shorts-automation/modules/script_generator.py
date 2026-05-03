import os
import json
import requests
from config import PROMPTS_DIR, OLLAMA_MODEL, GROQ_API_KEY, OPENAI_API_KEY
from modules.logger import get_logger

log = get_logger("script_generator")


def _parse_json(text: str) -> dict:
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Erro ao parsear JSON: {e}")
        return {}


# ============================================================
# PIPELINE MULTI-AGENTE: Llama 3 (Criativo) + GPT-4o (Editor)
# ============================================================

def _gerar_rascunho_groq(prompt: str) -> str:
    """Llama 3 via Groq: Roteirista Chefe. Gera texto criativo e agressivo."""
    if not GROQ_API_KEY or GROQ_API_KEY == "sua_chave_aqui":
        return ""
    log.info("⚡ Llama 3 (Groq) escrevendo rascunho criativo...")
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é um roteirista BRUTAL de YouTube Shorts virais brasileiros. Seu trabalho é criar ganchos que PARAM o scroll. Seja direto, agressivo e polêmico."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.85,
        )
        rascunho = response.choices[0].message.content.strip()
        log.info(f"Rascunho Llama 3 gerado! ({len(rascunho.split())} palavras)")
        return rascunho
    except Exception as e:
        log.error(f"Erro no Groq (rascunho): {e}")
        return ""


def _refinar_com_gpt(rascunho: str, tema: str) -> dict:
    """GPT-4o-mini: Diretor de Produção. Lapida o rascunho e gera JSON estruturado."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_aqui":
        return {}
    log.info("🎬 GPT-4o-mini refinando e extraindo JSON de produção...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    system_prompt = """Você é um DIRETOR DE PRODUÇÃO de YouTube Shorts (Especialista em Algoritmo 2026). Você recebe um rascunho de roteiro e deve:
1. VERIFICAR que o gancho (primeiras 2 frases) contém a PALAVRA-CHAVE do tema. Se não contiver, reescreva o gancho incluindo a palavra-chave. O espectador PRECISA saber o assunto nos primeiros 3 segundos.
2. VERIFICAR que o roteiro conta UMA ÚNICA história/caso com profundidade. Se listar múltiplos exemplos superficiais, reescreva focando no mais interessante com 3 atos (O que aconteceu → O que descobriram → O que nunca explicaram).
3. VERIFICAR que o CTA tem NO MÁXIMO 5 palavras (ex: "Curte e se inscreve."). Se for maior, encurte.
4. Ajustar o texto para ter ENTRE 80 e 120 palavras (30-45 segundos de fala).
5. Corrigir erros factuais óbvios. Manter o tom coloquial brasileiro.
6. Gerar 3 a 5 termos de busca em inglês para encontrar VÍDEOS de stock (B-Roll) no Pexels. Os termos devem ser ESPECÍFICOS à história contada no roteiro, com foco em MOVIMENTO e AÇÃO.
7. Criar um Título Otimizado (Descritivo + palavra-chave do tema + emoção). Exemplo: "O navio que encontraram vazio no oceano 😱".
8. Criar uma Descrição Otimizada (Palavras-chave + hashtags do nicho).

Retorne APENAS JSON no formato:
{
  "roteiro_texto": "O texto final para narração...",
  "busca_videos": ["termo1 em ingles", "termo2", "termo3"],
  "clima_da_musica": "tipo da musica de fundo",
  "titulo_youtube": "Título Viral com emoção",
  "descricao_youtube": "Descrição com hashtags relevantes"
}"""

    data = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"TEMA: {tema}\n\nRASCUNHO DO ROTEIRISTA:\n{rascunho}"}
        ],
        "temperature": 0.4
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        resultado = _parse_json(content)
        if resultado and "roteiro_texto" in resultado:
            log.info("✅ Pipeline Multi-Agente concluído! (Llama criou → GPT refinou e criou metadados)")
            return resultado
        return {}
    except Exception as e:
        log.error(f"Erro no GPT (refinamento): {e}")
        return {}


# ============================================================
# FALLBACKS SOLO (caso uma das APIs falhe)
# ============================================================

def _gerar_roteiro_openai_solo(prompt: str) -> dict:
    """GPT-4o-mini sozinho como fallback."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_aqui":
        return {}
    log.info("Fallback: GPT-4o-mini gerando roteiro solo...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
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
        log.info("Roteiro gerado via OpenAI (solo) com sucesso!")
        return _parse_json(content)
    except Exception as e:
        log.error(f"Erro no OpenAI: {e}")
        return {}


def _gerar_roteiro_groq_solo(prompt: str) -> dict:
    """Llama 3 sozinho gerando JSON direto."""
    if not GROQ_API_KEY or GROQ_API_KEY == "sua_chave_aqui":
        return {}
    log.info("Fallback: Groq (Llama 3) gerando roteiro solo...")
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
        log.info("Roteiro gerado via Groq (solo) com sucesso!")
        return _parse_json(content)
    except Exception as e:
        log.error(f"Erro no Groq: {e}")
        return {}


def _gerar_roteiro_ollama(prompt: str) -> dict:
    log.info(f"Fallback final: Ollama local ({OLLAMA_MODEL})...")
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


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def gerar_roteiro(tema: str) -> dict:
    """
    Gera roteiro viral com pipeline Multi-Agente:
    1. Llama 3 (Groq) cria rascunho criativo agressivo
    2. GPT-4o-mini refina, ajusta tempo e extrai JSON de produção
    
    Fallbacks: OpenAI solo -> Groq solo -> Ollama
    """
    prompt_path = os.path.join(PROMPTS_DIR, "roteiro_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    json_instructions = """

    IMPORTANTE: Você deve retornar EXATAMENTE UM JSON com o seguinte formato:
    {
      "roteiro_texto": "O texto completo para a narração de voz (hook, corpo e CTA tudo junto)",
      "busca_videos": [
        "termo de busca em ingles para video 1",
        "termo de busca em ingles para video 2",
        "termo de busca em ingles para video 3"
      ],
      "clima_da_musica": "lofi hip hop calmo"
    }
    """
    prompt_solo = prompt_template.format(tema=tema) + json_instructions
    log.info(f"Gerando roteiro para o tema: {tema}")

    # === PIPELINE MULTI-AGENTE (Llama 3 + GPT-4o) ===
    rascunho = _gerar_rascunho_groq(prompt_template.format(tema=tema))
    if rascunho:
        resultado = _refinar_com_gpt(rascunho, tema)
        if resultado and "roteiro_texto" in resultado:
            return resultado
        log.warning("GPT não conseguiu refinar. Tentando fallbacks solo...")

    # === FALLBACKS SOLO ===
    resultado = _gerar_roteiro_openai_solo(prompt_solo)
    if resultado and "roteiro_texto" in resultado:
        return resultado

    resultado = _gerar_roteiro_groq_solo(prompt_solo)
    if resultado and "roteiro_texto" in resultado:
        return resultado

    resultado = _gerar_roteiro_ollama(prompt_solo)
    if resultado and "roteiro_texto" in resultado:
        return resultado

    # Fallback de emergência
    log.error("Todas as APIs falharam. Usando roteiro de emergência.")
    return {
        "roteiro_texto": f"Você não vai acreditar no que descobri sobre {tema}! Curta e se inscreva para mais!",
        "busca_videos": [f"{tema}"],
        "clima_da_musica": "calm ambient"
    }


def carregar_roteiro_arquivo(caminho: str) -> dict:
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
        if conteudo.startswith("{"):
            return json.loads(conteudo)
        return {
            "roteiro_texto": conteudo,
            "busca_videos": ["aesthetic background"],
            "clima_da_musica": "lofi"
        }
    except Exception as e:
        log.error(f"Erro ao ler arquivo de roteiro: {e}")
        return None
