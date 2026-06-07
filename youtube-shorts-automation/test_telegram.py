import urllib.request
import urllib.parse
import json
import sys

def safe_print(text):
    try:
        sys.stdout.buffer.write((text + "\n").encode('utf-8'))
    except Exception:
        print(text.encode('ascii', errors='replace').decode('ascii'))

def main():
    # 1. Chamar o webhook local
    url_report = "http://localhost:8090/weekly_report"
    safe_print("Chamando o webhook em http://localhost:8090/weekly_report...")
    safe_print("Isso pode levar de 30 a 90 segundos porque ele roda o scraper e atualiza as estatísticas...")
    
    try:
        req = urllib.request.Request(url_report)
        resp = urllib.request.urlopen(req, timeout=180)
        report = json.loads(resp.read().decode('utf-8'))
        safe_print("Dados do relatório obtidos com sucesso do Webhook!")
    except Exception as e:
        safe_print(f"Erro ao chamar o webhook: {e}")
        sys.exit(1)

    # 2. Formatar a mensagem do Telegram
    msg = "📊 *ShortBot - Relatório Semanal de Desempenho*\n\n"
    msg += f"📅 *Período*: {report.get('periodo_inicio')} a {report.get('periodo_fim')}\n"
    msg += f"📹 *Vídeos Publicados na Semana*: {report.get('total_videos')}\n"
    msg += f"👁️ *Views Totais*: {report.get('views_totais')}\n"
    msg += f"❤️ *Likes Totais*: {report.get('likes_totais')}\n"
    msg += f"💬 *Comentários*: {report.get('comments_totais')}\n"
    msg += f"📈 *Engajamento Médio*: {report.get('media_engagement_pct')}%\n"
    
    score = report.get('media_quality_score')
    if score is not None:
        msg += f"✨ *Score de Qualidade Médio*: {score}/10\n"
    msg += "\n"

    # Top Vídeos
    msg += "🏆 *TOP 3 Vídeos da Semana*:\n"
    top_3 = report.get('top_3', [])
    if top_3:
        for i, v in enumerate(top_3):
            emoji = ["1️⃣", "2️⃣", "3️⃣"][i]
            msg += f"{emoji} *{v.get('titulo', 'Sem título')}*\n"
            msg += f"   👁️ *{v.get('views', 0)}* views | ❤️ *{v.get('likes', 0)}* likes\n"
    else:
        msg += "Nenhum vídeo com visualizações nesta semana.\n"
    msg += "\n"

    # Alertas
    alertas = report.get('alertas', [])
    if alertas:
        msg += "🚨 *Alertas*:\n"
        for al in alertas:
            msg += f"• {al}\n"
        msg += "\n"

    # Recomendações
    recos = report.get('recomendacoes', [])
    if recos:
        msg += "💡 *Recomendações*:\n"
        for rec in recos:
            msg += f"• {rec}\n"
        msg += "\n"

    msg += "🚀 ShortBot operacional!"

    # 3. Enviar para o Telegram
    bot_token = "8836464936:AAHJ1UHqt0N6ECwd1ACMzmD2g_Lv7t_Khe8"
    chat_id = "5330885633"
    
    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    safe_print("Enviando mensagem para o Telegram...")
    try:
        data_bytes = json.dumps(payload).encode('utf-8')
        req_telegram = urllib.request.Request(
            telegram_url, 
            data=data_bytes,
            headers=headers,
            method="POST"
        )
        resp_telegram = urllib.request.urlopen(req_telegram, timeout=30)
        response_text = resp_telegram.read().decode('utf-8')
        safe_print(f"Resposta do Telegram: {response_text}")
        safe_print("Sucesso! Relatório enviado para o Telegram.")
    except Exception as e:
        safe_print(f"Erro ao enviar para o Telegram: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
