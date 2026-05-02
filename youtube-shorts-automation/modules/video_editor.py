import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip,
    CompositeVideoClip, concatenate_videoclips
)
from moviepy.video.fx.all import crop, fadein, fadeout
from config import OUTPUT_DIR, RESOLUTION
from modules.logger import get_logger

log = get_logger("video_editor")

FONT_NAME = "arialbd.ttf"
FONT_SIZE = 90
STROKE_WIDTH = 5


def _aplicar_ken_burns(clip, zoom_factor=1.15):
    """Aplica efeito Ken Burns (zoom lento progressivo) ao clip."""
    w, h = clip.size
    duration = clip.duration

    def zoom_frame(get_frame, t):
        frame = get_frame(t)
        progress = t / duration
        current_zoom = 1.0 + (zoom_factor - 1.0) * progress

        new_w = int(w / current_zoom)
        new_h = int(h / current_zoom)
        x_start = (w - new_w) // 2
        y_start = (h - new_h) // 2

        cropped = frame[y_start:y_start + new_h, x_start:x_start + new_w]

        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    return clip.fl(zoom_frame)


def _ajustar_clip_vertical(clip, target_w, target_h):
    """Redimensiona e faz crop do clip para proporção 9:16."""
    w, h = clip.size
    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        clip = crop(clip, width=new_w, height=h, x_center=w / 2, y_center=h / 2)
    else:
        new_h = int(w / target_ratio)
        clip = crop(clip, width=w, height=new_h, x_center=w / 2, y_center=h / 2)

    return clip.resize(newsize=(target_w, target_h))


