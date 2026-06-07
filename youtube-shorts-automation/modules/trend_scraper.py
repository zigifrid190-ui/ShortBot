import os
import json
import random
import time
import requests
from config import BASE_DIR, OPENAI_API_KEY
from modules.logger import get_logger

log = get_logger("trend_scraper")

# Cache de temas recentes para evitar repetição nas últimas 48h
_CACHE_PATH = os.path.join(BASE_DIR, "last_themes_cache.json")
_CACHE_TTL_HOURS = 48


def _load_recent_themes() -> list:
    """Carrega temas usados nas últimas 48h do cache local."""
    if not os.path.exists(_CACHE_PATH):
        return []
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cutoff = time.time() - (_CACHE_TTL_HOURS * 3600)
        return [entry["tema"] for entry in data if entry.get("ts", 0) > cutoff]
    except Exception:
        return []


def _save_themes_to_cache(temas: list) -> None:
    """Salva temas gerados no cache com timestamp."""
    existing = []
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    cutoff = time.time() - (_CACHE_TTL_HOURS * 3600)
    existing = [e for e in existing if e.get("ts", 0) > cutoff]
    for tema in temas:
        existing.append({"tema": tema, "ts": time.time()})
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Erro ao salvar cache de temas: {e}")

# Categorias de nicho purificadas de alta performance (Grok/Ares aprovam)
NICHOS_VIRAIS = [
    "curiosidades sobre o corpo humano",
    "fatos históricos bizarros",
    "psicologia e manipulação mental",
    "fatos sobre o universo",
    "curiosidades sobre animais",
    "mistérios não resolvidos",
    "curiosidades sobre o cérebro",
    "fatos científicos surpreendentes",
    "fatos sobre o oceano",
    "curiosidades sobre o espaço",
    "descobertas arqueológicas inexplicáveis",
    "casos criminais históricos sem solução"
]


def _buscar_trends_google() -> list:
    """Busca tendências reais do Google Trends via RSS (sem API key)."""
    log.info("Buscando tendências do Google Trends Brasil...")
    url = "https://trends.google.com.br/trends/trendingsearches/daily/rss?geo=BR"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse simples do XML/RSS para extrair os títulos
        import re
        titulos = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>", response.text)
        
        if not titulos:
            # Fallback: tenta sem CDATA
            titulos = re.findall(r"<title>(.+?)</title>", response.text)
            # Remove o título do feed em si
            titulos = [t for t in titulos if "Daily Search Trends" not in t and "Google" not in t]
        
        if titulos:
            log.info(f"Google Trends: {len(titulos)} tendências encontradas.")
            return titulos[:10]
    except Exception as e:
        log.warning(f"Erro ao buscar Google Trends: {e}")
    
    return []


def _buscar_trends_serpapi() -> list:
    """Alternativa: busca trends via SerpAPI se disponível (requer key)."""
    # Placeholder para expansão futura com SerpAPI ou similar
    return []


