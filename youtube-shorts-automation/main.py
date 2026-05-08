import argparse
import glob
import os
import sys
import time
import traceback
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
from modules.trend_scraper import obter_temas_virais

log = get_logger("main")

# Cooldown entre shorts (em segundos) para evitar rate-limit de APIs
COOLDOWN_ENTRE_SHORTS = 30


def limpar_assets():
    """Remove arquivos temporários da pasta assets/."""
    for f in glob.glob(os.path.join(ASSETS_DIR, "*")):
        if os.path.isfile(f):
            try:
                os.remove(f)
            except OSError:
                pass
    log.info("Assets temporários limpos.")


def gerar_short(tema: str, index: int = 1, roteiro_path: str = None, skip_upload: bool = False, publish_at: str = None) -> bool:
    """Gera um short completo. Retorna True se sucesso, False se falhou."""
    log.info(f"{'='*60}")
    log.info(f"INICIANDO GERAÇÃO DE SHORT #{index}")
    log.info(f"Tema: {tema}")
    log.info(f"{'='*60}")

    try:
        # 0. Limpar assets de execuções anteriores
        limpar_assets()

        # 1. Roteiro (de arquivo ou gerado por IA)
        if roteiro_path:
            roteiro_json = carregar_roteiro_arquivo(roteiro_path)
        else:
            roteiro_json = gerar_roteiro(tema)

        if not roteiro_json or "roteiro_texto" not in roteiro_json:
            log.error("Falha ao obter roteiro. Abortando este short.")
            return False
            
        roteiro_texto = roteiro_json["roteiro_texto"]
        busca_videos = roteiro_json.get("busca_videos", roteiro_json.get("prompts_imagem", [tema]))
        clima_musica = roteiro_json.get("clima_da_musica", "lofi")

        # 2. Áudio e Legendas
        audio_filename = f"audio_{index}.mp3"
        audio_path = gerar_audio(roteiro_texto, audio_filename)
        legendas = gerar_legendas_whisper(audio_path)

        # 3. Busca de B-Rolls em vídeo (dinâmicos, sem imagens estáticas)
        videos_ou_imagens = buscar_visuais(tema, num_videos=len(busca_videos), busca_videos=busca_videos)
        if not videos_ou_imagens:
            log.error("Falha ao buscar B-Rolls. Abortando este short.")
            return False

            
        # 3.5 Busca Música de Fundo
        bg_music = buscar_musica_fundo(clima_musica)

        # 4. Edição de Vídeo (com Ken Burns + transições + Música Fundo)
        tema_slug = tema.replace(' ', '_').lower()[:30]
        output_video_name = f"short_{tema_slug}_{index}.mp4"
        video_final = editar_video(
            videos_ou_imagens, 
            audio_path, 
            legendas, 
            output_filename=output_video_name,
            bg_music_path=bg_music
        )

        # 5. Thumbnail (usa frame do primeiro vídeo/imagem como fundo)
        thumb_name = f"thumb_{tema_slug}_{index}.jpg"
        thumb = gerar_thumbnail(roteiro_texto, thumb_name, video_path=videos_ou_imagens[0])

        # 6. Upload
        if skip_upload:
            log.info("Upload pulado (modo --sem-upload).")
        else:
            titulo_yt = roteiro_json.get("titulo_youtube")
            descricao_yt = roteiro_json.get("descricao_youtube")
            upload_youtube(
                video_final, 
                thumb, 
                roteiro_texto, 
                tema=tema, 
                publish_at=publish_at,
                titulo_youtube=titulo_yt,
                descricao_youtube=descricao_yt
            )

        log.info(f"Short #{index} concluído com sucesso!")
        return True

    except Exception as e:
        log.error(f"Erro fatal no short #{index}: {e}")
        log.error(traceback.format_exc())
