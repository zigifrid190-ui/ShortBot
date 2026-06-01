"""
levels_script_gen.py — Gerador de Roteiro no Formato Levels (ZukiFunBR)

Pipeline Multi-Agente (Sinergia):
  1. Groq (Llama 3)  : Criativo / Ideação (Rascunho de ideias absurdas e tempos)
  2. GPT-4o-mini     : Diretor / Refinamento (Hook forte, ritmo, remove narração literal, adiciona descrições visuais)
  3. Grok (xAI)      : Finalizador / Formatação JSON (Ajuste viral final e empacotamento estrito no schema)
"""
import os
import json
import sys
import requests

# Adiciona o diretório pai ao path para importar config e logger
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    PROMPTS_DIR, XAI_API_KEY, OPENAI_API_KEY, GROQ_API_KEY, OLLAMA_MODEL
)
from modules.logger import get_logger

log = get_logger("levels_script_gen")


def _parse_json_safe(text: str) -> dict:
    """Extrai e faz parse de JSON de um texto que pode conter markdown."""
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Erro ao parsear JSON: {e}\nTexto recebido: {text[:300]}")
        return {}


def _validar_levels(data: dict, num_levels: int) -> bool:
    """Valida que o JSON retornado tem o schema correto com levels suficientes."""
    if not isinstance(data, dict):
        return False
    if "levels" not in data or not isinstance(data["levels"], list):
        return False
    if len(data["levels"]) < max(4, num_levels - 2):
        log.warning(f"Levels insuficientes: {len(data['levels'])} (esperado ~{num_levels})")
        return False
    for level in data["levels"]:
        if not all(k in level for k in ["id", "objeto", "tempo_texto", "narração", "prompt_video"]):
            log.warning(f"Level com schema incompleto: {level}")
            return False
    return True


# ============================================================
# ESTÁGIO 1: IDEAÇÃO (GROQ / LLAMA 3)
# ============================================================
def _estagio_ideacao_groq(tema: str, num_levels: int) -> str:
    log.info("🧠 [Agente 1/3] Groq (Llama 3) ideando escalada absurda...")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY não configurada.")
        
    prompt = f"""Você é o Criativo Chefe.
Sua missão é criar o esqueleto de {num_levels} níveis para um YouTube Short comparativo de tempos, sobre o tema: '{tema}'.

REGRAS:
1. Defina um DESTINO ou OBJETIVO CLARO E ÚNICO.
2. Crie {num_levels} níveis de meios de transporte/movimentação, do mais LENTO para o mais RÁPIDO.
3. Para cada nível, estime a velocidade e o TEMPO ABSURDO calculado corretamente (ex: anos, séculos).
4. Escreva uma frase sarcástica curta ironizando a demora.
Não precisa formatar perfeito, apenas gere o conteúdo cru com as ideias bem boladas."""

    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


