import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import VideoFileClip
from config import OUTPUT_DIR, RESOLUTION
from modules.logger import get_logger

log = get_logger("thumbnail_generator")

FONT_NAME = "arialbd.ttf"


def _extrair_frame_video(video_path: str, tempo: float = 2.0) -> Image.Image:
    """Extrai um frame do vídeo para usar como fundo da thumbnail."""
    try:
        clip = VideoFileClip(video_path)
        t = min(tempo, clip.duration - 0.5)
        frame = clip.get_frame(max(0, t))
        clip.close()
        return Image.fromarray(frame)
    except Exception as e:
        log.warning(f"Não foi possível extrair frame do vídeo: {e}")
        return None


def _criar_gradiente_overlay(w: int, h: int) -> Image.Image:
    """Cria um overlay com gradiente escuro de baixo para cima."""
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(h):
        # Gradiente: topo com 30% opacidade, base com 85%
        alpha = int(80 + (215 - 80) * (y / h))
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return overlay


def gerar_thumbnail(
    roteiro: str,
    filename: str = "thumbnail.jpg",
    video_path: str = None
) -> str:
    """
    Gera uma thumbnail com visual profissional:
    - Fundo: frame do vídeo (com blur) ou gradiente colorido
    - Overlay: gradiente escuro
    - Texto: hook grande e centralizado com sombra
    """
    log.info("Gerando thumbnail...")
    w, h = RESOLUTION

    # 1. Fundo — tenta usar frame do vídeo, senão usa gradiente
    if video_path and os.path.exists(video_path):
        bg = _extrair_frame_video(video_path)
        if bg:
            bg = bg.resize((w, h), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=6))
        else:
            bg = None
    else:
        bg = None

    if bg is None:
        # Gradiente colorido como fallback
        bg = Image.new('RGB', (w, h), (15, 15, 25))
        draw_bg = ImageDraw.Draw(bg)
        cores = [
            ((20, 80, 180), (180, 30, 100)),
            ((150, 50, 200), (30, 120, 200)),
            ((200, 100, 30), (180, 30, 80)),
        ]
        c1, c2 = random.choice(cores)
        for y in range(h):
            ratio = y / h
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw_bg.line([(0, y), (w, y)], fill=(r, g, b))

    # Converte para RGBA para sobrepor
    bg = bg.convert('RGBA')

    # 2. Overlay gradiente escuro
    overlay = _criar_gradiente_overlay(w, h)
    bg = Image.alpha_composite(bg, overlay)

    # 3. Texto do hook
    bg_rgb = bg.convert('RGB')
    draw = ImageDraw.Draw(bg_rgb)

    palavras = roteiro.split()
    texto_hook = " ".join(palavras[:7]).upper()
    if len(palavras) > 7:
        texto_hook += "..."

    try:
        font_large = ImageFont.truetype(FONT_NAME, 110)
    except (IOError, OSError):
        font_large = ImageFont.load_default()

    # Centraliza o texto com word wrap simples
    max_chars_per_line = 14
    linhas = []
    palavras_hook = texto_hook.split()
    linha_atual = ""
    for p in palavras_hook:
        teste = f"{linha_atual} {p}".strip()
        if len(teste) <= max_chars_per_line:
            linha_atual = teste
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = p
    if linha_atual:
        linhas.append(linha_atual)

    texto_final = "\n".join(linhas)

    # Sombra do texto
    shadow_offset = 4
    draw.text(
        (w / 2 + shadow_offset, h / 2 + shadow_offset),
        texto_final, fill=(0, 0, 0), font=font_large, anchor="mm", align="center"
    )
    # Texto principal em branco/amarelo
    draw.text(
        (w / 2, h / 2),
        texto_final, fill=(255, 255, 80), font=font_large, anchor="mm", align="center"
    )

    output_path = os.path.join(OUTPUT_DIR, filename)
    bg_rgb.save(output_path, quality=95)
    log.info(f"Thumbnail salva em: {output_path}")
    return output_path
