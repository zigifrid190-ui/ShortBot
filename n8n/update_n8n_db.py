import sqlite3
import json
import os

db_path = r"C:\Users\zigifrid\Documents\Docker\database.sqlite"
workspace_wf_path = r"c:\Users\zigifrid\Documents\Projetos IA\ShortBot\n8n\workflow_stats.json"

def get_modified_nodes_and_connections(nodes, connections):
    new_nodes = []
    for node in nodes:
        # 1. Modify Format Message
        if node.get("name") == "Format Message" or node.get("id") == "5e8a8a8a-e9fa-47c1-8408-e8db5d8c36df":
            js_code = node["parameters"]["jsCode"]
            # Replace encodeURIComponent and return { msg: encodeURIComponent(msg) } with return { msg: msg }
            if "encodeURIComponent(msg)" in js_code:
                js_code = js_code.replace("encodeURIComponent(msg)", "msg")
            node["parameters"]["jsCode"] = js_code
            new_nodes.append(node)
            
        # 2. Modify Send a text message (Telegram)
        elif node.get("name") == "Send a text message" or node.get("id") == "449745a0-383d-4801-96c6-52b2bd5e8b95":
            telegram_node = {
                "parameters": {
                    "method": "POST",
                    "url": "https://api.telegram.org/bot8836464936:AAHJ1UHqt0N6ECwd1ACMzmD2g_Lv7t_Khe8/sendMessage",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {
                                "name": "chat_id",
                                "value": "5330885633"
                            },
                            {
                                "name": "text",
                                "value": "={{ $json.msg }}"
                            },
                            {
                                "name": "parse_mode",
                                "value": "Markdown"
                            }
                        ]
                    },
                    "options": {}
                },
                "id": "449745a0-383d-4801-96c6-52b2bd5e8b95",
                "name": "Send Telegram (HTTP)",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4,
                "position": node.get("position", [864, 208])
            }
            new_nodes.append(telegram_node)
            
        # 3. Modify Notify Generation Started (CallMeBot -> Telegram HTTP)
        elif node.get("name") == "Notify Generation Started" or node.get("id") == "9e8a8a8a-e9fa-47c1-8408-e8db5d8c36df":
            notify_node = {
                "parameters": {
                    "method": "POST",
                    "url": "https://api.telegram.org/bot8836464936:AAHJ1UHqt0N6ECwd1ACMzmD2g_Lv7t_Khe8/sendMessage",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {
                                "name": "chat_id",
                                "value": "5330885633"
                            },
                            {
                                "name": "text",
                                "value": "🤖 *ShortBot - Geração Iniciada*:\nA geração semanal de 5 novos Shorts (um por dia) foi iniciada e está sendo processada no Windows Host. Os vídeos serão agendados automaticamente nos horários de pico! 🚀"
                            },
                            {
                                "name": "parse_mode",
                                "value": "Markdown"
                            }
                        ]
                    },
                    "options": {}
                },
                "id": "9e8a8a8a-e9fa-47c1-8408-e8db5d8c36df",
                "name": "Notify Generation Started",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4,
                "position": node.get("position", [656, 464])
            }
            new_nodes.append(notify_node)
            
        # 4. Handle "Send WhatsApp (CallMeBot)" if it still exists in any form (it shouldn't, but just in case)
        elif node.get("name") == "Send WhatsApp (CallMeBot)":
            # We replace it with the new Send Telegram (HTTP) node as a fallback
            telegram_node = {
                "parameters": {
                    "method": "POST",
                    "url": "https://api.telegram.org/bot8836464936:AAHJ1UHqt0N6ECwd1ACMzmD2g_Lv7t_Khe8/sendMessage",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {
                                "name": "chat_id",
                                "value": "5330885633"
                            },
                            {
                                "name": "text",
                                "value": "={{ $json.msg }}"
                            },
                            {
                                "name": "parse_mode",
                                "value": "Markdown"
                            }
                        ]
                    },
                    "options": {}
                },
                "id": "6e8a8a8a-e9fa-47c1-8408-e8db5d8c36df",
                "name": "Send Telegram (HTTP)",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4,
                "position": node.get("position", [850, 200])
            }
            new_nodes.append(telegram_node)
        else:
            new_nodes.append(node)
            
    # Update connections: Replace "Send a text message" and "Send WhatsApp (CallMeBot)" with "Send Telegram (HTTP)"
    new_connections = {}
    for source_node, conn_data in connections.items():
        new_conn_data = {}
        for conn_type, conn_list in conn_data.items():
            new_list = []
            for conn in conn_list:
                updated_conn_list = []
                for dest in conn:
                    if dest.get("node") in ["Send a text message", "Send WhatsApp (CallMeBot)"]:
                        dest["node"] = "Send Telegram (HTTP)"
                    updated_conn_list.append(dest)
                new_list.append(updated_conn_list)
            new_conn_data[conn_type] = new_list
        new_connections[source_node] = new_conn_data
        
    return new_nodes, new_connections

def main():
    print(f"Modifying n8n database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Fetch current workflow
    cursor.execute("SELECT nodes, connections FROM workflow_entity WHERE id='4e8a8a8a-e9fa-47c1-8408-e8db5d8c36df';")
    row = cursor.fetchone()
    if not row:
        print("Error: ShortBot workflow not found in SQLite DB.")
        conn.close()
        return
        
    nodes = json.loads(row[0])
    connections = json.loads(row[1])
    
    new_nodes, new_connections = get_modified_nodes_and_connections(nodes, connections)
    
    # 2. Update workflow in database
    cursor.execute(
        "UPDATE workflow_entity SET nodes=?, connections=? WHERE id='4e8a8a8a-e9fa-47c1-8408-e8db5d8c36df';",
        (json.dumps(new_nodes, ensure_ascii=False), json.dumps(new_connections, ensure_ascii=False))
    )
    conn.commit()
    print("Successfully updated ShortBot workflow in n8n database!")
    conn.close()
    
    # 3. Also update the workspace workflow JSON file to keep it updated!
    if os.path.exists(workspace_wf_path):
        print(f"Updating workspace JSON file: {workspace_wf_path}")
        with open(workspace_wf_path, "r", encoding="utf-8") as f:
            ws_wf = json.load(f)
            
        ws_nodes = ws_wf.get("nodes", [])
        ws_connections = ws_wf.get("connections", {})
        
        new_ws_nodes, new_ws_connections = get_modified_nodes_and_connections(ws_nodes, ws_connections)
        
        ws_wf["nodes"] = new_ws_nodes
        ws_wf["connections"] = new_ws_connections
        
        with open(workspace_wf_path, "w", encoding="utf-8") as f:
            json.dump(ws_wf, f, ensure_ascii=False, indent=2)
        print("Successfully updated workspace JSON file!")
        
if __name__ == "__main__":
    main()