def _calcular_horarios_publicacao(quantidade: int, um_por_dia: bool = False) -> list:
    """
    Calcula horários de publicação inteligentes baseados nos picos de audiência.
    """
    import datetime
    import random

    # Horários de pico em BRT (UTC-3):
    # 8 = Ida para o trabalho, 12 = Almoço, 18 = Saída do trabalho
    PICOS_BRT = [8, 12, 18]
    BRT_OFFSET = datetime.timedelta(hours=-3)

    agora_utc = datetime.datetime.utcnow()
    agora_brt = agora_utc + BRT_OFFSET

    horarios = []

    if um_por_dia:
        # 1 short por dia, nos próximos 'quantidade' dias
        for dia_offset in range(1, quantidade + 1):
            hora_pico = random.choice(PICOS_BRT)
            slot_brt = agora_brt.replace(hour=hora_pico, minute=0, second=0, microsecond=0)
            slot_brt += datetime.timedelta(days=dia_offset)
            slot_utc = slot_brt - BRT_OFFSET
            horarios.append(slot_utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return horarios

    # Comportamento padrão (empilhados)
    horarios.append(None)  # Primeiro vídeo é imediato
    if quantidade <= 1:
        return horarios

    slots_disponiveis = []
    # Adicionando o pico das 21 para o comportamento padrão
    PICOS_BRT_PADRAO = [8, 12, 18, 21]
    for dia_offset in range(3):
        for hora_pico in PICOS_BRT_PADRAO:
            slot_brt = agora_brt.replace(hour=hora_pico, minute=0, second=0, microsecond=0)
            slot_brt += datetime.timedelta(days=dia_offset)
            slot_utc = slot_brt - BRT_OFFSET
            if slot_utc > agora_utc + datetime.timedelta(minutes=30):
                slots_disponiveis.append(slot_utc)

    ultimo_slot = agora_utc
    for slot in slots_disponiveis:
        if len(horarios) >= quantidade:
            break
        if (slot - ultimo_slot).total_seconds() >= 4 * 3600:
            horarios.append(slot.strftime("%Y-%m-%dT%H:%M:%SZ"))
            ultimo_slot = slot

    while len(horarios) < quantidade:
        ultimo_slot += datetime.timedelta(hours=5)
        horarios.append(ultimo_slot.strftime("%Y-%m-%dT%H:%M:%SZ"))

    return horarios


def executar_lote(temas: list, quantidade_por_tema: int = 1, um_por_dia: bool = False, **kwargs):
    """Executa um lote de shorts com cooldown e agenda nos horários de pico."""
    total = len(temas) * quantidade_por_tema
    sucesso = 0
    falhas = 0
    count = 1

    log.info(f"{'#'*60}")
    log.info(f"INICIANDO LOTE: {total} shorts ({len(temas)} temas x {quantidade_por_tema})")
    log.info(f"{'#'*60}")
    inicio = time.time()

    # Calcula horários de publicação inteligentes
    horarios = _calcular_horarios_publicacao(total, um_por_dia=um_por_dia)
    for i, h in enumerate(horarios):
        if h:
            log.info(f"  Short #{i+1} agendado para: {h}")
        else:
            log.info(f"  Short #{i+1}: IMEDIATO (público)")

    for tema in temas:
        for _ in range(quantidade_por_tema):
            publish_at = horarios[count - 1] if count - 1 < len(horarios) else None

            resultado = gerar_short(tema, index=count, publish_at=publish_at, **kwargs)
            if resultado:
                sucesso += 1
            else:
                falhas += 1
            count += 1

            # Cooldown entre shorts para não estourar rate-limits
            if count <= total:
                log.info(f"Aguardando {COOLDOWN_ENTRE_SHORTS}s antes do próximo short...")
                time.sleep(COOLDOWN_ENTRE_SHORTS)

    duracao = time.time() - inicio
    log.info(f"{'#'*60}")
    log.info(f"LOTE FINALIZADO em {duracao/60:.1f} minutos")
    log.info(f"Sucesso: {sucesso}/{total} | Falhas: {falhas}/{total}")
    log.info(f"{'#'*60}")


def job_automatico(quantidade: int, skip_upload: bool, um_por_dia: bool = False):
    """Job que roda automaticamente: busca temas virais e gera shorts."""
    log.info("="*60)
    log.info("MODO AUTOMÁTICO: Buscando temas virais...")
    log.info("="*60)
    
    try:
        temas = obter_temas_virais(quantidade=quantidade)
        if not temas:
            log.error("Nenhum tema viral encontrado. Pulando esta execução.")
            return
        
        executar_lote(
            temas, 
            quantidade_por_tema=1, 
            um_por_dia=um_por_dia,
            skip_upload=skip_upload
        )
    except Exception as e:
        log.error(f"Erro no job automático: {e}")
        log.error(traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(
        description="ShortBot 2.0 - YouTube Shorts Automation com IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --tema "dicas de produtividade"
  python main.py --tema "curiosidades" --quantidade 5
  python main.py --csv temas.csv --sem-upload
  python main.py --auto 3                          # Gera 3 shorts com temas virais
  python main.py --auto 5 --agendar 10:00          # 5 shorts/dia às 10h (modo fantasma)
  python main.py --auto 2 --agendar 08:00,14:00    # 2 shorts 2x/dia
        """
    )
    parser.add_argument("--tema", type=str, help="Tema para gerar um short")
    parser.add_argument("--quantidade", type=int, default=1, help="Quantidade de shorts a gerar por tema")
    parser.add_argument("--csv", type=str, help="Arquivo CSV com temas (um por linha)")
    parser.add_argument("--roteiro", type=str, help="Arquivo .txt ou .json com roteiro pronto")
    parser.add_argument("--sem-upload", action="store_true", help="Gera o vídeo sem fazer upload")
    parser.add_argument("--auto", type=int, metavar="N", help="Modo Piloto Automático: busca N temas virais e gera shorts")
    parser.add_argument("--agendar", type=str, metavar="HH:MM", help="Agendar execução diária (ex: 10:00 ou 08:00,14:00,20:00)")
    parser.add_argument("--um-por-dia", action="store_true", help="Agenda 1 short por dia para os próximos N dias nos horários de pico (8h, 12h, 18h)")

    args = parser.parse_args()

    # === MODO AUTOMÁTICO (Piloto Automático) ===
    if args.auto:
        if args.agendar:
            # Modo Fantasma: agenda execução e fica rodando em loop infinito
            horarios = [h.strip() for h in args.agendar.split(",")]
            log.info(f"MODO FANTASMA ativado: {args.auto} shorts nos horários {horarios}")
            
            # Executa uma vez imediatamente
            job_automatico(args.auto, args.sem_upload, args.um_por_dia)
            
            # Agenda para os horários definidos
            for horario in horarios:
                schedule.every().day.at(horario).do(
                    job_automatico, 
                    quantidade=args.auto, 
                    skip_upload=args.sem_upload,
                    um_por_dia=args.um_por_dia
                )
                log.info(f"Agendado para {horario} todos os dias.")
            
            # Loop infinito resiliente
            log.info("Loop de agendamento iniciado. Ctrl+C para parar.")
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(30)
                except KeyboardInterrupt:
                    log.info("Agendamento encerrado pelo usuário.")
                    break
                except Exception as e:
                    log.error(f"Erro no loop de agendamento: {e}")
                    log.info("Recuperando em 60s...")
                    time.sleep(60)
        else:
            # Modo Automático Único: busca temas e gera agora
            job_automatico(args.auto, args.sem_upload, args.um_por_dia)
        return

    # === MODO MANUAL (temas fornecidos) ===
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
        log.error("Forneça pelo menos um tema com --tema, --csv ou use --auto N")
        parser.print_help()
        sys.exit(1)

    extra_kwargs = {
        "roteiro_path": args.roteiro,
        "skip_upload": args.sem_upload,
        "um_por_dia": args.um_por_dia
    }

    if args.agendar:
        horarios = [h.strip() for h in args.agendar.split(",")]
        log.info(f"Modo agendado: {horarios}")
        
        executar_lote(temas, args.quantidade, **extra_kwargs)
        
        for horario in horarios:
            schedule.every().day.at(horario).do(
                executar_lote, temas=temas, quantidade_por_tema=args.quantidade, **extra_kwargs
            )
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                log.info("Agendamento encerrado.")
                break
            except Exception as e:
                log.error(f"Erro no agendamento: {e}. Recuperando em 60s...")
                time.sleep(60)
    else:
        executar_lote(temas, args.quantidade, **extra_kwargs)


if __name__ == "__main__":
    main()

