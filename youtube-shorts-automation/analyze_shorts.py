import os
import re
import pickle
import glob
import json
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from config import BASE_DIR, LOGS_DIR

TOKEN_PATH = os.path.join(BASE_DIR, "token.pickle")

def get_youtube_client():
    if not os.path.exists(TOKEN_PATH):
        print(f"Erro: token.pickle nao encontrado em {TOKEN_PATH}")
        return None
    with open(TOKEN_PATH, "rb") as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"Erro ao renovar token: {e}")
            return None
    try:
        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"Erro ao construir cliente do YouTube: {e}")
        return None

def extract_videos_from_logs():
    video_pattern = re.compile(r"URL: https://youtube.com/shorts/([a-zA-Z0-9_-]+)")
    tema_pattern = re.compile(r"Tema:\s*(.+)")
    
    videos = {}
    log_files = glob.glob(os.path.join(LOGS_DIR, "*.log"))
    
    for filepath in sorted(log_files):
        filename = os.path.basename(filepath)
        log_date = filename.replace(".log", "")
        
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        current_theme = "Desconhecido"
        for i, line in enumerate(lines):
            # Tentar achar o tema
            theme_match = tema_pattern.search(line)
            if theme_match:
                current_theme = theme_match.group(1).strip()
            
            # Tentar achar a URL do vídeo
            video_match = video_pattern.search(line)
            if video_match:
                video_id = video_match.group(1)
                
                time_str = log_date
                time_match = re.match(r"\[([\d\-\s\:]+)\]", line)
                if time_match:
                    time_str = time_match.group(1)
                    
                videos[video_id] = {
                    "video_id": video_id,
                    "theme": current_theme,
                    "logged_at": time_str,
                    "log_file": filename
                }
    return list(videos.values())

def main():
    youtube = get_youtube_client()
    if not youtube:
        print("Nao foi possivel autenticar com o YouTube.")
        return
        
    videos = extract_videos_from_logs()
    if not videos:
        print("Nenhum video encontrado nos logs.")
        return
        
    print(f"Encontrados {len(videos)} videos nos logs. Buscando estatisticas no YouTube...")
    
    video_ids = [v["video_id"] for v in videos]
    api_results = {}
    
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i+50]
        ids_str = ",".join(batch_ids)
        try:
            res = youtube.videos().list(part="snippet,statistics", id=ids_str).execute()
            for item in res.get("items", []):
                v_id = item["id"]
                api_results[v_id] = item
        except Exception as e:
            print(f"Erro ao buscar lote {i}: {e}")
            
    report_data = []
    for v in videos:
        v_id = v["video_id"]
        if v_id in api_results:
            api_data = api_results[v_id]
            stats = api_data.get("statistics", {})
            snippet = api_data.get("snippet", {})
            
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            title = snippet.get("title", v["theme"])
            published_at = snippet.get("publishedAt", v["logged_at"])
            
            viral_rate = (likes / views * 100) if views > 0 else 0.0
            engagement = ((likes + comments) / views * 100) if views > 0 else 0.0
            
            report_data.append({
                "video_id": v_id,
                "title": title,
                "theme": v["theme"],
                "published_at": published_at,
                "logged_at": v["logged_at"],
                "views": views,
                "likes": likes,
                "comments": comments,
                "viral_rate": viral_rate,
                "engagement": engagement,
                "status": "Ativo"
            })
        else:
            report_data.append({
                "video_id": v_id,
                "title": f"[Indisponivel/Privado] {v['theme']}",
                "theme": v["theme"],
                "published_at": v["logged_at"],
                "logged_at": v["logged_at"],
                "views": 0,
                "likes": 0,
                "comments": 0,
                "viral_rate": 0.0,
                "engagement": 0.0,
                "status": "Indisponivel"
            })
            
    report_data.sort(key=lambda x: x["views"], reverse=True)
    
    output_path = os.path.join(BASE_DIR, "video_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False)
        
    print(f"Analise concluida e salva em {output_path}")

if __name__ == "__main__":
    main()
