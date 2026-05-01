import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Configurações de API e Ambiente
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Configurações do Vídeo
RESOLUTION = (1080, 1920) # Largura, Altura para formato vertical (9:16)
MAX_DURATION_SECONDS = 55
DEFAULT_VOICE = "pt-BR-FranciscaNeural" # ou "pt-BR-AntonioNeural"

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

# Criar os diretórios caso não existam
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(PROMPTS_DIR, exist_ok=True)
