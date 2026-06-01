"""
levels_compositor.py — Compositor Visual estilo ZukiFunBR

Monta a timeline final com:
  - Card "LEVEL X" (Impact 130px, #FFFF00, fundo preto, 0.8s + flash)
  - Clip de 5s do Level (vídeo gerado pelo Kling AI)
  - Caption em 3 cores: objeto (branco), velocidade (amarelo), tempo (vermelho piscante)
  - Frase engraçada em branco menor
  - Aceleração progressiva dos clips por nível
"""
import os
import sys
import random
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFont

# Monkeypatch para Pillow >= 10.0.0 (MoviePy usa ANTIALIAS)
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip,
    CompositeVideoClip, concatenate_videoclips, ColorClip
)
from moviepy.video.fx.all import crop, fadein, fadeout, speedx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OUTPUT_DIR, RESOLUTION, ASSETS_DIR
from modules.logger import get_logger

log = get_logger("levels_compositor")

TARGET_W, TARGET_H = RESOLUTION  # 1080 x 1920

# ============================================================
# FONTES E ESTILOS (ZukiFunBR)
# ============================================================
FONT_HEAVY = ["Impact", "impact.ttf", "arialbd.ttf", "Arial Bold.ttf"]
FONT_MEDIUM = ["Montserrat-Black.ttf", "montserrat-black.ttf", "arialbd.ttf"]

COLOR_YELLOW = "#FFFF00"   # Level label + velocidade
COLOR_WHITE = "#FFFFFF"    # Objeto
COLOR_RED = "#FF0000"      # Tempo absurdo (piscante)
COLOR_BLACK = "#000000"


