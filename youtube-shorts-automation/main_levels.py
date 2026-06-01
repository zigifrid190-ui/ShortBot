#!/usr/bin/env python
"""
main_levels.py — Entrypoint do Módulo Roteiro B (Formato Levels / ZukiFunBR)

Este sistema é COMPLETAMENTE SEPARADO do main.py original.
Usa: Grok API → Kling AI → MoviePy

Uso:
    python main_levels.py --tema "Distância até Marte"
    python main_levels.py --tema "Animais mais rápidos" --num-levels 9 --sem-upload
    python main_levels.py --csv temas_levels.csv --sem-upload
"""
import argparse
import glob
import os
import sys
import time
import traceback

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ASSETS_DIR
from modules.logger import get_logger
from modules.audio_generator import gerar_audio, gerar_legendas_whisper
from modules.uploader import upload_youtube

from modules_levels.levels_script_gen import gerar_levels
from modules_levels.levels_video_gen import gerar_clips_levels
from modules_levels.levels_compositor import montar_video_levels

log = get_logger("main_levels")

COOLDOWN = 15  # segundos entre vídeos


def limpar_assets():
    """Remove arquivos temporários da pasta assets/ (exceto skull.png e skeleton_master.png)."""
    preservar = {"skull.png", "skeleton_master.png"}
    for f in glob.glob(os.path.join(ASSETS_DIR, "*")):
        basename = os.path.basename(f)
        if os.path.isfile(f) and basename not in preservar:
            try:
                os.remove(f)
            except OSError:
                pass
    log.info("Assets temporários limpos (skeleton preservado).")


def gerar_short_levels(
    tema: str,
    index: int = 1,
    num_levels: int = 8,
    skip_upload: bool = False
) -> bool:
    """
    Gera um Short completo no formato Levels (ZukiFunBR).

    Pipeline:
    1. Gerar JSON de Levels (Grok API)
    2. Gerar narração unificada (ElevenLabs)
    3. Gerar clips por Level (Kling AI Image-to-Video)
    4. Montar vídeo final (MoviePy compositor)
    5. Upload (YouTube API, opcional)
    """
    log.info("=" * 60)
    log.info(f"ROTEIRO B — SHORT #{index}: {tema}")
    log.info("=" * 60)

    try:
        limpar_assets()

        # === ETAPA 1: Script em Levels ===
        log.info("📝 [1/4] Gerando roteiro em Levels (Grok API)...")
        levels_data = gerar_levels(tema, num_levels=num_levels)
        if not levels_data or not levels_data.get("levels"):
            log.error("Falha ao gerar roteiro em Levels. Abortando.")
            return False

        levels = levels_data["levels"]
        log.info(f"✅ {len(levels)} levels gerados.")

        # === ETAPA 2: Narração (ElevenLabs) ===
        log.info("🎙️ [2/4] Gerando narração unificada (ElevenLabs)...")

        # Montar o texto completo: hook + levels + CTA
        partes_narração = [levels_data.get("hook", "")]
        for level in levels:
            partes_narração.append(level.get("narração", f"Level {level['id']}. {level.get('objeto', '')}. {level.get('tempo_texto', '')}. {level.get('frase_engracada', '')}"))
        partes_narração.append(levels_data.get("cta", "Curte e se inscreve!"))

        texto_narração = " ".join(filter(None, partes_narração))
        audio_filename = f"levels_audio_{index}.mp3"
        audio_path = gerar_audio(texto_narração, audio_filename)

        if not audio_path or not os.path.exists(audio_path):
            log.error("Falha ao gerar áudio. Abortando.")
            return False

        legendas = gerar_legendas_whisper(audio_path)
        log.info("✅ Áudio e legendas gerados.")

        # === ETAPA 3: Clips por Level (Kling AI) ===
        log.info("🎬 [3/4] Gerando clips por Level (Kling AI)...")
        clips_por_level = gerar_clips_levels(levels)

        clips_ok = sum(1 for v in clips_por_level.values() if v)
        log.info(f"✅ {clips_ok}/{len(levels)} clips gerados pela Kling AI.")

        # === ETAPA 4: Composição Final (MoviePy) ===
        log.info("🖥️ [4/4] Montando vídeo final (ZukiFunBR Visual Engine)...")
        tema_slug = tema.replace(" ", "_").lower()[:30]
        output_filename = f"levels_{tema_slug}_{index}.mp4"

        video_final = montar_video_levels(
            levels_data=levels_data,
            clips_por_level=clips_por_level,
            audio_path=audio_path,
            legendas=legendas,
            output_filename=output_filename
        )

        if not video_final or not os.path.exists(video_final):
            log.error("Falha ao montar o vídeo final.")
            return False

        log.info(f"✅ Vídeo gerado: {video_final}")

        # === ETAPA 5: Upload (opcional) ===
        if skip_upload:
            log.info("Upload pulado (modo --sem-upload).")
        else:
            log.info("📤 Fazendo upload para o YouTube...")
            titulo = levels_data.get("titulo_youtube", f"Curiosidades sobre {tema}")
            descricao = levels_data.get("descricao_youtube", "")
            upload_youtube(
                video_final,
                None,  # sem thumbnail customizada por ora
                texto_narração,
                tema=tema,
                titulo_youtube=titulo,
                descricao_youtube=descricao
            )
            log.info("✅ Upload concluído.")

        log.info(f"🏆 Short #{index} (Roteiro B) concluído com sucesso!")
        return True

    except Exception as e:
        log.error(f"Erro fatal no Short #{index}: {e}")
        log.error(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(
        description="ShortBot — Módulo Roteiro B (Formato Levels / ZukiFunBR)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main_levels.py --tema "Quanto tempo para chegar em Marte"
  python main_levels.py --tema "Animais mais rápidos" --num-levels 9 --sem-upload
  python main_levels.py --csv temas_levels.csv --sem-upload
        """
    )
    parser.add_argument("--tema", type=str, help="Tema para gerar o Short em Levels")
    parser.add_argument("--csv", type=str, help="Arquivo CSV com temas (um por linha)")
    parser.add_argument("--num-levels", type=int, default=8, help="Número de Levels a gerar (padrão: 8)")
    parser.add_argument("--sem-upload", action="store_true", help="Gera o vídeo sem fazer upload")

    args = parser.parse_args()

    # Coletar temas
    temas = []
    if args.csv:
        import csv
        try:
            with open(args.csv, "r", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if row and row[0].strip():
                        temas.append(row[0].strip())
        except Exception as e:
            log.error(f"Erro ao ler CSV: {e}")
            sys.exit(1)
    elif args.tema:
        temas = [args.tema]

    if not temas:
        log.error("Forneça pelo menos um tema com --tema ou --csv")
        parser.print_help()
        sys.exit(1)

    # Executar lote
    total = len(temas)
    sucesso = 0
    inicio = time.time()

    log.info("#" * 60)
    log.info(f"ROTEIRO B — LOTE: {total} short(s) | {args.num_levels} levels cada")
    log.info("#" * 60)

    for i, tema in enumerate(temas, start=1):
        resultado = gerar_short_levels(
            tema=tema,
            index=i,
            num_levels=args.num_levels,
            skip_upload=args.sem_upload
        )
        if resultado:
            sucesso += 1

        if i < total:
            log.info(f"Aguardando {COOLDOWN}s antes do próximo...")
            time.sleep(COOLDOWN)

    duracao = (time.time() - inicio) / 60
    log.info("#" * 60)
    log.info(f"LOTE CONCLUÍDO em {duracao:.1f} minutos | Sucesso: {sucesso}/{total}")
    log.info("#" * 60)


if __name__ == "__main__":
    main()