def obter_temas_virais(quantidade: int = 5, nicho: str = None) -> list:
    """
    Retorna lista de temas virais para gerar shorts.
    Prioridade: Tema do dia (themes.py) -> Google Trends -> Nichos Curados.

    Args:
        quantidade: Número de temas para retornar.
        nicho: Se fornecido, filtra/prioriza temas desse nicho.
    """
    from themes import get_theme_for_today

    temas = []
    recentes = _load_recent_themes()

    # 1. Garante o tema do dia como primeiro item
    tema_dia = get_theme_for_today()
    if tema_dia not in recentes:
        temas.append(tema_dia)
        log.info(f"Tema do dia adicionado: {tema_dia}")
    else:
        log.info(f"Tema do dia já foi usado recentemente, usando como contexto apenas.")

    # 2. Tenta buscar tendências reais do Google
    trends = _buscar_trends_google()
    if trends:
        metade = max(1, quantidade // 2)
        # Filtra trends que não foram usados recentemente
        novos_trends = [t for t in trends if t not in recentes]
        selecionados = random.sample(novos_trends, min(metade, len(novos_trends))) if novos_trends else []
        temas.extend(selecionados)
        log.info(f"Selecionados {len(selecionados)} temas do Google Trends.")

    # 3. Complementa com nichos virais curados (filtra recentes)
    faltam = quantidade - len(temas)
    if faltam > 0:
        pool = NICHOS_VIRAIS.copy()
        if nicho:
            filtrados = [n for n in pool if nicho.lower() in n.lower()]
            if filtrados:
                pool = filtrados
        pool_novo = [n for n in pool if n not in recentes] or pool
        complemento = random.sample(pool_novo, min(faltam, len(pool_novo)))
        temas.extend(complemento)
        log.info(f"Complementados com {len(complemento)} temas de nichos curados.")

    temas = temas[:quantidade]
    _save_themes_to_cache(temas)
    log.info(f"Temas finais selecionados ({len(temas)}): {temas}")
    return temas


def obter_temas_por_desempenho(quantidade: int = 5) -> list:
    """
    Analisa os dados de performance de 'all_video_stats.json' e usa IA para
    gerar novos temas virais baseados nos temas que obtiveram melhor alcance.
    """
    stats_path = os.path.join(BASE_DIR, "all_video_stats.json")
    if not os.path.exists(stats_path):
        log.warning("Base de dados 'all_video_stats.json' nao encontrada. Usando nichos estaticos.")
        return obter_temas_virais(quantidade)
        
    try:
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
    except Exception as e:
        log.error(f"Erro ao carregar estatisticas: {e}")
        return obter_temas_virais(quantidade)
        
    # Filtrar apenas videos com visualizacoes ativas (evitar dados zerados)
    videos_ativos = [v for v in stats if v.get("views", 0) > 0 and v.get("status") == "Ativo"]
    if not videos_ativos:
        log.info("Nenhum video com visualizacoes registrado. Usando nichos estaticos.")
        return obter_temas_virais(quantidade)
        
    # Pegar o TOP 5 videos mais assistidos
    top_videos = videos_ativos[:5]
    top_details = []
    for idx, v in enumerate(top_videos):
        top_details.append(
            f"#{idx+1}: Tema original: '{v['theme']}' | Titulo: '{v['title']}' | Views: {v['views']} | Taxa Viral: {v.get('viral_rate', 0.0):.2f}%"
        )
    top_context = "\n".join(top_details)
    
    log.info(f"Gerando temas dinamicos a partir do TOP {len(top_videos)} videos mais assistidos...")
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_aqui":
        log.warning("OPENAI_API_KEY nao configurada para selecao de temas. Usando fallback estatico.")
        top_themes = list(set([v["theme"] for v in top_videos]))
        selected = random.choices(top_themes, k=quantidade)
        return [f"{t} bizarros" for t in selected]
        
    # Chamar GPT para criar temas derivados
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = """Você é um analista especialista em viralização de Shorts. 
Sua tarefa é analisar os temas e títulos de maior sucesso do canal e gerar NOVOS temas com altíssimo potencial de viralização.

Distribua a geração de novos temas da seguinte forma:
1. 50% de Aproveitamento (Exploitation): Temas derivados diretamente dos nichos e ângulos de maior sucesso no canal (ex: se criaturas marinhas bizarras ou fatos do corpo humano deram certo, gere novas variações focadas).
2. 50% de Exploração (Exploration): Novos temas e ângulos inéditos com alto potencial de engajamento, mas que ainda não foram amplamente testados ou que não aparecem no topo das views, focando em testar novos públicos para expandir o canal.

Regras importantes para todos os temas:
- Devem se manter estritamente dentro dos nichos permitidos: Corpo Humano (bizarro), Psicologia Sombria, Animais Exóticos/Venenosos e Mistérios/História Dark.
- Devem ser curtos, diretos e prontos para uso como tema de roteiro (ex: "animais abissais mais assustadores do oceano", "fatos sobre a anatomia que parecem mentira").

Retorne APENAS um JSON no formato:
{
  "temas": ["tema 1", "tema 2", "tema 3", ...]
}"""

    user_prompt = f"""Aqui estão os vídeos de melhor desempenho do canal:
{top_context}

Gere exatamente {quantidade} novos temas virais, equilibrando 50% em derivações do sucesso acima e 50% em novas explorações de público."""

    try:
        r = requests.post(
            url,
            headers=headers,
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.8
            },
            timeout=20
        )
        r.raise_for_status()
        res = r.json()["choices"][0]["message"]["content"]
        temas_gerados = json.loads(res).get("temas", [])
        if temas_gerados:
            log.info(f"Temas dinamicos gerados pela IA: {temas_gerados}")
            return temas_gerados[:quantidade]
    except Exception as e:
        log.error(f"Erro ao gerar temas dinamicos via IA: {e}")
        
    return obter_temas_virais(quantidade)

