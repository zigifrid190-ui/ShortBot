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

    # 2. Formatar a mensagem do WhatsApp
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

    # 3. Enviar para o WhatsApp via CallMeBot
    phone = "5598985626885"
    apikey = "3982252"
    encoded_msg = urllib.parse.quote(msg)

    callmebot_url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={apikey}"

    safe_print("Enviando mensagem para o WhatsApp via CallMeBot...")
    try:
        req_whatsapp = urllib.request.Request(
            callmebot_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        resp_whatsapp = urllib.request.urlopen(req_whatsapp, timeout=30)
        response_text = resp_whatsapp.read().decode('utf-8')
        safe_print(f"Resposta do CallMeBot: {response_text}")
        safe_print("Sucesso! Mensagem de teste enviada.")
    except Exception as e:
        safe_print(f"Erro ao enviar via CallMeBot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
