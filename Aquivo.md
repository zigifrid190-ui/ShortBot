# Roteiro Completo: Ferramenta de Automação de YouTube Shorts com IA (Python)

**Nome do Projeto:** `youtube-shorts-automation`  
**Versão do Roteiro:** 1.0 (30 de abril de 2026)  
**Objetivo:** Criar uma ferramenta **100% automática, rodando localmente**, que recebe um tema (ou lista de temas) e gera + posta YouTube Shorts de até 60 segundos com áudio gerado por IA (voz natural em PT-BR), vídeo editado com stock footage, legendas sincronizadas e upload automático.  
**Custo alvo:** R$ 0,00/mês (tudo local ou APIs gratuitas).  
**Público-alvo do usuário final:** Criadores de conteúdo que querem publicar 5–50 Shorts por dia sem esforço manual.

---

## 1. Visão Geral do Projeto

A ferramenta deve executar o pipeline completo **de ponta a ponta**:

1. **Input** → Tema(s) escolhido(s) pelo usuário (via CLI ou arquivo CSV).
2. **Geração de Roteiro** → LLM local gera roteiro otimizado para Shorts (hook + conteúdo + CTA).
3. **Geração de Áudio** → TTS em português brasileiro (voz natural, com timestamps).
4. **Busca de Visuais** → Stock videos verticais relevantes (Pexels API – grátis).
5. **Edição de Vídeo** → Montagem automática 9:16 (1080x1920), áudio + legendas animadas grandes + zoom suave.
6. **Thumbnail** → Geração simples automática.
7. **Upload** → Postagem automática como YouTube Short (público, com título, descrição, tags e hashtags).

**Requisitos não-funcionais:**
- Totalmente modular e extensível.
- Logging completo + tratamento de erros.
- Rodar em qualquer máquina (CPU ou GPU).
- Tempo médio por short: < 8 minutos.
- Fácil de agendar (cron / schedule).
- Zero dependência paga obrigatória.

---

## 2. Stack Tecnológica (Custo Zero)

| Camada              | Tecnologia                          | Motivo |
|---------------------|-------------------------------------|--------|
| LLM                 | Ollama (llama3.2 ou qwen2.5:7b)    | Local, grátis, excelente em PT-BR |
| TTS                 | edge-tts (Microsoft) ou Piper TTS  | Voz natural PT-BR, gratuita |
| Vídeo               | MoviePy + FFmpeg                    | Edição simples e poderosa |
| Stock Video         | Pexels API (chave gratuita)         | Milhões de vídeos grátis |
| Legendas            | Whisper (OpenAI) + MoviePy         | Sincronização palavra-por-palavra |
| Upload YouTube      | YouTube Data API v3 + OAuth        | Oficial do Google |
| Interface           | CLI + argparse                      | Simples e automatizável |
| Agendamento         | schedule + cron/Windows Task Scheduler | Execução diária automática |

**Opcional (melhoria futura):**
- Stable Diffusion local (Flux) para thumbnails ou imagens.
- Fish Speech ou XTTS para voz clonada.

---

## 3. Estrutura de Pastas

