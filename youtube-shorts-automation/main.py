import argparse
import sys
import time
import schedule

from modules.script_generator import gerar_roteiro
from modules.audio_generator import gerar_audio, gerar_legendas_whisper
from modules.visuals_fetcher import buscar_visuais
from modules.video_editor import editar_video
from modules.thumbnail_generator import gerar_thumbnail
from modules.uploader import upload_youtube

def gerar_short(tema: str, index: int = 1):
    print(f"\n{'='*50}")
    print(f"[*] INICIANDO GERAÇÃO DE SHORT #{index}")
    print(f"[*] Tema: {tema}")
    print(f"{'='*50}\n")
    
    # 1. Geração de roteiro
    roteiro = gerar_roteiro(tema)
    if not roteiro:
        print("[!] Falha ao gerar roteiro. Abortando.")
        return
        
    # 2. Áudio e Legendas
    audio_filename = f"audio_{index}.mp3"
    audio_path = gerar_audio(roteiro, audio_filename)
    legendas = gerar_legendas_whisper(audio_path)
    
    # 3. Busca de Visuais
    videos = buscar_visuais(tema, num_videos=1)
    if not videos:
        print("[!] Falha ao buscar vídeo. Abortando.")
        return
    video_base = videos[0]
    
    # 4. Edição de Vídeo
    output_video_name = f"short_{tema.replace(' ', '_')}_{index}.mp4"
    video_final = editar_video(video_base, audio_path, legendas, output_filename=output_video_name)
    
    # 5. Thumbnail
    thumb_name = f"thumb_{tema.replace(' ', '_')}_{index}.jpg"
    thumb = gerar_thumbnail(roteiro, thumb_name)
    
    # 6. Upload
    upload_youtube(video_final, thumb, roteiro)
    
    print(f"\n[*] Short #{index} concluído com sucesso!")

def job_diario(temas: list):
    print("\n[*] Executando tarefa agendada diária...")
    if temas:
        tema = temas[0] # Pode implementar lógica para rotacionar/sortear
        gerar_short(tema)

def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation")
    parser.add_argument("--tema", type=str, help="Tema para gerar um short")
    parser.add_argument("--quantidade", type=int, default=1, help="Quantidade de shorts a gerar")
    parser.add_argument("--csv", type=str, help="Arquivo CSV com temas")
    parser.add_argument("--agendar-diario", action="store_true", help="Agendar execução diária")
    
    args = parser.parse_args()
    
    temas = []
    if args.csv:
        import csv
        try:
            with open(args.csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row: temas.append(row[0])
        except Exception as e:
            print(f"[!] Erro ao ler CSV: {e}")
            sys.exit(1)
    elif args.tema:
        temas = [args.tema]
        
    if not temas:
        print("Forneça pelo menos um tema com --tema ou uma lista em --csv.")
        sys.exit(1)
        
    if args.agendar_diario:
        print("[*] Modo Agendamento Diário ativado.")
        job_diario(temas) # Executa o primeiro logo de cara
        schedule.every().day.at("10:00").do(job_diario, temas=temas)
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Execução imediata
        count = 1
        for tema in temas:
            for _ in range(args.quantidade):
                gerar_short(tema, index=count)
                count += 1

if __name__ == "__main__":
    main()
