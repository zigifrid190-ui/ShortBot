import urllib.request
import json
import os
import sqlite3

bot_token = "8836464936:AAHJ1UHqt0N6ECwd1ACMzmD2g_Lv7t_Khe8"
db_path = r"C:\Users\zigifrid\Documents\Docker\database.sqlite"
workspace_wf_path = r"c:\Users\zigifrid\Documents\Projetos IA\ShortBot\n8n\workflow_stats.json"
test_telegram_path = r"c:\Users\zigifrid\Documents\Projetos IA\ShortBot\youtube-shorts-automation\test_telegram.py"

def update_files_with_chat_id(new_chat_id):
    print(f"Updating all configurations with new chat ID: {new_chat_id}")
    
    # 1. Update SQLite DB
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT nodes, connections FROM workflow_entity WHERE id='4e8a8a8a-e9fa-47c1-8408-e8db5d8c36df';")
            row = cursor.fetchone()
            if row:
                nodes = json.loads(row[0])
                connections = json.loads(row[1])
                updated = False
                for node in nodes:
                    if node.get("type") == "n8n-nodes-base.httpRequest":
                        params = node.get("parameters", {})
                        body_params = params.get("bodyParameters", {}).get("parameters", [])
                        for bp in body_params:
                            if bp.get("name") == "chat_id":
                                bp["value"] = str(new_chat_id)
                                updated = True
                if updated:
                    cursor.execute(
                        "UPDATE workflow_entity SET nodes=? WHERE id='4e8a8a8a-e9fa-47c1-8408-e8db5d8c36df';",
                        (json.dumps(nodes, ensure_ascii=False),)
                    )
                    conn.commit()
                    print("[OK] SQLite Database updated.")
            conn.close()
        except Exception as e:
            print("Error updating DB:", e)
            
    # 2. Update workspace workflow JSON
    if os.path.exists(workspace_wf_path):
        try:
            with open(workspace_wf_path, "r", encoding="utf-8") as f:
                ws_wf = json.load(f)
            ws_nodes = ws_wf.get("nodes", [])
            updated = False
            for node in ws_nodes:
                if node.get("type") == "n8n-nodes-base.httpRequest":
                    params = node.get("parameters", {})
                    body_params = params.get("bodyParameters", {}).get("parameters", [])
                    for bp in body_params:
                        if bp.get("name") == "chat_id":
                            bp["value"] = str(new_chat_id)
                            updated = True
            if updated:
                with open(workspace_wf_path, "w", encoding="utf-8") as f:
                    json.dump(ws_wf, f, ensure_ascii=False, indent=2)
                print("[OK] Workspace workflow JSON file updated.")
        except Exception as e:
            print("Error updating workspace JSON:", e)
            
    # 3. Update test_telegram.py
    if os.path.exists(test_telegram_path):
        try:
            with open(test_telegram_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Replace chat_id = "..."
            import re
            new_content = re.sub(r'chat_id = "[\d]+"', f'chat_id = "{new_chat_id}"', content)
            if new_content != content:
                with open(test_telegram_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("[OK] test_telegram.py updated.")
        except Exception as e:
            print("Error updating test_telegram.py:", e)

def main():
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    print("Fetching updates from Telegram...")
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        updates = json.loads(resp.read().decode('utf-8'))
        
        results = updates.get("result", [])
        if not results:
            print("No messages/updates found. Please send a message to the bot on Telegram first!")
            return
            
        # Get the latest message sender's chat ID
        latest_message = results[-1]
        chat = latest_message.get("message", {}).get("chat", {})
        chat_id = chat.get("id")
        first_name = chat.get("first_name", "User")
        
        if chat_id:
            print(f"Detected Chat ID: {chat_id} from user: {first_name}")
            update_files_with_chat_id(chat_id)
            print("All set! Run test_telegram.py now to verify.")
        else:
            print("Could not find a valid chat ID in the latest update.")
    except Exception as e:
        print("Error fetching updates:", e)

if __name__ == "__main__":
    main()