```bash
youtube-shorts-automation/
├── main.py                  # Ponto de entrada
├── config.py                # Configurações e variáveis de ambiente
├── requirements.txt
├── .env.example
├── modules/
│   ├── script_generator.py
│   ├── audio_generator.py
│   ├── visuals_fetcher.py
│   ├── video_editor.py
│   ├── thumbnail_generator.py
│   └── uploader.py
├── assets/                  # Temporário (stock, áudio, vídeos finais)
├── output/                  # Shorts finais + thumbnails
├── logs/                    # Logs diários
└── prompts/                 # Prompts prontos para LLM
## 4. Módulos Detalhados (Especificação para Agentes)

### 4.1 config.py
- Carregar .env (PEXELS_API_KEY, YOUTUBE_CLIENT_SECRET).
- Constantes: resolução (1080x1920), duração máxima (55s), voz padrão PT-BR.

### 4.2 script_generator.py
- Usar Ollama local.
- Prompt detalhado (incluir no arquivo prompts/roteiro_prompt.txt):
  - Hook nos primeiros 3s.
  - Linguagem jovem, conversacional, viral (PT-BR).
  - 120–160 palavras.
  - Estrutura: Hook → Corpo (1-2 fatos/dicas) → CTA forte.
- Retornar apenas texto puro.

### 4.3 audio_generator.py
- edge-tts (voice="pt-BR-FranciscaNeural" ou "pt-BR-AntonioNeural").
- Salvar audio.mp3.
- (Opcional) Usar Whisper para gerar JSON de timestamps palavra-por-palavra.

### 4.4 visuals_fetcher.py
- Buscar vídeos verticais 9:16 no Pexels com query = tema + "vertical".
- Baixar 1–2 vídeos de alta qualidade.
- Fazer download direto.

### 4.5 video_editor.py (O MAIS IMPORTANTE)
- Carregar stock video → cortar/loop para duração exata do áudio.
- Redimensionar para 1080x1920.
- Aplicar zoom lento (Ken Burns).
- Adicionar áudio.
- Gerar legendas grandes (fonte Impact/Arial Black, tamanho 80, cor branca com sombra preta, centralizadas).
- Legendas aparecem palavra-por-palavra sincronizadas.
- (Opcional) Música de fundo baixa (Pixabay API gratuita).
- Exportar como short_final.mp4 (H.264 + AAC).

### 4.6 thumbnail_generator.py
- Usar Pillow.
- Fundo gradiente escuro + texto grande do hook + emoji + seta.
- Salvar como thumbnail.jpg.

### 4.7 uploader.py
- Autenticação OAuth (gerar token.json na primeira execução).
- Título: "Hook forte + emoji".
- Descrição: roteiro completo + CTA + hashtags + link do canal.
- Tags: 10–15 tags relevantes + #shorts #viral.
- Privacy: public.
- Categoria: Shorts (o YouTube detecta automaticamente).


## 5. Arquivo main.py – Fluxo Principal

```python
# Pseudocódigo (o agente deve implementar completo)
def main(tema: str, quantidade: int = 1):
    for i in range(quantidade):
        roteiro = gerar_roteiro(tema)
        audio_path = gerar_audio(roteiro)
        video_paths = buscar_visuais(tema)
        video_final = editar_video(video_paths[0], audio_path, roteiro)
        thumb = gerar_thumbnail(roteiro)
        upload_youtube(video_final, thumb, roteiro)
```

## 6. Comandos CLI

```bash
python main.py --tema "dicas de produtividade" --quantidade 5
python main.py --csv temas.csv --agendar-diario
```

## 7. Testes e Critérios de Aceitação

- Gerar 1 short completo e validar manualmente (áudio claro, legendas sincronizadas, upload OK).
- Testar com 5 temas diferentes.
- Verificar se o vídeo tem menos de 60s e formato vertical.
- Logs devem registrar todos os passos e erros.
- Funcionar sem internet após baixar modelos Ollama (exceto Pexels e upload).


## 8. Próximos Passos Sugeridos (para o Agente do Antigravity)

- Criar o repositório e a estrutura de pastas.
- Instalar dependências e configurar Ollama + FFmpeg.
- Implementar módulo por módulo (começar por script_generator.py).
- Testar cada módulo isoladamente.
- Integrar no main.py.
- Adicionar tratamento de erros e logging.
- Criar README.md com instruções de uso.

---

### Instruções Adicionais

**Pronto!**  

Copie **todo o conteúdo acima** (desde o `# Roteiro Completo...` até o final) e cole em um arquivo novo chamado `ROTEIRO_YOUTUBE_SHORTS.md`.  

Depois é só jogar esse arquivo inteiro no **Antigravity da Google** e mandar ele criar o projeto completo.  

Se quiser que eu gere algum módulo específico (ex: o `main.py` pronto ou o `video_editor.py`) ou ajude na implementação, basta avisar!