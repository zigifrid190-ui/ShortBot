import os
from config import PROMPTS_DIR, OLLAMA_MODEL
from ollama import Client

def gerar_roteiro(tema: str) -> str:
    """
    Gera um roteiro para YouTube Shorts usando um modelo local no Ollama.
    """
    prompt_path = os.path.join(PROMPTS_DIR, "roteiro_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    prompt = prompt_template.format(tema=tema)
    
    print(f"[*] Gerando roteiro para o tema: {tema}...")
    
    # Inicializa cliente (padrão localhost:11434)
    client = Client()
    
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    roteiro = response.get('message', {}).get('content', '').strip()
    return roteiro

if __name__ == "__main__":
    # Teste rápido
    roteiro = gerar_roteiro("Dicas de produtividade")
    print("\n--- Roteiro Gerado ---")
    print(roteiro)
