import http.server
import socketserver
import subprocess
import os
import sys
import json

PORT = 8089

class ScraperHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Tenta localizar o executável do Python dentro do ambiente virtual
        venv_python = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = os.path.join(os.path.dirname(base_dir), ".venv", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = sys.executable  # Fallback para o python global

        if self.path == '/run':
            try:
                script_path = os.path.join(base_dir, "scrape_all_stats.py")
                # Executa o scraper de estatísticas de forma síncrona
                result = subprocess.run(
                    [venv_python, script_path],
                    capture_output=True,
                    text=True,
                    cwd=base_dir
                )
                
                stats_file = os.path.join(base_dir, "all_video_stats.json")
                if os.path.exists(stats_file):
                    with open(stats_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    error_msg = {"error": "Arquivo all_video_stats.json nao gerado.", "details": result.stderr}
                    self.wfile.write(json.dumps(error_msg).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif self.path == '/generate':
            try:
                main_path = os.path.join(base_dir, "main.py")
                # Executa o gerador em segundo plano de forma assíncrona (Popen), pois leva minutos
                log_file_path = os.path.join(base_dir, "logs", "weekly_generation.log")
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                
                with open(log_file_path, "a", encoding="utf-8") as log_file:
                    subprocess.Popen(
                        [venv_python, main_path, "--auto", "5", "--um-por-dia"],
                        cwd=base_dir,
                        stdout=log_file,
                        stderr=log_file
                    )
                
                self.send_response(202) # 202 Accepted
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                res = {
                    "status": "started",
                    "message": "Geração semanal de 5 Shorts iniciada com sucesso em segundo plano.",
                    "log_file": log_file_path
                }
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found. Use /run or /generate")

def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ScraperHandler) as httpd:
        print(f"Servidor Webhook do ShortBot ativo na porta {PORT}...")
        print(f"Endpoint de raspagem: http://localhost:{PORT}/run")
        print(f"Endpoint de geração: http://localhost:{PORT}/generate")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")

if __name__ == "__main__":
    main()
