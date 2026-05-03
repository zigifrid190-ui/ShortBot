import random
import requests
from modules.logger import get_logger

log = get_logger("trend_scraper")

# Categorias de nicho que performam bem em Shorts PT-BR
NICHOS_VIRAIS = [
    "curiosidades sobre o corpo humano",
    "fatos históricos bizarros",
    "dicas de produtividade",
    "psicologia e manipulação mental",
    "fatos sobre o universo",
    "curiosidades sobre animais",
    "dicas de finanças pessoais",
    "tecnologia do futuro",
    "fatos sobre países",
    "mistérios não resolvidos",
    "erros que te impedem de crescer",
    "hábitos de pessoas bem sucedidas",
    "curiosidades sobre o cérebro",
    "fatos científicos surpreendentes",
    "dicas de inteligência emocional",
    "curiosidades sobre comida",
    "fatos sobre o oceano",
    "lições de vida dos bilionários",
    "curiosidades sobre o espaço",
    "verdades que ninguém te conta",
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
    Prioridade: Google Trends -> Nichos Curados (interno).
    
    Args:
        quantidade: Número de temas para retornar.
        nicho: Se fornecido, filtra/prioriza temas desse nicho.
    """
    temas = []
    
    # 1. Tenta buscar tendências reais do Google
    trends = _buscar_trends_google()
    if trends:
        # Pega até metade da quantidade de trends reais
        metade = max(1, quantidade // 2)
        selecionados = random.sample(trends, min(metade, len(trends)))
        temas.extend(selecionados)
        log.info(f"Selecionados {len(selecionados)} temas do Google Trends.")
    
    # 2. Complementa com nichos virais curados
    faltam = quantidade - len(temas)
    if faltam > 0:
        pool = NICHOS_VIRAIS.copy()
        if nicho:
            # Filtra nichos que contenham a palavra-chave do nicho
            filtrados = [n for n in pool if nicho.lower() in n.lower()]
            if filtrados:
                pool = filtrados
        
        complemento = random.sample(pool, min(faltam, len(pool)))
        temas.extend(complemento)
        log.info(f"Complementados com {len(complemento)} temas de nichos curados.")
    
    log.info(f"Temas finais selecionados ({len(temas)}): {temas}")
    return temas
