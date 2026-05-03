# Planejamento de Melhorias 2.0 - ShortBot (Foco em Viralização e Automação)

## 1. Avaliação do Estado Atual (Pontos Fracos e Gargalos)
Após uma análise completa com a biblioteca `.agent` (`explorer-agent` e `project-planner`), o sistema atual é funcional e modular, mas possui gargalos estruturais que impedem uma escala verdadeiramente viral e 100% autônoma. 

### ❌ Pontos Fracos Identificados
1. **Visuais Genéricos (Stock Videos):** O `visuals_fetcher.py` utiliza Pexels e Pixabay. O problema de vídeos em *stock* é que eles costumam não reter a atenção nos primeiros milissegundos. Vídeos virais precisam de visuais dinâmicos, mudanças de padrão frequentes e imagens que comuniquem perfeitamente a fala.
2. **Narração Reconhecível (TTS Básico):** O `audio_generator.py` usa `edge-tts` (da Microsoft) ou `gTTS`. Embora o `edge-tts` seja razoável e gratuito, vozes muito comuns/robóticas diminuem drasticamente a retenção no YouTube Shorts (a métrica #1 do algoritmo).
3. **Falta de Dinamismo na Edição:** O `video_editor.py` executa um leve efeito "Ken Burns" e sobrepõe texto formatado. Para virais, faltam Efeitos Sonoros (SFX como *pop* ou *whoosh*), legendas coloridas destacando palavras-chave, emojis integrados e cortes muito mais secos/rápidos.
4. **Agendamento Frágil e Linear:** O agendamento via argumento `--agendar-diario` no `main.py` (usando a lib `schedule`) roda de forma bloqueante no terminal. Se a máquina reiniciar ou o processo falhar, a automação morre sem aviso.
5. **Falta de Auto-Alimentação de Temas:** A automação hoje exige que você defina os temas via CSV ou linha de comando. Para ser **100% automatizado e viral**, ele mesmo deveria buscar as tendências ("Trending") na internet para escolher os temas.

---

## 2. Roteiro de Melhorias (Roadmap 2.0)

Este plano atende exatamente as metas de (1.1) a (1.6) do seu arquivo original e injeta táticas validadas de retenção de Shorts.

### Fase 1: IA Audiovisual de Alta Retenção (Audio e Vídeo)
*Focando nos itens 1.1, 1.2, 1.3 e 1.4*

* **Aprimoramento Visual (IA + Multi-APIs):**
  * **O que fazer:** Implementar geradores de Imagem por IA (ex: Leonardo.ai, Fal.ai/Flux ou OpenAI DALL-E) em vez de focar apenas em stock.
  * **Como funciona:** O modelo de linguagem gera um "prompt de arte" para cada frase dita. O bot gera as imagens com IA, e o `video_editor.py` cria o movimento sobre essas imagens com cortes a cada 3 segundos.
  * **Sistema Fallback:** Leonardo.ai -> Fal.ai -> Pexels (Stock).

* **Aprimoramento Áudio (IA Realista + Multi-APIs):**
  * **O que fazer:** Integrar a **ElevenLabs** (ou OpenAI TTS) como gerador de áudio primário. As vozes da ElevenLabs possuem inflexão e respiração que prendem o ouvinte.
  * **Sistema Fallback:** ElevenLabs -> OpenAI TTS -> Edge-TTS (Grátis, Terciário).

### Fase 2: Roteirização Inteligente e Música
*Focando nos itens 1.5 e 1.6*

* **Roteirização Avançada (Multi-APIs):**
  * **O que fazer:** Incluir Google Gemini (Gemini 1.5 Flash - rápido/gratuito via API key) e OpenAI, mantendo Groq e Ollama como opções locais/gratuitas. 
  * **Upgrade:** Dividir a lógica no `script_generator.py` para a IA retornar um **JSON** estruturado contendo: `gancho`, `narrativa`, `cta`, `sugestão_de_imagens_por_cena` e `clima_da_musica`.
* **Fundo Musical Dinâmico:**
  * **O que fazer:** Aprimorar o `music_fetcher.py`. Com base no campo `clima_da_musica` retornado pelo LLM, buscar via API Músicas Livres de Copyright (ex: Pixabay Music ou pasta categorizada). Adicionar *Audio Ducking* (a música fica <10% do volume na fala e sobe na pausa/final).

### Fase 3: Edição Viral "Estilo Alex Hormozi/Ali Abdaal"
* **Legendas Dinâmicas:** Atualizar a função no `video_editor.py` para pintar de amarelo/verde a palavra exata que está sendo dita no momento e incluir fontes em itálico para enfatizar perguntas.
* **SFX Automatizado:** Adicionar efeitos de "Swoosh" nas transições de imagem e "Pop" no aparecimento das legendas.

### Fase 4: Automação Total (Operação Fantasma)
* **Trend Scraper:** Desenvolver um módulo para raspar ou consumir API de tendências do Google Trends ou X/Twitter. Se o CSV de temas estiver vazio, o próprio bot define o tema baseado no que está viral.
* **Orquestrador Resiliente:** Transferir o script para rodar com o Agendador de Tarefas do Windows ou PM2, contendo *Try/Catch* com logs rotativos diários.

---

## 3. Próximos Passos (Plano de Execução)

Podemos implementar essas mudanças por módulos, sem quebrar o bot atual. Recomendo a seguinte ordem:

1. **[Tarefa A] Audio & Múltiplas APIs:** Criar arquitetura de Fallback no módulo de áudio (ElevenLabs > OpenAI > Edge-TTS) + Implementar ducking da música de fundo (Item 1.3, 1.4, 1.6). ✅ **IMPLEMENTADO**
2. **[Tarefa B] LLM JSON & Visuais IA:** Alterar o `script_generator.py` para trazer as descrições das imagens e alterar o `visuals_fetcher.py` para usar IA (Leonardo.ai/DALL-E) integrando Fallbacks (Item 1.1, 1.2, 1.5). ✅ **IMPLEMENTADO**
3. **[Tarefa C] Edição Viral:** Refatorar o `video_editor.py` para incluir os SFX, transições rápidas (3 seg) e legendas destacadas. ✅ **IMPLEMENTADO**
4. **[Tarefa D] Motor de Automação:** Acoplar o "Buscador de Tendências" e configurar a execução autônoma à prova de falhas. ✅ **IMPLEMENTADO**

---

## 4. Guia de Uso Rápido (Novos Comandos)

```bash
# Modo clássico (tema manual)
python main.py --tema "dicas de produtividade" --sem-upload

# Modo Piloto Automático (busca temas virais sozinho)
python main.py --auto 3

# Modo Fantasma (gera 5 shorts/dia às 10h, todos os dias)
python main.py --auto 5 --agendar 10:00

# Modo Fantasma Multi-Horário (2 shorts, 3x/dia)
python main.py --auto 2 --agendar 08:00,14:00,20:00
```

## 5. Novas Variáveis de Ambiente (.env)

```env
ELEVENLABS_API_KEY=...      # Voz IA premium (prioridade 1)
OPENAI_API_KEY=...          # GPT-4o-mini (roteiro) + DALL-E 3 (visuais) + TTS (áudio prioridade 2)
LEONARDO_API_KEY=...        # Reservado para expansão futura
ELEVENLABS_VOICE_ID=...     # ID da voz desejada
OPENAI_VOICE=echo           # Voz OpenAI TTS
```