def _criar_clip_legenda(word: str, start_time: float, end_time: float, target_w: int):
    """Cria um ImageClip com uma palavra estilizada para legendas."""
    if not word.strip():
        return None

    word_upper = word.upper()

    try:
        font = ImageFont.truetype(FONT_NAME, FONT_SIZE)
    except (IOError, OSError):
        font = ImageFont.load_default()

    img_w = target_w - 80
    img_h = int(FONT_SIZE * 2)
    img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        bbox = draw.textbbox((0, 0), word_upper, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(word_upper, font=font)

    x = (img_w - tw) / 2
    y = (img_h - th) / 2

    # Contorno preto (sombra)
    for dx in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
        for dy in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
            draw.text((x + dx, y + dy), word_upper, font=font, fill="black")

    # Texto principal branco
    draw.text((x, y), word_upper, font=font, fill="white")

    img_array = np.array(img)
    rgb = img_array[:, :, :3]
    alpha = img_array[:, :, 3] / 255.0

    txt_clip = ImageClip(rgb).set_mask(ImageClip(alpha, ismask=True))
    txt_clip = txt_clip.set_position("center").set_start(start_time).set_end(end_time)

    return txt_clip


def _montar_clips_video(video_paths: list, duracao_total: float, target_w: int, target_h: int):
    """
    Monta múltiplos clipes de vídeo com transições de fade.
    Se só tiver 1 vídeo, aplica loop. Se tiver múltiplos, divide o tempo entre eles.
    """
    FADE_DURATION = 0.5

    if len(video_paths) == 1:
        clip = VideoFileClip(video_paths[0])
        if clip.duration < duracao_total:
            from moviepy.video.fx.all import loop
            clip = clip.fx(loop, duration=duracao_total)
        else:
            clip = clip.subclip(0, duracao_total)

        clip = _ajustar_clip_vertical(clip, target_w, target_h)
        clip = _aplicar_ken_burns(clip)
        return clip

    # Múltiplos clipes: divide o tempo igualmente com transição fade
    duracao_por_clip = duracao_total / len(video_paths)
    clips_prontos = []

    for i, vpath in enumerate(video_paths):
        try:
            clip = VideoFileClip(vpath)
            # Ajusta duração do segmento
            seg_dur = min(clip.duration, duracao_por_clip + FADE_DURATION)
            clip = clip.subclip(0, seg_dur)
            clip = _ajustar_clip_vertical(clip, target_w, target_h)
            clip = _aplicar_ken_burns(clip, zoom_factor=1.1)

            # Aplica fade-in/out para transição suave
            if i > 0:
                clip = fadein(clip, FADE_DURATION)
            if i < len(video_paths) - 1:
                clip = fadeout(clip, FADE_DURATION)

            clips_prontos.append(clip)
        except Exception as e:
            log.warning(f"Erro ao processar clip {vpath}: {e}")

    if not clips_prontos:
        raise RuntimeError("Nenhum clip de vídeo pôde ser processado.")

    return concatenate_videoclips(clips_prontos, method="compose")


def editar_video(
    video_paths: list,
    audio_path: str,
    legendas: list,
    output_filename: str = "short_final.mp4",
    bg_music_path: str = None
) -> str:
    """
    Monta o vídeo final: múltiplos stock videos com Ken Burns,
    transições fade, áudio narrado e legendas palavra-por-palavra.
    Opcionalmente adiciona música de fundo (bg_music_path).
    """
    log.info("Iniciando edição do vídeo...")
    target_w, target_h = RESOLUTION

    try:
        # 1. Carregar Áudio Principal (Voz)
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        log.info(f"Áudio carregado: {audio_duration:.1f}s")

        # 1.5 Carregar Música de Fundo (opcional)
        if bg_music_path and os.path.exists(bg_music_path):
            from moviepy.audio.fx.all import volumex, audio_fadeout
            from moviepy.editor import CompositeAudioClip
            from moviepy.video.fx.all import loop
            
            log.info(f"Adicionando música de fundo: {bg_music_path}")
            bg_clip = AudioFileClip(bg_music_path)
            
            # Se a música for mais curta que a voz, faz loop. Se não, corta.
            if bg_clip.duration < audio_duration:
                # O MoviePy AudioFileClip não tem método loop direto em algumas versões,
                # então usamos um fallback simples: pegar um subclip maior falhará, 
                # mas podemos usar a lib para isso ou ignorar e deixar acabar.
                # Para garantir, vamos só cortar no max.
                pass
            bg_clip = bg_clip.subclip(0, min(bg_clip.duration, audio_duration))
            
            # Reduz o volume da música para 10%
            bg_clip = bg_clip.fx(volumex, 0.1)
            bg_clip = bg_clip.fx(audio_fadeout, 2.0)
            
            audio_clip = CompositeAudioClip([audio_clip, bg_clip])

        # 2. Montar clips de vídeo (com Ken Burns + transições)
        if isinstance(video_paths, str):
            video_paths = [video_paths]

        base_clip = _montar_clips_video(video_paths, audio_duration, target_w, target_h)

        # Ajusta duração final para bater com o áudio
        if base_clip.duration > audio_duration:
            base_clip = base_clip.subclip(0, audio_duration)

        base_clip = base_clip.set_audio(audio_clip)

        # 3. Gerar Clips de Legendas Sincronizadas
        text_clips = []
        for palavra_info in legendas:
            txt_clip = _criar_clip_legenda(
                palavra_info["word"],
                palavra_info["start"],
                palavra_info["end"],
                target_w
            )
            if txt_clip:
                text_clips.append(txt_clip)

        log.info(f"Legendas criadas: {len(text_clips)} palavras")

        # 4. Compor o vídeo final
        final_video = CompositeVideoClip([base_clip] + text_clips)

        output_path = os.path.join(OUTPUT_DIR, output_filename)
        log.info(f"Exportando vídeo final para {output_path}...")

        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="ultrafast",
            logger="bar"
        )

        # Fechar clips para liberar memória
        base_clip.close()
        audio_clip.close()
        final_video.close()

        log.info(f"Edição concluída! Vídeo salvo em: {output_path}")
        return output_path

    except Exception as e:
        log.error(f"Erro durante a edição do vídeo: {e}")
        raise
