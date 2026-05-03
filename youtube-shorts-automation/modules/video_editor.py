import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip,
    CompositeVideoClip, concatenate_videoclips
)
from moviepy.video.fx.all import crop, fadein, fadeout
from config import OUTPUT_DIR, RESOLUTION, ASSETS_DIR
from modules.logger import get_logger

log = get_logger("video_editor")

# Tipografia estilo viral (Montserrat Black > Arial Bold > fallback)
FONT_CANDIDATES = ["Montserrat-Black.ttf", "montserrat-black.ttf", "arialbd.ttf", "Arial Bold.ttf"]
FONT_SIZE = 72
STROKE_WIDTH = 5

# Cortes rápidos: duração máxima por clip (em segundos)
MAX_CLIP_DURATION = 3.0
MIN_CLIP_DURATION = 2.0

# Zoom dinâmico
ZOOM_IN_FACTOR = 1.20   # Primeiro clip: zoom agressivo para prender atenção
ZOOM_SUBTLE_FACTOR = 1.08  # Demais clips: zoom sutil para manter energia


def _get_font(size=FONT_SIZE):
    """Tenta carregar a melhor fonte disponível no sistema."""
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _aplicar_zoom_dinamico(clip, zoom_factor=1.10, direction="in"):
    """
    Aplica zoom dinâmico ao clip.
    direction='in': zoom para dentro (começa largo, termina close)
    direction='out': zoom para fora (começa close, termina largo)
    direction='random': escolhe aleatoriamente
    """
    if direction == "random":
        direction = random.choice(["in", "out"])

    w, h = clip.size
    duration = clip.duration

    def zoom_frame(get_frame, t):
        frame = get_frame(t)
        progress = t / max(duration, 0.01)

        if direction == "in":
            current_zoom = 1.0 + (zoom_factor - 1.0) * progress
        else:
            current_zoom = zoom_factor - (zoom_factor - 1.0) * progress

        new_w = int(w / current_zoom)
        new_h = int(h / current_zoom)
        x_start = (w - new_w) // 2
        y_start = (h - new_h) // 2

        # Clamp para evitar índices fora dos limites
        x_start = max(0, x_start)
        y_start = max(0, y_start)
        new_w = min(new_w, w - x_start)
        new_h = min(new_h, h - y_start)

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


