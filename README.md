# ShortBot - Automação Viral de YouTube Shorts 🚀

## 📖 Sobre o Projeto
O **ShortBot** é uma ferramenta de automação focada na criação e publicação de YouTube Shorts de forma 100% autônoma. O objetivo principal do projeto é gerar vídeos de alta retenção (seguindo o padrão algorítmico do YouTube em 2026) a custo próximo a zero, utilizando um pipeline coordenado de inteligência artificial para roteirização, narração, busca de clipes em vídeo (B-Rolls), edição dinâmica e upload agendado.

## 🚀 Funcionalidades Atuais

### 🧠 Roteirização Multi-Agente (Co-Criação)
- **Llama 3 (Criativo):** Responsável por criar roteiros com ganchos fortes e conteúdo direto e retentivo.
- **GPT-4o-mini / Gemini (Editor/Diretor):** Lapida o texto para a duração ideal de Shorts (50-60s) e extrai palavras-chave precisas em JSON para a busca de mídias dinâmicas.

### 🎙️ Áudio Realista & Dinâmico
- Integração com **ElevenLabs** e **OpenAI TTS** para vozes de altíssima qualidade (com inflexões reais e respiração), cruciais para a retenção do espectador.
- Fallback para **Edge-TTS** (gratuito) caso as cotas acabem.
- **Audio Ducking:** Adição automática de fundos musicais sem direitos autorais que abaixam de volume durante a locução e aumentam nas pausas.

### 🎬 Edição Viral & B-Rolls
- Abandono do modelo "slideshow estático" em prol do uso de **Micro-clipes (B-Rolls)** dinâmicos do Pexels/Pixabay via API, garantindo constante movimento na tela nos primeiros 3 segundos de vídeo.
- **Legendas Dinâmicas:** Animações palavra por palavra (*Word-by-word*) centralizadas, com cores chamativas e fontes visíveis.
- Edição completamente unificada em código usando **MoviePy** + **FFmpeg**.

### 🤖 Operação "Fantasma" e Anti-Spam
- **Trend Scraper:** Caso não se passe um tema, o bot possui capacidade de rastrear tendências para definir o que criar.
- **Upload Inteligente:** Postar vários vídeos de uma vez ativa filtros de Spam do YouTube. O ShortBot agenda as publicações com janelas de 4 a 6 horas entre si ou deixa em "Rascunho", otimizando o alcance e distribuição (Fase Explore/Exploit).

## 💻 Como Utilizar

### Requisitos Básicos e Instalação
O projeto foi desenhado para rodar via CLI de maneira modular. Certifique-se de ter instalado os pacotes listados em `requirements.txt` (ex: `moviepy`, `openai`, `google-api-python-client`, etc).

### Configuração de Ambiente (`.env`)
Você precisará preencher algumas variáveis de ambiente:
```env
ELEVENLABS_API_KEY=...      # Voz IA premium (Prioridade 1)
OPENAI_API_KEY=...          # Roteiro lapidado e TTS (Prioridade 2)
PEXELS_API_KEY=...          # Busca de B-Rolls (Gratuito)
# Além disso, é necessário configurar as credenciais do YouTube (client_secrets.json) para o upload.
```

### Comandos CLI 

```bash
# Execução clássica (passando um tema manual sem upload imediato)
python main.py --tema "Dicas secretas de produtividade" --sem-upload

# Modo Piloto Automático (O bot busca tendências e gera vídeos sozinho)
python main.py --auto 3

# Modo Fantasma (Ex: Gera e agenda 5 shorts diariamente às 10h da manhã)
python main.py --auto 5 --agendar 10:00

# Agendamento Multi-Horário
python main.py --auto 3 --agendar 08:00,14:00,20:00

# Agendamento "1 por dia" nos horários de pico (8h, 12h ou 18h)
python main.py --auto 5 --um-por-dia
```

---

## 📈 Histórico de Melhorias e Evolução da Arquitetura

O ShortBot nasceu de uma prova de conceito básica e evoluiu para tentar "hackear" a atenção do espectador:

### ✅ Versão 1.0 (A Fundação)
- Criação do pipeline básico linear: Input de Tema -> LLM Local (Ollama) -> Edge-TTS -> Imagens/Vídeos Pexels simples -> Edição estática com Ken Burns -> Upload via YouTube API.
- Funcionalidade principal pautada em automação de custo 0 rodando na própria máquina.

### ✅ Versão 2.0 (Foco Completo em Retenção - Atual)
- **Dinamismo Visual [Melhorias 1.1 e 1.2]:** Injeção de B-Rolls dinâmicos baseados em recortes curtos (2s a 4s) para prender a atenção.
- **Qualidade Sensorial [Melhorias 1.3 e 1.4]:** Arquitetura Multi-API de fallback para TTS avançado (ElevenLabs > OpenAI > Edge-TTS).
- **Roteiros Mais Engajantes [Melhorias 1.5 e 1.6]:** Separação de funções do LLM (Llama para a "criatividade solta e viral" e GPT para "direção técnica e extração do JSON") e integração de trilha sonora adaptativa.
- **Segurança da Conta:** Refatoração do sistema de agendamento para evitar o "Shadowban" do YouTube por uploads massivos (Spam).

### 🔮 Versão 3.0 (A Máquina Definitiva - Planejamento)
- [ ] **Dominação Multi-Plataforma:** Publicação unificada no **Instagram Reels** e **TikTok**.
- [ ] **Efeitos Sonoros (SFX) Sincronizados:** O texto indicará palavras-chave para acionar Efeitos Sonoros exatos no frame em que a legenda aparece (ex: Som de moeda na palavra "Dinheiro").
- [ ] **Motor de Analytics & Retroalimentação Viral:** Sistema que consome os Analytics das próprias postagens e instrui o LLM a reproduzir automaticamente os temas que deram as maiores taxas de visualização no seu nicho.
- [ ] **Painel de Controle (Web Dashboard):** Criação de uma interface gráfica rodando localmente (FastAPI/Streamlit) para abandonar a dependência estrita do terminal, facilitando visualização do calendário e custos de API.
