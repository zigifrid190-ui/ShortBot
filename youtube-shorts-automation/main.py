import argparse
import glob
import os
import sys
import time
import schedule

from config import ASSETS_DIR
from modules.logger import get_logger
from modules.script_generator import gerar_roteiro, carregar_roteiro_arquivo
from modules.audio_generator import gerar_audio, gerar_legendas_whisper
from modules.visuals_fetcher import buscar_visuais
from modules.music_fetcher import buscar_musica_fundo
from modules.video_editor import editar_video
from modules.thumbnail_generator import gerar_thumbnail
from modules.uploader import upload_youtube

log = get_logger("main")


def limpar_assets():
    """Remove arquivos temporários da pasta assets/."""
    for f in glob.glob(os.path.join(ASSETS_DIR, "*")):
        if not f.endswith("music"): # Preserva a pasta de music local
            try:
                os.remove(f)
            except OSError:
                pass
    log.info("Assets temporários limpos.")


def gerar_short(tema: str, index: int = 1, roteiro_path: str = None, skip_upload: bool = False):
    log.info(f"{'='*50}")
    log.info(f"INICIANDO Geração DE SHORT #{index}")
    log.info(f"Tema: {tema}")
    log.info(f"{'='*50}")

    try:
        # 0. Limpar assets de execuções anteriores
        limpar_assets()

        # 1. Roteiro (de arquivo ou gerado por IA)
        if roteiro_path:
            roteiro = carregar_roteiro_arquivo(roteiro_path)
        else:
            roteiro = gerar_roteiro(tema)

        if not roteiro:
            log.error("Falha ao obter roteiro. Abortando este short.")
            return

        # 2. Áudio e Legendas
        audio_filename = f"audio_{index}.mp3"
        audio_path = gerar_audio(roteiro, audio_filename)
        legendas = gerar_legendas_whisper(audio_path)

        # 3. Busca de Visuais (múltiplas fontes, 2 vídeos para transição)
        videos = buscar_visuais(tema, num_videos=2)
        if not videos:
            log.error("Falha ao buscar vídeos. Abortando este short.")
            return
            
        # 3.5 Busca Música de Fundo
        bg_music = buscar_musica_fundo(tema)

        # 4. Edição de Vídeo (com Ken Burns + transições + Música Fundo)
        tema_slug = tema.replace(' ', '_').lower()
        output_video_name = f"short_{tema_slug}_{index}.mp4"
        video_final = editar_video(
            videos, 
            audio_path, 
            legendas, 
            output_filename=output_video_name,
            bg_music_path=bg_music
        )

        # 5. Thumbnail (usa frame do primeiro vídeo como fundo)
        thumb_name = f"thumb_{tema_slug}_{index}.jpg"
        thumb = gerar_thumbnail(roteiro, thumb_name, video_path=videos[0])

        # 6. Upload
        if skip_upload:
            log.info("Upload pulado (modo --sem-upload).")
        else:
            upload_youtube(video_final, thumb, roteiro, tema=tema)

        log.info(f"Short #{index} concluído com sucesso!")

    except Exception as e:
        log.error(f"Erro fatal no short #{index}: {e}", exc_info=True)


def job_diario(temas: list, **kwargs):
    log.info("Executando tarefa agendada diária...")
    if temas:
        tema = temas[0]
        gerar_short(tema, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation - ShortBot")
    parser.add_argument("--tema", type=str, help="Tema para gerar um short")
    parser.add_argument("--quantidade", type=int, default=1, help="Quantidade de shorts a gerar")
    parser.add_argument("--csv", type=str, help="Arquivo CSV com temas (um por linha)")
    parser.add_argument("--roteiro", type=str, help="Arquivo .txt com roteiro pronto (ignora geração por IA)")
    parser.add_argument("--sem-upload", action="store_true", help="Gera o vídeo sem fazer upload")
    parser.add_argument("--agendar-diario", action="store_true", help="Agendar execução diária às 10:00")

    args = parser.parse_args()

    temas = []
    if args.csv:
        import csv
        try:
            with open(args.csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        temas.append(row[0].strip())
        except Exception as e:
            log.error(f"Erro ao ler CSV: {e}")
            sys.exit(1)
    elif args.tema:
        temas = [args.tema]

    if not temas:
        log.error("Forneça pelo menos um tema com --tema ou uma lista em --csv.")
        sys.exit(1)

    extra_kwargs = {
        "roteiro_path": args.roteiro,
        "skip_upload": args.sem_upload
    }

    if args.agendar_diario:
        log.info("Modo Agendamento Diário ativado.")
        job_diario(temas, **extra_kwargs)
        schedule.every().day.at("10:00").do(job_diario, temas=temas, **extra_kwargs)
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        count = 1
        for tema in temas:
            for _ in range(args.quantidade):
                gerar_short(tema, index=count, **extra_kwargs)
                count += 1


if __name__ == "__main__":
    main()
