import os
from PIL import Image, ImageDraw, ImageFont
from config import OUTPUT_DIR, RESOLUTION

def gerar_thumbnail(roteiro: str, filename="thumbnail.jpg") -> str:
    """Gera uma thumbnail simples para o vídeo baseado no hook do roteiro."""
    print("[*] Gerando thumbnail...")
    w, h = RESOLUTION
    # Cor de fundo padrão
    img = Image.new('RGB', (w, h), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 100)
    except IOError:
        font = ImageFont.load_default()
        
    # Usa as primeiras palavras como texto de destaque
    palavras = roteiro.split()
    texto_hook = " ".join(palavras[:6]) + "..."
    
    # Centralizar o texto na thumbnail (aproximação simples)
    draw.text((w/2, h/2), texto_hook, fill=(255, 255, 0), font=font, anchor="mm", align="center")
    
    output_path = os.path.join(OUTPUT_DIR, filename)
    img.save(output_path)
    print(f"[*] Thumbnail salva em: {output_path}")
    return output_path
