# Planejamento: ShortBot 3.0 - A Máquina Definitiva

Após o sucesso absoluto e a estabilização da versão 2.0 (Pipeline Multi-Agente, B-Rolls Dinâmicos e Agendamento Anti-Spam), o foco da **Versão 3.0** é expansão de alcance, qualidade sensorial e usabilidade. 

Abaixo estão os 4 pilares arquiteturais para a próxima evolução do sistema:

---

## 1. 📱 Dominação Multi-Plataforma (Reels & TikTok)
**O que é:** O bot não se limitará mais ao YouTube. Todo vídeo gerado será distribuído automaticamente para as outras duas maiores redes de vídeos curtos.
**Como implementar:**
- Expandir o `uploader.py` para suportar conexões adicionais.
- **Instagram Reels:** Integração via Facebook Graph API (Instagram for Business).
- **TikTok:** Integração via TikTok Content Posting API ou automação headless (Playwright/Selenium) caso a API oficial seja restrita.
- **Resultado:** 1 renderização de vídeo gerando 3x mais tráfego e visibilidade.

## 2. 🎛️ Efeitos Sonoros Dinâmicos e Espaciais (SFX)
**O que é:** Adicionar a mesma engenharia de som usada pelos maiores editores do YouTube (estilo Hormozi/MrBeast), onde palavras-chave disparam sons específicos para manter o cérebro do usuário engajado.
**Como implementar:**
- Atualizar o `script_generator.py` para que o GPT-4o retorne marcações de tempo/palavras para SFX. 
- *Exemplo de JSON:* `{"sfx": [{"tipo": "caixa_registradora", "palavra": "dinheiro"}]}`.
- Ter uma pasta `assets/sfx/` com sons prontos (explosão, *whoosh*, dinheiro, erro, sino).
- O `video_editor.py` fará a mixagem matemática no MoviePy para o som tocar no milissegundo exato que a palavra aparecer na legenda.

## 3. 📊 Motor de Analytics & Retroalimentação Viral
**O que é:** O bot passará a "aprender" com o próprio sucesso. Ele saberá o que viraliza no SEU canal e focará nesses nichos sozinho.
**Como implementar:**
- Criar um novo módulo `analytics_engine.py` que roda 1x ao dia.
- Ele lê a YouTube Data API para puxar as *views*, *likes* e *retenção* dos últimos vídeos.
- Se o algoritmo detectar que o tema "História Bizarra" pegou 5.000 views e "Finanças" pegou 100 views, ele injeta os dados num prompt do Llama 3: *"Llama, o tema 'História Bizarra' viralizou. Gere 10 novos temas idênticos a esse"*.
- **Resultado:** Um ciclo de retroalimentação autossustentável (Self-Learning Viral Loop).

## 4. 🖥️ Painel de Controle (Dashboard Web)
**O que é:** Tirar a dependência exclusiva do terminal preto (CLI) e dar ao ShortBot uma interface gráfica de nível comercial.
**Como implementar:**
- Construir uma interface leve rodando localmente (usando **Streamlit**, **Flask** ou **FastAPI** + React).
- **Features do Painel:**
  - Botão gigante de "Gerar Novo Lote".
  - Calendário visual mostrando os horários dos vídeos agendados.
  - Player de vídeo embutido para aprovar os curtas antes de postar.
  - Gráficos puxando os dados do módulo de Analytics.
  - Mostrador de saldo/custos estimado das APIs (ElevenLabs/OpenAI).

---

## 🛠️ Roteiro de Execução

Marque com um "x" por onde você quer que a engenharia comece:

- [ ] Fase 1: Interface Gráfica (Painel Web)
- [ ] Fase 2: Dominação Multi-Plataforma
- [ ] Fase 3: Efeitos Sonoros Dinâmicos (SFX)
- [ ] Fase 4: Motor de Analytics
