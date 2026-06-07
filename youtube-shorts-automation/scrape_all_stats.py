import os
import re
import glob
import json
import time
import requests
from config import BASE_DIR, LOGS_DIR

def extract_videos_from_logs():
    video_pattern = re.compile(r"URL: https://youtube.com/shorts/([a-zA-Z0-9_-]+)")
    tema_pattern = re.compile(r"Tema:\s*(.+)")
    
    videos = {}
    log_files = glob.glob(os.path.join(LOGS_DIR, "*.log"))
    
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    
    for filepath in sorted(log_files):
        filename = os.path.basename(filepath)
        log_date = filename.replace(".log", "")
        
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", log_date):
            continue
            
        if log_date < cutoff_date:
            continue
            
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        current_theme = "Desconhecido"
        for line in lines:
            theme_match = tema_pattern.search(line)
            if theme_match:
                current_theme = theme_match.group(1).strip()
            
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

def parse_short_page(video_id):
    url = f"https://www.youtube.com/shorts/{video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"status": "HTTP Error", "code": r.status_code}
            
        html = r.text
        
        # Extracao de titulo simplificada
        title = "Sem Título"
        title_match = re.search(r"<title>([^<]+)</title>", html)
        if title_match:
            title = title_match.group(1).replace(" - YouTube", "").strip()
            
        # Extracao do bloco ytInitialData
        data_match = re.search(r"var ytInitialData\s*=\s*({.+?});", html)
        if not data_match:
            data_match = re.search(r"window\['ytInitialData'\]\s*=\s*({.+?});", html)
            
        views = 0
        likes = 0
        comments = 0
        pub_date = "Desconhecida"
        
        # Regex fallback para Views, Likes
        # viewCount: "86"
        vc_match = re.search(r'"viewCount"\s*:\s*"(\d+)"', html)
        if vc_match:
            views = int(vc_match.group(1))
            
        if data_match:
            try:
                data = json.loads(data_match.group(1))
                
                # Buscar views e likes em factoids
                # Caminho: engagementPanels[1] -> videoDescriptionHeaderRenderer
                description_panel = None
                for panel in data.get("engagementPanels", []):
                    renderer = panel.get("engagementPanelSectionListRenderer", {})
                    content = renderer.get("content", {})
                    items = content.get("structuredDescriptionContentRenderer", {}).get("items", [])
                    for item in items:
                        if "videoDescriptionHeaderRenderer" in item:
                            description_panel = item["videoDescriptionHeaderRenderer"]
                            break
                    if description_panel:
                        break
                        
                if description_panel:
                    # Views
                    views_text = description_panel.get("views", {}).get("simpleText", "")
                    v_match = re.search(r"([\d\.,\s]+)", views_text)
                    if v_match:
                        views = int(re.sub(r'[^\d]', '', v_match.group(1)))
                        
                    # Factoids (Likes, Ano, etc)
                    for factoid in description_panel.get("factoid", []):
                        renderer = factoid.get("factoidRenderer", {})
                        if not renderer and "viewCountFactoidRenderer" in factoid:
                            renderer = factoid["viewCountFactoidRenderer"].get("factoid", {}).get("factoidRenderer", {})
                            
                        if renderer:
                            val = renderer.get("value", {}).get("simpleText", "0")
                            label = renderer.get("label", {}).get("simpleText", "").lower()
                            
                            if "like" in label:
                                val_clean = re.sub(r'[^\d]', '', val)
                                likes = int(val_clean) if val_clean else 0
                            elif "view" in label:
                                val_clean = re.sub(r'[^\d]', '', val)
                                if val_clean:
                                    views = int(val_clean)
                            elif any(char.isdigit() for char in label): # Ano (ex: 2026)
                                pub_date = f"{val} {label}"
                
                # Comments from buttonViewModels
                # Caminho: overlay -> reelPlayerOverlayRenderer -> playerOverlay -> reelPlayerOverlayViewModel -> actionBar -> reelActionBarViewModel -> buttonViewModels
                overlay = data.get("overlay", {})
                reel_overlay = overlay.get("reelPlayerOverlayRenderer", {})
                player_overlay = reel_overlay.get("playerOverlay", {})
                view_model = player_overlay.get("reelPlayerOverlayViewModel", {})
                action_bar = view_model.get("actionBar", {})
                bar_vm = action_bar.get("reelActionBarViewModel", {})
                buttons = bar_vm.get("buttonViewModels", [])
                
                for btn in buttons:
                    model = btn.get("buttonViewModel", {})
                    icon = model.get("iconName", "")
                    if icon == "SHORTS_COMMENT":
                        title_val = model.get("title", "0")
                        # Tratar formatos como "1.2K" ou "0"
                        if "K" in title_val:
                            comments = int(float(title_val.replace("K", "")) * 1000)
                        elif "M" in title_val:
                            comments = int(float(title_val.replace("M", "")) * 1000000)
                        else:
                            val_clean = re.sub(r'[^\d]', '', title_val)
                            comments = int(val_clean) if val_clean else 0
                            
                    elif icon == "LIKE" or icon == "LIKE_FILLED":
                        title_val = model.get("title", "")
                        if title_val and title_val.lower() != "like":
                            if "K" in title_val:
                                likes = int(float(title_val.replace("K", "")) * 1000)
                            elif "M" in title_val:
                                likes = int(float(title_val.replace("M", "")) * 1000000)
                            else:
                                val_clean = re.sub(r'[^\d]', '', title_val)
                                likes = int(val_clean) if val_clean else 0
            except Exception as e:
                pass # usar fallbacks regex
                
        return {
            "status": "Success",
            "title": title,
            "views": views,
            "likes": likes,
            "comments": comments,
            "published_date": pub_date
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}