def _criar_clip_legenda(word: str, start_time: float, end_time: float, target_w: int, index: int = 0):
    """
    Cria legenda estilo viral com AUTO-ESCALA:
    Se o bloco de palavras for mais largo que a tela, a fonte reduz
    automaticamente até caber. Nunca corta o texto.
    """
    if not word.strip():
        return None

    word_upper = word.upper()
    margin = 80  # margem lateral total
    max_text_w = target_w - margin

    # Auto-escala: reduz a fonte até o texto caber na largura disponível
    current_size = FONT_SIZE
    font = _get_font(current_size)

    while current_size > 28:
        temp_img = Image.new('RGBA', (max_text_w, 100), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        try:
            bbox = temp_draw.textbbox((0, 0), word_upper, font=font)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = temp_draw.textsize(word_upper, font=font)

        if tw <= max_text_w:
            break
        current_size -= 4
        font = _get_font(current_size)

    # Mede o tamanho final do texto com a fonte escolhida
    measure_img = Image.new('RGBA', (max_text_w + 40, current_size * 3), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure_img)
    try:
        bbox = measure_draw.textbbox((0, 0), word_upper, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = measure_draw.textsize(word_upper, font=font)

    # Cria a imagem com tamanho exato para o texto
    img_w = max_text_w
    img_h = int(th * 2.2)
    img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - tw) / 2
    y = (img_h - th) / 2

    # Contorno preto grosso (sombra para legibilidade)
    stroke = min(STROKE_WIDTH, max(3, current_size // 15))
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            draw.text((x + dx, y + dy), word_upper, font=font, fill="black")

    # Cores vibrantes alternadas (Branco, Amarelo Neon, Ciano)
    colors = ["#FFFFFF", "#FFD600", "#00E5FF"]
    fill_color = colors[index % len(colors)]

    draw.text((x, y), word_upper, font=font, fill=fill_color)

    img_array = np.array(img)
    rgb = img_array[:, :, :3]
    alpha = img_array[:, :, 3] / 255.0

    txt_clip = ImageClip(rgb).set_mask(ImageClip(alpha, ismask=True))
    txt_clip = txt_clip.set_position("center").set_start(start_time).set_end(end_time)

    return txt_clip


def _montar_clips_video(video_paths: list, duracao_total: float, target_w: int, target_h: int):
    """
    Monta múltiplos clipes com CORTES RÁPIDOS (2-3s por clip),
    zoom dinâmico alternado e transições de crossfade.
    Algoritmo 2026: energia visual alta = menos swipe-away.
    """
    CROSSFADE = 0.3
    clips_prontos = []
    clips_carregados = []

    # Carrega todos os vídeos disponíveis
    for vpath in video_paths:
        try:
            is_image = vpath.lower().endswith(('.jpg', '.jpeg', '.png'))
            if is_image:
                clip = ImageClip(vpath).set_duration(MAX_CLIP_DURATION)
            else:
                clip = VideoFileClip(vpath)
            clip = _ajustar_clip_vertical(clip, target_w, target_h)
            clips_carregados.append(clip)
        except Exception as e:
            log.warning(f"Erro ao carregar clip {vpath}: {e}")

    if not clips_carregados:
        raise RuntimeError("Nenhum clip de vídeo ou imagem pôde ser processado.")

    # Preenche a timeline com cortes rápidos de 2-3s
    tempo_acumulado = 0.0
    clip_index = 0
    zoom_directions = ["in", "out"]

    while tempo_acumulado < duracao_total:
        clip = clips_carregados[clip_index % len(clips_carregados)]
        tempo_restante = duracao_total - tempo_acumulado

        # Duração do segmento: entre MIN e MAX, sem exceder o que resta
        seg_dur = min(
            random.uniform(MIN_CLIP_DURATION, MAX_CLIP_DURATION),
            tempo_restante + CROSSFADE,
            clip.duration
        )

        if seg_dur < 0.5:
            break

        # Ponto de início aleatório no clip original (para variedade)
        max_start = max(0, clip.duration - seg_dur)
        start_point = random.uniform(0, max_start) if max_start > 0 else 0
        segment = clip.subclip(start_point, start_point + seg_dur)

        # Zoom dinâmico: primeiro clip é agressivo, depois alterna in/out
        if clip_index == 0:
            segment = _aplicar_zoom_dinamico(segment, ZOOM_IN_FACTOR, "in")
        else:
            direction = zoom_directions[clip_index % 2]
            segment = _aplicar_zoom_dinamico(segment, ZOOM_SUBTLE_FACTOR, direction)

        # Crossfade entre clips
        if len(clips_prontos) > 0:
            segment = fadein(segment, CROSSFADE)
        if tempo_restante > seg_dur:
            segment = fadeout(segment, CROSSFADE)

        clips_prontos.append(segment)
        tempo_acumulado += seg_dur - CROSSFADE
        clip_index += 1

    if not clips_prontos:
        raise RuntimeError("Falha ao montar timeline de clips.")

    log.info(f"Timeline montada: {len(clips_prontos)} cortes rápidos (~{MAX_CLIP_DURATION}s cada)")

    if len(clips_prontos) == 1:
        final = clips_prontos[0]
        if final.duration > duracao_total:
            return final.subclip(0, duracao_total)
        return final

    return concatenate_videoclips(clips_prontos, method="compose")


def _gerar_sfx_whoosh():
    """
    Gera um efeito sonoro 'whoosh' sintético caso não exista o arquivo swoosh.mp3.
    Usa uma onda de ruído com fade rápido (150ms).
    """
    duration = 0.15
    sample_rate = 44100
    samples = int(duration * sample_rate)

    noise = np.random.uniform(-0.3, 0.3, samples).astype(np.float32)

    # Envelope: fade-in rápido + fade-out
    envelope = np.ones(samples, dtype=np.float32)
    fade_in = int(0.02 * sample_rate)
    fade_out = int(0.10 * sample_rate)
    envelope[:fade_in] = np.linspace(0, 1, fade_in)
    envelope[-fade_out:] = np.linspace(1, 0, fade_out)

    audio_data = noise * envelope

    # Salva como arquivo temporário
    sfx_path = os.path.join(ASSETS_DIR, "_whoosh_generated.mp3")
    try:
        import soundfile as sf
        sf.write(sfx_path, audio_data, sample_rate)
        return sfx_path
    except ImportError:
        # Fallback: cria com scipy se disponível
        try:
            from scipy.io import wavfile
            wav_path = os.path.join(ASSETS_DIR, "_whoosh_generated.wav")
            wavfile.write(wav_path, sample_rate, (audio_data * 32767).astype(np.int16))
            return wav_path
        except ImportError:
            return None


def editar_video(
    video_paths: list,
    audio_path: str,
    legendas: list,
    output_filename: str = "short_final.mp4",
    bg_music_path: str = None
) -> str:
    """
    Motor de edição otimizado para o Algoritmo YouTube 2026:
    - Cortes rápidos a cada 2-3 segundos (energia visual alta)
    - Zoom dinâmico alternado (in/out) para manter atenção
    - Zoom agressivo no primeiro clip (anti swipe-away)
    - SFX Whoosh nas transições
    - Legendas grandes estilo viral (cores alternadas)
    - Música de fundo mixada a 10%
    """
    log.info("Iniciando edição do vídeo (Motor 2026)...")
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

            log.info(f"Adicionando música de fundo: {bg_music_path}")
            bg_clip = AudioFileClip(bg_music_path)

            bg_clip = bg_clip.subclip(0, min(bg_clip.duration, audio_duration))
            bg_clip = bg_clip.fx(volumex, 0.1)
            bg_clip = bg_clip.fx(audio_fadeout, 2.0)

            audio_clip = CompositeAudioClip([audio_clip, bg_clip])

        # 2. Montar clips com CORTES RÁPIDOS + ZOOM DINÂMICO
        if isinstance(video_paths, str):
            video_paths = [video_paths]

        base_clip = _montar_clips_video(video_paths, audio_duration, target_w, target_h)

        # Ajusta duração final para bater com o áudio
        if base_clip.duration > audio_duration:
            base_clip = base_clip.subclip(0, audio_duration)

        # 2.5 Adicionar SFX (Whoosh) nas transições
        sfx_clips = []
        swoosh_path = os.path.join(ASSETS_DIR, "swoosh.mp3")

        # Se não tiver o arquivo swoosh.mp3, tenta gerar um sintético
        if not os.path.exists(swoosh_path):
            swoosh_path = _gerar_sfx_whoosh()

        if swoosh_path and os.path.exists(swoosh_path):
            log.info("Adicionando SFX (Whoosh) nas transições...")
            try:
                from moviepy.audio.fx.all import volumex as vx
                swoosh_base = AudioFileClip(swoosh_path).fx(vx, 0.25)

                # Calcula os pontos de corte reais
                tempo = 0.0
                for i in range(1, len(video_paths) * 3):  # Estimativa de cortes
                    tempo += random.uniform(MIN_CLIP_DURATION, MAX_CLIP_DURATION) - 0.3
                    if tempo >= audio_duration:
                        break
                    sfx = swoosh_base.copy().set_start(tempo)
                    sfx_clips.append(sfx)
            except Exception as e:
                log.warning(f"Não foi possível adicionar SFX Whoosh: {e}")
        else:
            log.info("SFX Whoosh não disponível, prosseguindo sem efeitos sonoros.")

        # Compor Áudio Final (Voz + Fundo + SFX)
        from moviepy.editor import CompositeAudioClip
        audio_layer = [audio_clip]
        audio_layer.extend(sfx_clips)

        final_audio = CompositeAudioClip(audio_layer)
        base_clip = base_clip.set_audio(final_audio)

        # 3. Agrupar legendas em BLOCOS de 3-4 palavras (melhor legibilidade)
        WORDS_PER_BLOCK = 3
        text_clips = []
        block_index = 0
        
        for i in range(0, len(legendas), WORDS_PER_BLOCK):
            bloco = legendas[i:i + WORDS_PER_BLOCK]
            if not bloco:
                break
            
            palavras_bloco = " ".join([w["word"] for w in bloco])
            start_time = bloco[0]["start"]
            end_time = bloco[-1]["end"]
            
            txt_clip = _criar_clip_legenda(
                palavras_bloco,
                start_time,
                end_time,
                target_w,
                index=block_index
            )
            if txt_clip:
                text_clips.append(txt_clip)
            block_index += 1

        log.info(f"Legendas criadas: {len(text_clips)} blocos de {WORDS_PER_BLOCK} palavras (estilo viral)")

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