# ============================================================
# ESTÁGIO 2: DIREÇÃO E REFINAMENTO (GPT-4o-mini)
# ============================================================
def _estagio_direcao_gpt(rascunho: str) -> str:
    log.info("🎬 [Agente 2/3] GPT-4o-mini refinando ritmo e ganchos...")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY não configurada.")
        
    prompt = f"""Você é o Diretor de Shorts Virais (estilo ZukiFunBR).
Aqui está o rascunho criativo gerado pela sua equipe:
---
{rascunho}
---
Sua missão é lapidar esse texto para um vídeo de retenção altíssima.
REGRAS DE OURO:
1. Crie um HOOK fortíssimo (max 2 frases) logo no início declarando exatamente o DESTINO e a premissa.
2. NUNCA narre ações do personagem (ex: proibido falar "a caveira ri", "o personagem lamenta"). A ironia deve ser apenas dita diretamente para o espectador com acidez.
3. Para cada nível, descreva brevemente como seria o visual da cena animada (prompt de vídeo) em inglês, focando no objeto e no absurdo.
4. Mantenha as frases rápidas, de impacto, estilo locução enérgica.
Não use JSON ainda. Apenas escreva o texto refinado e os prompts."""

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, json=data, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ============================================================
# ESTÁGIO 3: FORMATAÇÃO JSON VIRAL (GROK)
# ============================================================
def _estagio_formatacao_grok(texto_refinado: str) -> dict:
    log.info("🤖 [Agente 3/3] Grok (xAI) formatando JSON estrito...")
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY não configurada.")
        
    prompt = f"""Você é o Especialista em Dados de Shorts.
Extraia as informações deste roteiro refinado:
---
{texto_refinado}
---

Gere EXATAMENTE UM JSON válido com o seguinte schema, sem adicionar markdown ou texto fora do JSON:
{{
  "titulo_youtube": "Título com emoji e emoção",
  "descricao_youtube": "Descrição com hashtags do nicho",
  "hook": "O gancho inicial exato do roteiro",
  "cta": "Curte e se inscreve!",
  "levels": [
    {{
      "id": 1,
      "label": "LEVEL 1",
      "objeto": "A PÉ",
      "velocidade_kmh": 5,
      "tempo_texto": "levaria X ANOS",
      "frase_engracada": "Piada sarcástica crua.",
      "narração": "Level 1. A pé. A 5 km/h, levaria X anos. Piada sarcástica.",
      "prompt_video": "2D cartoon animation, skeleton riding a turtle, dark cosmic background...",
      "meme_caveira": false
    }}
  ]
}}
Certifique-se de que a narração NÃO mencione coisas como "e a caveira ri".
Apenas retorne o JSON e NADA MAIS. Lembre-se de colocar true no meme_caveira nos 2 momentos mais absurdos."""

    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "grok-3-mini",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    response = requests.post(url, json=data, headers=headers, timeout=60)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_json_safe(content)


# ============================================================
# FUNÇÃO PRINCIPAL PÚBLICA
# ============================================================

def gerar_levels(tema: str, num_levels: int = 8) -> dict:
    """
    Gera o roteiro de Níveis usando uma pipeline multi-agente (Llama 3 -> GPT-4o-mini -> Grok).
    """
    log.info(f"Iniciando Sinergia de Agentes para roteiro: '{tema}' ({num_levels} levels)")
    
    try:
        # Estágio 1
        ideacao = _estagio_ideacao_groq(tema, num_levels)
        
        # Estágio 2
        direcao = _estagio_direcao_gpt(ideacao)
        
        # Estágio 3
        resultado = _estagio_formatacao_grok(direcao)
        
        if resultado and _validar_levels(resultado, num_levels):
            # Garantir ordenação por velocidade crescente
            resultado["levels"].sort(key=lambda x: x.get("velocidade_kmh", 0))
            # Re-numerar os ids após ordenação
            for i, level in enumerate(resultado["levels"], start=1):
                level["id"] = i
                level["label"] = f"LEVEL {i}"
            log.info(f"✅ Roteiro Co-criado gerado com {len(resultado['levels'])} cenas!")
            return resultado
        else:
            log.error("A formatação final JSON falhou na validação.")
            
    except Exception as e:
        log.error(f"Erro no pipeline multi-agente: {e}")

    # Fallback de emergência
    log.error("Usando roteiro de emergência devido a falha no pipeline.")
    return {
        "titulo_youtube": f"A verdade chocante sobre {tema} 😱",
        "descricao_youtube": f"Você não vai acreditar nisso! #shorts #curiosidades",
        "hook": f"Você já parou para pensar na verdade sobre {tema}? Prepare-se para se chocar.",
        "cta": "Curte e se inscreve!",
        "levels": [
            {
                "id": 1, "label": "LEVEL 1", "objeto": tema,
                "velocidade_kmh": 5, "tempo_texto": "MUITO TEMPO",
                "frase_engracada": "Nem esperando sentado.",
                "narração": f"Level 1. {tema}. Demora tanto que nem esperando sentado você consegue.",
                "prompt_video": f"2D cartoon animation, abstract representation of {tema}, clean style",
                "meme_caveira": True
            }
        ]
    }
