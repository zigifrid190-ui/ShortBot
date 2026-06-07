import os
import sys
import json
import glob
import argparse
import datetime
from pathlib import Path

# Adiciona o diretório base do projeto ao sys.path para carregar os módulos locais
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from modules.logger import get_logger
from modules.uploader import upload_youtube
from modules.tiktok_uploader import upload_tiktok
from config import DISABLE_TIKTOK

log = get_logger("upload_existing")

def extrair_metadados_de_json(json_path: str) -> dict:
    """Carrega metadados de um arquivo JSON do roteiro."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Mapeia chaves comuns usadas no ShortBot
        titulo = data.get("titulo_youtube") or data.get("titulo") or data.get("title")
        descricao = data.get("descricao_youtube") or data.get("descricao") or data.get("description")
        
        # Extrai roteiro completo (narração)
        roteiro = data.get("roteiro_texto") or data.get("roteiro") or data.get("script")
        if not roteiro and "levels" in data:
            # Reconstrói a narração se for roteiro de níveis
            narracoes = [level.get("narração", "") for level in data["levels"] if level.get("narração")]
            roteiro = " ".join(narracoes)
            
        return {
            "titulo": titulo,
            "descricao": descricao,
            "roteiro": roteiro or ""
        }
    except Exception as e:
        log.warning(f"Não foi possível ler metadados de {json_path}: {e}")
    return {}

def obter_titulo_do_nome(filename: str) -> str:
    """Gera um título estilo Artemis a partir do nome do arquivo."""
    # Remove extensão e prefixos comuns
    nome = Path(filename).stem
    if nome.startswith("short_"):
        nome = nome[6:]
    elif nome.startswith("levels_"):
        nome = nome[7:]
    
    # Limpa caracteres e substitui underscores por espaços
    nome_limpo = nome.replace("_", " ").strip()
    
    # Capitalização básica
    nome_titulo = nome_limpo.capitalize()
    
    # Adiciona emojis de impacto (Artemis style)
    prefixo = "🔥" if len(nome_titulo) % 2 == 0 else "😱"
    return f"{prefixo} {nome_titulo}! #shorts"

def processar_upload_individual(video_path: str, thumb_path: str = None, meta_path: str = None,
                               titulo: str = None, descricao: str = None, agendar: str = None,
                               skip_upload: bool = False, plataforma: str = "ambas"):
    """Realiza o upload de um único vídeo."""
    log.info(f"Processando vídeo individual: {video_path}")
    
    # 1. Encontrar metadados JSON se existirem
    metadata = {}
    if meta_path and os.path.exists(meta_path):
        metadata = extrair_metadados_de_json(meta_path)
    else:
        # Tenta buscar JSON de roteiro correspondente na mesma pasta
        base_name = Path(video_path).stem
        dir_name = Path(video_path).parent
        # Tenta padrões como video_name.json, roteiro_name.json, etc.
        possiveis_jsons = [
            dir_name / f"{base_name}.json",
            dir_name / f"roteiro_{base_name}.json",
            dir_name / "roteiro_c" / f"roteiro_c_{base_name}.json",
            dir_name / "roteiros_c" / f"roteiro_c_{base_name}.json"
        ]
        for pj in possiveis_jsons:
            if pj.exists():
                log.info(f"Metadados correspondentes encontrados: {pj}")
                metadata = extrair_metadados_de_json(str(pj))
                break

    # Resolve título final
    titulo_final = titulo or metadata.get("titulo") or obter_titulo_do_nome(video_path)
    # Resolve descrição
    descricao_final = descricao or metadata.get("descricao") or (
        f"{titulo_final}\n\n"
        f"📌 Se você curte mistérios e curiosidades, DEIXA O LIKE e SE INSCREVE!\n"
        f"🔔 Vídeos diários para explodir sua mente.\n\n"
        f"#shorts #curiosidades #viral"
    )
    # Resolve roteiro/transcrição
    roteiro_final = metadata.get("roteiro") or titulo_final

    # 2. Encontrar thumbnail correspondente se não for passada
    if not thumb_path:
        base_name = Path(video_path).stem
        dir_name = Path(video_path).parent
        
        # Converte short_tema_1 para thumb_tema_1
        slug = base_name
        if slug.startswith("short_"):
            slug = slug[6:]
            
        possiveis_thumbs = [
            dir_name / f"thumb_{slug}.jpg",
            dir_name / f"thumb_{slug}.png",
            dir_name / f"{base_name}.jpg",
            dir_name / f"{base_name}.png"
        ]
        for pt in possiveis_thumbs:
            if pt.exists():
                thumb_path = str(pt)
                log.info(f"Thumbnail correspondente encontrada: {thumb_path}")
                break

    log.info(f"Metadados Finais:")
    log.info(f"  Título: {titulo_final}")
    log.info(f"  Agendado para: {agendar or 'Imediato (Público)'}")
    
    if skip_upload:
        log.info("[MOCK] Upload simulado com sucesso (modo --sem-upload).")
        return True
        
    sucesso_yt = True
    if plataforma in ("youtube", "ambas"):
        video_id = upload_youtube(
            video_path=video_path,
            thumb_path=thumb_path,
            roteiro=roteiro_final,
            tema="",
            publish_at=agendar,
            titulo_youtube=titulo_final,
            descricao_youtube=descricao_final
        )
        sucesso_yt = video_id is not None

    sucesso_tt = True
    if plataforma in ("tiktok", "ambas"):
        if DISABLE_TIKTOK:
            log.info("Upload para o TikTok desativado no arquivo .env.")
        else:
            try:
                log.info("Iniciando upload correspondente para o TikTok...")
                sucesso_tt = upload_tiktok(
                    video_path=video_path,
                    roteiro=roteiro_final,
                    tema="",
                    publish_at=agendar,
                    legenda_personalizada=titulo_final
                )
            except Exception as e:
                log.error(f"Erro ao enviar para o TikTok: {e}")
                sucesso_tt = False

    return sucesso_yt and sucesso_tt

def processar_upload_lote(pasta_path: str, agendar_inicio: str = None, intervalo_horas: int = 4,
                          skip_upload: bool = False, plataforma: str = "ambas"):
    """Varre a pasta em busca de arquivos .mp4 e faz o upload em lote."""
    log.info(f"Iniciando varredura em lote na pasta: {pasta_path}")
    
    # Procura por vídeos
    videos = glob.glob(os.path.join(pasta_path, "*.mp4"))
    if not videos:
        log.error(f"Nenhum arquivo .mp4 encontrado na pasta: {pasta_path}")
        return False
        
    log.info(f"Encontrados {len(videos)} vídeos para upload.")
    
    # Configura horário inicial de publicação
    agendamento_corrente = None
    if agendar_inicio:
        try:
            # Espera formato ISO 8601: "YYYY-MM-DDTHH:MM:SSZ"
            # Remove o 'Z' para conversão e mantém ciente de UTC
            dt_str = agendar_inicio
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1]
            agendamento_corrente = datetime.datetime.fromisoformat(dt_str)
        except Exception as e:
            log.error(f"Formato de agendamento inicial inválido: {e}. Use YYYY-MM-DDTHH:MM:SSZ")
            sys.exit(1)
            
    sucessos = 0
    for idx, video in enumerate(sorted(videos)):
        log.info(f"\n{'-'*50}")
        log.info(f"UPLOADING VÍDEO {idx+1}/{len(videos)}: {Path(video).name}")
        log.info(f"{'-'*50}")
        
        agendar_str = None
        if agendamento_corrente:
            # Formata para padrão ISO da API do YouTube
            agendar_str = agendamento_corrente.strftime("%Y-%m-%dT%H:%M:%SZ")
            # Adiciona o intervalo para o próximo vídeo
            agendamento_corrente += datetime.timedelta(hours=intervalo_horas)
            
        sucesso = processar_upload_individual(
            video_path=video,
            thumb_path=None,
            meta_path=None,
            titulo=None,
            descricao=None,
            agendar=agendar_str,
            skip_upload=skip_upload,
            plataforma=plataforma
        )
        
        if sucesso:
            sucessos += 1
            
    log.info(f"\nUpload em lote concluído: {sucessos}/{len(videos)} vídeos enviados com sucesso.")
    return sucessos > 0

def main():
    parser = argparse.ArgumentParser(
        description="ShortBot Utility — Upload de vídeos curtos existentes para o YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Upload individual imediato
  python upload_existing.py --video "output/short_peixes_mais_perigosos_5.mp4"

  # Upload individual com agendamento e metadados customizados
  python upload_existing.py --video "output/short_peixes_mais_perigosos_5.mp4" --titulo "🔥 5 PEIXES QUE TE MATAM EM SEGUNDOS! 😱" --agendar "2026-06-01T18:00:00Z"

  # Upload em lote (todos os vídeos da pasta) agendados com intervalo de 6h
  python upload_existing.py --pasta "output" --agendar-lote-inicio "2026-06-01T08:00:00Z" --intervalo-horas 6

  # Simulação (Dry Run) sem gastar cota/enviar
  python upload_existing.py --pasta "output" --sem-upload
        """
    )
    
    # Grupo mutuamente exclusivo: ou vídeo individual ou pasta
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--video", type=str, help="Caminho do arquivo de vídeo (.mp4)")
    grupo.add_argument("--pasta", type=str, help="Caminho da pasta contendo vídeos para upload em lote")
    
    # Parâmetros de upload individual
    parser.add_argument("--thumb", type=str, help="Caminho do arquivo de thumbnail (opcional)")
    parser.add_argument("--metadata", type=str, help="Caminho do arquivo JSON de metadados do roteiro (opcional)")
    parser.add_argument("--titulo", type=str, help="Título customizado do Short (opcional)")
    parser.add_argument("--descricao", type=str, help="Descrição customizada do Short (opcional)")
    parser.add_argument("--agendar", type=str, help="Data/Hora de agendamento individual (ISO 8601, ex: 2026-06-01T12:00:00Z)")
    
    # Parâmetros de upload em lote
    parser.add_argument("--agendar-lote-inicio", type=str, metavar="ISO_DATE", help="Data/Hora inicial para agendamento dos vídeos em lote (ex: 2026-06-01T08:00:00Z)")
    parser.add_argument("--intervalo-horas", type=int, default=4, help="Intervalo de horas entre os vídeos agendados em lote (padrão: 4)")
    
    # Flag global
    parser.add_argument("--sem-upload", action="store_true", help="Executa as preparações e buscas de metadados sem fazer upload real")
    parser.add_argument("--plataforma", type=str, choices=["youtube", "tiktok", "ambas"], default="ambas", help="Plataforma de destino para o upload (padrão: ambas)")

    args = parser.parse_args()

    # Validação e roteamento
    if args.video:
        if not os.path.exists(args.video):
            log.error(f"Arquivo de vídeo não encontrado: {args.video}")
            sys.exit(1)
            
        sucesso = processar_upload_individual(
            video_path=args.video,
            thumb_path=args.thumb,
            meta_path=args.metadata,
            titulo=args.titulo,
            descricao=args.descricao,
            agendar=args.agendar,
            skip_upload=args.sem_upload,
            plataforma=args.plataforma
        )
        sys.exit(0 if sucesso else 1)
        
    elif args.pasta:
        if not os.path.exists(args.pasta) or not os.path.isdir(args.pasta):
            log.error(f"Pasta inválida ou não encontrada: {args.pasta}")
            sys.exit(1)
            
        sucesso = processar_upload_lote(
            pasta_path=args.pasta,
            agendar_inicio=args.agendar_lote_inicio,
            intervalo_horas=args.intervalo_horas,
            skip_upload=args.sem_upload,
            plataforma=args.plataforma
        )
        sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
