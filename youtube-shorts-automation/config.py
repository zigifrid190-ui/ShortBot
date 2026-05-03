import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Configurações de API e Ambiente
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY", "")
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Vozes padrão
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJcg") # Voz masculina padrão (Adam)
OPENAI_VOICE = os.getenv("OPENAI_VOICE", "echo")

# Configurações do Vídeo
RESOLUTION = (1080, 1920)  # Largura, Altura para formato vertical (9:16)
MAX_DURATION_SECONDS = 55
DEFAULT_VOICE = "pt-BR-FranciscaNeural"  # ou "pt-BR-AntonioNeural"

# Configurações de Retry
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

# Criar os diretórios caso não existam
for d in [ASSETS_DIR, OUTPUT_DIR, LOGS_DIR, PROMPTS_DIR]:
    os.makedirs(d, exist_ok=True)
