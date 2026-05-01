import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
from moviepy.video.fx.all import crop
from config import OUTPUT_DIR, RESOLUTION

def editar_video(video_path: str, audio_path: str, legendas: list, output_filename: str = "short_final.mp4") -> str:
    """Monta o vídeo final: junta o stock video, o áudio gerado e as legendas animadas."""
    print("[*] Iniciando edição do vídeo...")
    
    # 1. Carregar Áudio
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    
    # 2. Carregar Vídeo Base e ajustar duração
    base_clip = VideoFileClip(video_path)
    
    if base_clip.duration < audio_duration:
        # Fazer loop do vídeo se ele for mais curto que o áudio
        from moviepy.video.fx.all import loop
        base_clip = base_clip.fx(loop, duration=audio_duration)
    else:
        base_clip = base_clip.subclip(0, audio_duration)
        
    # Crop para proporção exata 9:16 (1080x1920)
    w, h = base_clip.size
    target_w, target_h = RESOLUTION
    target_ratio = target_w / target_h
    current_ratio = w / h
    
    if current_ratio > target_ratio:
        # Vídeo mais largo
        new_w = int(h * target_ratio)
        x_center, y_center = w / 2, h / 2
        base_clip = crop(base_clip, width=new_w, height=h, x_center=x_center, y_center=y_center)
    else:
        # Vídeo mais alto
        new_h = int(w / target_ratio)
        x_center, y_center = w / 2, h / 2
        base_clip = crop(base_clip, width=w, height=new_h, x_center=x_center, y_center=y_center)
        
    base_clip = base_clip.resize(newsize=RESOLUTION)
    base_clip = base_clip.set_audio(audio_clip)
    
    # 3. Gerar Clips de Legendas Sincronizadas
    text_clips = []
    
    for palavra_info in legendas:
        word = palavra_info["word"]
        start_time = palavra_info["start"]
        end_time = palavra_info["end"]
        
        # Ajuste para não ter legenda vazia ou muito curta
        if not word.strip(): continue
        
        # Usa Pillow para criar a legenda (sem ImageMagick)
        word_upper = word.upper()
        fontsize = 100
        stroke_width = 5
        
        try:
            font = ImageFont.truetype("arialbd.ttf", fontsize)
        except:
            font = ImageFont.load_default()
            
        # Criar imagem RGBA transparente com sobra de espaço
        img_w, img_h = target_w - 100, int(fontsize * 1.5)
        img = Image.new('RGBA', (img_w, img_h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # Pegar tamanho do texto
        try:
            bbox = draw.textbbox((0,0), word_upper, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(word_upper, font=font)
            
        x = (img_w - tw) / 2
        y = (img_h - th) / 2
        
        # Contorno preto
        for dx in range(-stroke_width, stroke_width+1):
            for dy in range(-stroke_width, stroke_width+1):
                draw.text((x+dx, y+dy), word_upper, font=font, fill="black")
        # Texto principal branco
        draw.text((x, y), word_upper, font=font, fill="white")
        
        # Converte a imagem em um ImageClip
        img_array = np.array(img)
        rgb = img_array[:,:,:3]
        alpha = img_array[:,:,3] / 255.0
        
        txt_clip = ImageClip(rgb).set_mask(ImageClip(alpha, ismask=True))
        
        # Posição centralizada
        txt_clip = txt_clip.set_position("center").set_start(start_time).set_end(end_time)
        text_clips.append(txt_clip)
        
    # 4. Compor o vídeo final
    final_video = CompositeVideoClip([base_clip] + text_clips)
    
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    print(f"[*] Exportando vídeo final para {output_path} (pode demorar um pouco)...")
    
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        logger="bar"
    )
    
    # Fechar clips
    base_clip.close()
    audio_clip.close()
    final_video.close()
    
    print(f"[*] Edição concluída! Vídeo salvo em: {output_path}")
    return output_path
