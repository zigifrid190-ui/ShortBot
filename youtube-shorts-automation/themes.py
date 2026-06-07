"""
Ciclo semanal de temas e estruturas narrativas do ShortBot.
Garante variedade automática sem intervenção manual diária.
"""

from datetime import datetime


# Tema principal por dia da semana (0=Seg ... 6=Dom)
WEEKLY_THEMES = {
    0: "corpo humano fatos nojentos estranhos ou surpreendentes",     # Segunda
    1: "animais bizarros extremos ou perigosos",                       # Terça
    2: "dark psychology truques mentais e manipulação",                # Quarta
    3: "história dark mistérios reais e casos não solucionados",       # Quinta
    4: "ciência e universo fatos que explodem a mente",                # Sexta
    5: "descobertas arqueológicas e segredos enterrados da história",  # Sábado
    6: "mistérios do oceano e criaturas abissais inexplicáveis",       # Domingo
}

# Estrutura narrativa prioritária por dia — força variedade no prompt
WEEKLY_STRUCTURES = {
    0: "fato_chocante_direto",     # Declaração direta + revelação progressiva
    1: "lista_de_um",              # "Este animal faz algo que nenhum cientista esperava"
    2: "revelacao_final",          # Constrói tensão, revela no final
    3: "caso_real",                # História real com 3 atos (aconteceu / descobriram / nunca explicaram)
    4: "loop_aberto",              # Pergunta implícita que só é respondida no fim
    5: "desafio_ao_espectador",    # "Você não vai acreditar até ver a prova"
    6: "misstery_box",             # Apresenta o mistério, aprofunda, deixa gancho no final
}

# Descrição das estruturas para inserir no prompt
STRUCTURE_DESCRIPTIONS = {
    "fato_chocante_direto": (
        "Use a estrutura FATO CHOCANTE DIRETO: Declare o fato mais impactante logo na abertura, "
        "depois explique o contexto e aprofunde o porquê ele é tão surpreendente."
    ),
    "lista_de_um": (
        "Use a estrutura LISTA DE UM: Foque em UM único animal/evento/fato com profundidade total. "
        "Comece com a declaração central (ex: 'Este animal faz X que nenhum cientista esperava'), "
        "depois desenvolva com detalhes específicos e únicos."
    ),
    "revelacao_final": (
        "Use a estrutura REVELAÇÃO FINAL: Construa tensão e suspense ao longo do roteiro. "
        "O espectador deve ficar curioso até a última frase que entrega a revelação principal."
    ),
    "caso_real": (
        "Use a estrutura CASO REAL com 3 atos: 1) O que aconteceu (contexto rápido e impactante), "
        "2) O que foi descoberto (a revelação central), 3) O que nunca foi explicado (gancho final)."
    ),
    "loop_aberto": (
        "Use a estrutura LOOP ABERTO: Apresente uma contradição ou paradoxo no início sem resolver. "
        "Desenvolva o contexto e feche o loop na última frase, mas deixe uma pergunta implícita."
    ),
    "desafio_ao_espectador": (
        "Use a estrutura DESAFIO: Desafie diretamente o espectador na abertura "
        "('Você não vai acreditar nisto até ver a prova'). Depois entregue as evidências progressivamente."
    ),
    "misstery_box": (
        "Use a estrutura MYSTERY BOX: Apresente o mistério central na abertura, "
        "aprofunde com camadas de informação surpreendentes, e termine com um gancho que "
        "mantém a dúvida viva ('e até hoje ninguém sabe o porquê')."
    ),
}


def get_theme_for_today() -> str:
    """Retorna o tema principal do dia da semana atual."""
    return WEEKLY_THEMES[datetime.now().weekday()]


def get_structure_for_today() -> str:
    """Retorna a chave da estrutura narrativa prioritária para hoje."""
    return WEEKLY_STRUCTURES[datetime.now().weekday()]


def get_structure_instruction_for_today() -> str:
    """Retorna a instrução de estrutura para inserir no prompt do Llama 3."""
    structure_key = get_structure_for_today()
    return STRUCTURE_DESCRIPTIONS[structure_key]


def get_full_context_for_today() -> dict:
    """
    Retorna contexto completo do dia para uso no pipeline de geração.
    Inclui tema, chave de estrutura e instrução de prompt.
    """
    weekday = datetime.now().weekday()
    structure_key = WEEKLY_STRUCTURES[weekday]
    return {
        "tema_do_dia": WEEKLY_THEMES[weekday],
        "estrutura": structure_key,
        "instrucao_estrutura": STRUCTURE_DESCRIPTIONS[structure_key],
        "dia_semana": weekday,
    }


if __name__ == "__main__":
    ctx = get_full_context_for_today()
    print(f"Tema de hoje: {ctx['tema_do_dia']}")
    print(f"Estrutura: {ctx['estrutura']}")
    print(f"Instrução:\n{ctx['instrucao_estrutura']}")