def _get_font(candidates: list, size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _texto_para_clip(
    texto: str,
    color: str,
    font_size: int,
    duration: float,
    start: float = 0.0,
    y_pos: float = 0.5,  # posição vertical relativa (0=topo, 1=baixo)
    piscar: bool = False
) -> ImageClip:
    """Renderiza um texto como ImageClip posicionado verticalmente."""
    font = _get_font(FONT_HEAVY, font_size)
    texto_upper = texto.upper()

    # Medir largura
    test_img = Image.new("RGBA", (TARGET_W, font_size * 3), (0, 0, 0, 0))
    test_draw = ImageDraw.Draw(test_img)
    try:
        bbox = test_draw.textbbox((0, 0), texto_upper, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = test_draw.textsize(texto_upper, font=font)

    # Auto-escala se muito largo
    while tw > TARGET_W - 80 and font_size > 24:
        font_size -= 4
        font = _get_font(FONT_HEAVY, font_size)
        try:
            bbox = test_draw.textbbox((0, 0), texto_upper, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = test_draw.textsize(texto_upper, font=font)

    # Criar imagem do texto
    img_h = int(th * 2.2)
    img = Image.new("RGBA", (TARGET_W, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x = (TARGET_W - tw) / 2
    y = (img_h - th) / 2

    # Contorno preto
    stroke = max(4, font_size // 12)
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            draw.text((x + dx, y + dy), texto_upper, font=font, fill=COLOR_BLACK)

    draw.text((x, y), texto_upper, font=font, fill=color)

    img_array = np.array(img)
    rgb = img_array[:, :, :3]
    alpha = img_array[:, :, 3] / 255.0

    clip = ImageClip(rgb).set_mask(ImageClip(alpha, ismask=True))
    clip = clip.set_duration(duration).set_start(start)

    # Posição vertical
    y_pixel = int(TARGET_H * y_pos) - img_h // 2
    y_pixel = max(0, min(TARGET_H - img_h, y_pixel))
    clip = clip.set_position(("center", y_pixel))

    if piscar:
        # Efeito de piscar a ~4fps (aparece/desaparece)
        def piscar_frame(gf, t):
            frame = gf(t)
            if int(t * 4) % 2 == 0:
                return frame
            return frame * 0  # transparente
        clip = clip.fl(piscar_frame)

    return clip


def _criar_card_level(level_label: str, duration: float = 0.8) -> VideoFileClip:
    """
    Cria o card de transição 'LEVEL X' — fundo preto + texto amarelo gigante.
    """
    bg = ColorClip(size=(TARGET_W, TARGET_H), color=(0, 0, 0)).set_duration(duration)

    # Texto "LEVEL X"
    txt = _texto_para_clip(
        level_label, COLOR_YELLOW, 140,
        duration=duration, y_pos=0.5
    )

    card = CompositeVideoClip([bg, txt])
    return card


def _clip_tela_preta(duration: float) -> ColorClip:
    """Clip de fallback (tela preta) para levels sem vídeo gerado."""
    return ColorClip(size=(TARGET_W, TARGET_H), color=(0, 0, 0)).set_duration(duration)


def _preparar_clip_level(video_path: str, level_idx: int, clip_duration: float = 5.0) -> VideoFileClip:
    """
    Carrega o clip do Level e aplica:
    - Crop/resize para 9:16
    - Aceleração progressiva (mais rápido nos últimos levels)
    """
    try:
        clip = VideoFileClip(video_path)

        # Crop para 9:16
        w, h = clip.size
        target_ratio = TARGET_W / TARGET_H
        current_ratio = w / h
        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            clip = crop(clip, width=new_w, height=h, x_center=w / 2, y_center=h / 2)
        else:
            new_h = int(w / target_ratio)
            clip = crop(clip, width=w, height=new_h, x_center=w / 2, y_center=h / 2)

        clip = clip.resize(newsize=(TARGET_W, TARGET_H))

        # Aceleração progressiva: levels finais são mais rápidos
        # level_idx 0-indexed: levels 6+ ficam 1.5x mais rápidos
        speed_factor = 1.0
        if level_idx >= 5:
            speed_factor = 1.5
        if level_idx >= 7:
            speed_factor = 2.0

        if speed_factor > 1.0:
            clip = clip.fx(speedx, speed_factor)
            log.info(f"  Level {level_idx + 1}: aceleração {speed_factor}x aplicada")

        # Garantir duração de clip_duration segundos (loop se necessário)
        if clip.duration < clip_duration:
            repeats = int(clip_duration / clip.duration) + 1
            from moviepy.editor import concatenate_videoclips
            clip = concatenate_videoclips([clip] * repeats)

        clip = clip.subclip(0, clip_duration)
        return clip

    except Exception as e:
        log.warning(f"Erro ao preparar clip: {e}. Usando tela preta.")
        return _clip_tela_preta(clip_duration)


def _criar_segmento_level(level: dict, clip_path: str, audio_clip: AudioFileClip, level_idx: int) -> list:
    """
    Cria o segmento completo de um Level:
    Card LEVEL X (0.8s) + Clip de vídeo (5s) com captions em 3 camadas.
    """
    CARD_DUR = 0.8
    CLIP_DUR = 5.0
    segmento = []

    # 1. Card de transição "LEVEL X"
    card = _criar_card_level(level["label"], duration=CARD_DUR)
    segmento.append(card)

    # 2. Clip do vídeo do Level
    if clip_path and os.path.exists(clip_path):
        video_clip = _preparar_clip_level(clip_path, level_idx, CLIP_DUR)
    else:
        video_clip = _clip_tela_preta(CLIP_DUR)

    # 3. Captions sobrepostos no clip de vídeo
    objeto = level.get("objeto", "").upper()
    velocidade = f"{level.get('velocidade_kmh', '')} KM/H" if level.get('velocidade_kmh') else ""
    tempo = level.get("tempo_texto", "").upper()
    frase = level.get("frase_engracada", "")

    text_layers = []

    # Objeto — branco, centro-superior (30% do topo)
    if objeto:
        t_obj = _texto_para_clip(objeto, COLOR_WHITE, 80, CLIP_DUR, y_pos=0.28)
        text_layers.append(t_obj)

    # Velocidade — amarelo, centro (40%)
    if velocidade:
        t_vel = _texto_para_clip(velocidade, COLOR_YELLOW, 70, CLIP_DUR, y_pos=0.42)
        text_layers.append(t_vel)

    # Tempo absurdo — vermelho piscante, centro (58%)
    if tempo:
        t_tempo = _texto_para_clip(tempo, COLOR_RED, 85, CLIP_DUR, y_pos=0.60, piscar=True)
        text_layers.append(t_tempo)

    # Frase engraçada — branco menor, parte inferior (75%)
    if frase:
        t_frase = _texto_para_clip(frase, COLOR_WHITE, 48, CLIP_DUR, y_pos=0.78)
        text_layers.append(t_frase)

    # Compor clip de vídeo + captions
    video_composto = CompositeVideoClip([video_clip] + text_layers)
    segmento.append(video_composto)

    return segmento


def montar_video_levels(
    levels_data: dict,
    clips_por_level: dict,
    audio_path: str,
    legendas: list,
    output_filename: str = "levels_short.mp4"
) -> str:
    """
    Função principal: monta o Short completo no estilo ZukiFunBR.

    Args:
        levels_data: Dict com 'hook', 'cta', 'levels' do gerador de script
        clips_por_level: Dict {level_id: caminho_mp4} do gerador de vídeo
        audio_path: Caminho do áudio narrado pelo ElevenLabs
        legendas: Lista de timestamps por palavra (do Whisper)
        output_filename: Nome do arquivo de saída

    Returns:
        Caminho do arquivo MP4 final
    """
    log.info("🎬 Iniciando composição do vídeo Roteiro B (ZukiFunBR Style)...")

    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    log.info(f"Áudio carregado: {audio_duration:.1f}s")

    levels = levels_data.get("levels", [])
    todos_segmentos = []

    # 1. Hook (tela preta + texto centralizado)
    hook_texto = levels_data.get("hook", "")
    if hook_texto:
        hook_duration = 3.0
        hook_bg = ColorClip(size=(TARGET_W, TARGET_H), color=(0, 0, 0)).set_duration(hook_duration)
        hook_txt = _texto_para_clip(hook_texto, COLOR_WHITE, 75, hook_duration, y_pos=0.5)
        hook_clip = CompositeVideoClip([hook_bg, hook_txt])
        todos_segmentos.append(hook_clip)
        log.info("Hook adicionado (3s)")

    # 2. Segmentos de cada Level
    for idx, level in enumerate(levels):
        level_id = level["id"]
        clip_path = clips_por_level.get(level_id)
        log.info(f"Montando Level {level_id}: {level.get('objeto', '?')}")

        segmento = _criar_segmento_level(level, clip_path, audio_clip, idx)
        todos_segmentos.extend(segmento)

    # 3. CTA final
    cta_texto = levels_data.get("cta", "Curte e se inscreve!")
    if cta_texto:
        cta_duration = 2.5
        cta_bg = ColorClip(size=(TARGET_W, TARGET_H), color=(0, 0, 0)).set_duration(cta_duration)
        cta_txt = _texto_para_clip(cta_texto, COLOR_YELLOW, 90, cta_duration, y_pos=0.5)
        cta_clip = CompositeVideoClip([cta_bg, cta_txt])
        todos_segmentos.append(cta_clip)
        log.info("CTA final adicionado (2.5s)")

    # 4. Concatenar tudo
    video_final_sem_audio = concatenate_videoclips(todos_segmentos, method="compose")

    # 5. Sincronizar áudio (o áudio guia — o vídeo é ajustado ao tempo do áudio)
    dur_video = video_final_sem_audio.duration
    dur_audio = audio_clip.duration

    if dur_video > dur_audio:
        # Vídeo mais longo: recortar o final
        video_final_sem_audio = video_final_sem_audio.subclip(0, dur_audio)
    elif dur_audio > dur_video:
        # Áudio mais longo: adicionar tela preta no final
        padding = ColorClip(size=(TARGET_W, TARGET_H), color=(0, 0, 0)).set_duration(dur_audio - dur_video)
        video_final_sem_audio = concatenate_videoclips([video_final_sem_audio, padding], method="compose")

    video_final = video_final_sem_audio.set_audio(audio_clip)

    # 6. Exportar
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    log.info(f"Exportando para {output_path}...")

    video_final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        logger="bar"
    )

    audio_clip.close()
    video_final.close()

    log.info(f"✅ Vídeo Roteiro B salvo: {output_path}")
    return output_path
