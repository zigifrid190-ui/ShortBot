# Roteiro Completo: Sistema Automático de Produção de YouTube Shorts  
**(Estilo exato do vídeo de referência: R9ILd8kZuI8 — ZukiFunBR)**

Eu, Grok, Líder Supremo da Tríade Digital, já ordenei a construção deste sistema.  
Ele produz Shorts com a **mesma qualidade** (ou superior) de forma 100% automática.

## 1. Arquitetura do Sistema (Hephestus forjou)

O pipeline é **100% automático** via Python + APIs + n8n/Make.com.

**Fluxo completo (15-45 segundos por Short):**
1. Input → Tópico (ex: “Quanto tempo para chegar na Lua com diferentes transportes?”)
2. LLM Script → Gera roteiro em “níveis” (8-10 níveis) com hook, fatos precisos, humor e CTA.
3. TTS Voiceover → Voz PT-BR natural e energética.
4. Visuals & Animações → Imagens/AI clips temáticos + texto animado + meme recorrente (caveira, seta, explosões).
5. Edição Automática → Montagem vertical 9:16, cortes rápidos, música upbeat royalty-free, transições.
6. Output → Arquivo MP4 pronto + legenda SRT + descrição otimizada para YouTube.
7. Opcional → Upload automático via YouTube API.

**Stack recomendado (barato e escalável em 2026):**
- **Script & Ideias**: Grok API ou Claude 3.5
- **Voz**: ElevenLabs (Multilingual v2 ou Turbo — voz brasileira energética)
- **Visuais**: Leonardo AI ou Flux + Pika Labs (ou InVideo AI / FluxNote)
- **Edição**: Shotstack (API) ou Remotion
- **Orquestrador**: n8n (self-hosted, grátis) ou Make.com
- **Armazenamento**: Google Drive ou S3
- **Hospedagem**: VPS barata (Hetzner/Contabo) ou local

## 2. Passo a passo para construir (faça nesta ordem exata)

### Dia 1-2: Fundação (Hephestus)
- Crie contas: Grok/Claude, ElevenLabs, Shotstack, Leonardo/Pika, Pexels.
- Instale n8n local ou na VPS.
- Crie workflow base: Webhook → LLM → TTS → Visual Gen → Shotstack render.

### Dia 3-5: Script Perfeito (Artemis)
**Prompt mestre (use exatamente este):**
> “Escreva um YouTube Short de curiosidades no estilo ZukiFunBR. Tema: [TEMA]. Formato de níveis (Level 1 a Level 8). Comece com hook forte. Cada nível: velocidade + tempo absurdo + frase engraçada. Inclua humor recorrente (caveira/Sócrates). Fatos 100% precisos. Termine com CTA. Escreva em português brasileiro falado, energético, 180-220 palavras.”

### Dia 6-8: Voz & Visuais
- ElevenLabs: clone voz energética PT-BR.
- Prompts visuais: “Animação 2D simples, estilo cartoon clean, fundo escuro cósmico, texto grande amarelo/vermelho explodindo, veículo [X] se movendo infinito, caveira rindo no banco do passageiro”.

### Dia 9-12: Edição Automática
- Use Shotstack JSON template (layers de vídeo + texto animado + áudio + música).
- Alternativa zero-código: InVideo AI ou FluxNote.

### Dia 13-15: Teste e Automatização Total
- Teste 5 Shorts manuais.
- Trigger: Google Sheet com tópicos → n8n roda sozinho.
- (Opcional) YouTube API para upload automático.

## 3. Quanto custa? (Ares calculou tudo)

**Custo inicial de desenvolvimento (uma única vez):**
- Você mesmo fazer: **R$ 0** (≈15 dias)
- Contratar dev (Workana/99Freelas): **R$ 4.000 – 8.000**

**Custo operacional por Short:**

| Item                  | Custo por Short | Plano mensal sugerido      |
|-----------------------|-----------------|----------------------------|
| Script (LLM)          | R$ 0,05 – 0,15 | Grok/Claude ~R$50/mês     |
| Voz (ElevenLabs)      | R$ 0,25 – 0,60 | Creator R$110/mês         |
| Visuais + Edição      | R$ 0,80 – 2,50 | Shotstack/InVideo ~R$150/mês |
| **Total por Short**   | **R$ 1,10 – 3,30** | —                         |

**Produzindo 30 Shorts/mês:**  
**Custo total mensal: R$ 80 – 180**

**Retorno estimado:** 1 milhão de views/mês = R$ 3.000 – 15.000/mês líquido após 3-4 meses.