def main():
    videos = extract_videos_from_logs()
    print(f"Total de {len(videos)} videos recentes (ultimos 14 dias) encontrados nos logs.")
    
    output_path = os.path.join(BASE_DIR, "all_video_stats.json")
    
    # Carrega dados existentes
    existing_stats = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "video_id" in item:
                        existing_stats[item["video_id"]] = item
        except Exception as e:
            print(f"Erro ao carregar dados antigos: {e}")
            
    results_map = existing_stats.copy()
    
    for idx, v in enumerate(videos):
        v_id = v["video_id"]
        print(f"[{idx+1}/{len(videos)}] Raspando {v_id} ({v['theme']})...")
        
        info = parse_short_page(v_id)
        
        if info.get("status") == "Success":
            views = info["views"]
            likes = info["likes"]
            comments = info["comments"]
            
            viral_rate = (likes / views * 100) if views > 0 else 0.0
            engagement = ((likes + comments) / views * 100) if views > 0 else 0.0
            
            results_map[v_id] = {
                "video_id": v_id,
                "theme": v["theme"],
                "logged_at": v["logged_at"],
                "title": info["title"],
                "views": views,
                "likes": likes,
                "comments": comments,
                "published_date": info["published_date"],
                "viral_rate": viral_rate,
                "engagement": engagement,
                "status": "Ativo"
            }
        else:
            # Se nao conseguiu raspar mas ja existia dado, mantem o antigo
            if v_id in existing_stats:
                print(f"  Falha ao raspar, mantendo dados anteriores para {v_id}")
            else:
                results_map[v_id] = {
                    "video_id": v_id,
                    "theme": v["theme"],
                    "logged_at": v["logged_at"],
                    "title": f"[Indisponível] {v['theme']}",
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "published_date": "Desconhecida",
                    "viral_rate": 0.0,
                    "engagement": 0.0,
                    "status": f"Erro ({info.get('status', 'Unknown')})"
                }
        
        time.sleep(1.0)
        
    results = list(results_map.values())
    results.sort(key=lambda x: x.get("views", 0), reverse=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print(f"Concluido! Salvo em {output_path}")

if __name__ == "__main__":
    main()
