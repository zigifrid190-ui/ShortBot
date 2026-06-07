"""
Gerador de Relatório Semanal do ShortBot.

Lê all_video_stats.json (gerado por scrape_all_stats.py) e produz:
  - Relatório em Markdown salvo em relatorios/
  - JSON estruturado para consumo pelo webhook / n8n

Uso direto:
    python generate_weekly_report.py

Via webhook (n8n chama GET /weekly_report):
    O webhook_server.py chama este módulo e retorna o JSON.
"""

import os
import json
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "all_video_stats.json")
REPORTS_DIR = os.path.join(BASE_DIR, "relatorios")


# ---- Thresholds de alerta (conforme roteiro 02) ----
ALERT_MIN_VIEWS_48H = 300
ALERT_MIN_RETENTION_FINAL = 40.0   # % — não temos retenção real via scraping público
ALERT_MAX_CTR_LOW = 8.0            # % — não disponível via scraping; campo reservado
ALERT_MAX_SAME_THEME = 3           # vezes num mesmo tema na semana


def _load_stats() -> list:
    if not os.path.exists(STATS_FILE):
        return []
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _filter_last_7_days(stats: list) -> list:
    """Filtra vídeos das últimas 7 dias com base no campo logged_at."""
    cutoff = datetime.now() - timedelta(days=7)
    recent = []
    for v in stats:
        try:
            logged = datetime.fromisoformat(str(v.get("logged_at", "")).replace("Z", ""))
            if logged >= cutoff:
                recent.append(v)
        except Exception:
            # logged_at pode ser só data sem hora — tenta apenas a data
            try:
                logged = datetime.strptime(str(v.get("logged_at", ""))[:10], "%Y-%m-%d")
                if logged >= cutoff:
                    recent.append(v)
            except Exception:
                pass
    # Se não encontrou nenhum com data válida, usa todos
    return recent if recent else stats


def _detect_alerts(videos: list, all_stats: list) -> list:
    """Gera lista de alertas baseada nos thresholds definidos."""
    alerts = []

    low_view_videos = [v for v in videos if v.get("views", 0) < ALERT_MIN_VIEWS_48H and v.get("views", 0) > 0]
    if low_view_videos:
        alerts.append(
            f"⚠️ {len(low_view_videos)} vídeo(s) com menos de {ALERT_MIN_VIEWS_48H} views — possível distribuição limitada."
        )

    # Verifica repetição de tema
    from collections import Counter
    themes = [v.get("theme", "desconhecido") for v in videos]
    theme_counts = Counter(themes)
    repeated = [(t, c) for t, c in theme_counts.items() if c > ALERT_MAX_SAME_THEME]
    for tema, count in repeated:
        alerts.append(f"⚠️ Tema '{tema}' apareceu {count}x esta semana — risco de penalização por repetição.")

    if not alerts:
        alerts.append("✅ Nenhum alerta crítico esta semana.")

    return alerts


def _load_historical_summary() -> list:
    """Carrega resumos das últimas 4 semanas de relatórios anteriores."""
    history = []
    if not os.path.exists(REPORTS_DIR):
        return history
    report_files = sorted(
        [f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")],
        reverse=True
    )[:4]
    for fname in report_files:
        try:
            with open(os.path.join(REPORTS_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            history.append({
                "semana": data.get("periodo_inicio", fname),
                "total_videos": data.get("total_videos", 0),
                "views_totais": data.get("views_totais", 0),
                "media_quality_score": data.get("media_quality_score", "N/A"),
                "alertas": len(data.get("alertas", [])),
            })
        except Exception:
            pass
    return history


def generate_report() -> dict:
    """
    Gera o relatório semanal completo.
    Retorna dict com todos os dados (usado pelo webhook para retornar JSON ao n8n).
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    all_stats = _load_stats()
    videos = _filter_last_7_days(all_stats)

    now = datetime.now()
    periodo_fim = now.strftime("%Y-%m-%d")
    periodo_inicio = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    # Ordena por views decrescente
    videos_sorted = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)
    top3 = videos_sorted[:3]
    bottom3 = [v for v in videos_sorted if v.get("views", 0) > 0][-3:][::-1]

    total_views = sum(v.get("views", 0) for v in videos)
    total_likes = sum(v.get("likes", 0) for v in videos)
    total_comments = sum(v.get("comments", 0) for v in videos)
    avg_engagement = (
        sum(v.get("engagement", 0.0) for v in videos) / len(videos)
        if videos else 0.0
    )
    avg_quality_score = None
    scores = [v.get("quality_score") for v in videos if v.get("quality_score") is not None]
    if scores:
        avg_quality_score = round(sum(scores) / len(scores), 1)

    alerts = _detect_alerts(videos, all_stats)
    history = _load_historical_summary()

    # ---- Recomendações automáticas baseadas nos dados ----
    recommendations = []
    if bottom3:
        worst = bottom3[0]
        recommendations.append(
            f"🔧 Roteiro com pior engajamento: '{worst.get('title', worst.get('theme'))}' "
            f"({worst.get('views', 0)} views). Analise a estrutura do gancho e evite repetir."
        )
    if top3:
        best = top3[0]
        recommendations.append(
            f"✅ Melhor desempenho: '{best.get('title', best.get('theme'))}' "
            f"({best.get('views', 0)} views). Explore variações deste tema/ângulo."
        )
    if avg_quality_score and avg_quality_score < 7:
        recommendations.append(
            f"⚠️ Quality score médio abaixo de 7 ({avg_quality_score}). "
            "Revise os prompts ou ajuste o threshold de qualidade."
        )
    if not recommendations:
        recommendations.append("📈 Sistema dentro dos parâmetros normais. Mantenha a estratégia atual.")

    report_data = {
        "gerado_em": now.isoformat(),
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim,
        "total_videos": len(videos),
        "views_totais": total_views,
        "likes_totais": total_likes,
        "comments_totais": total_comments,
        "media_engagement_pct": round(avg_engagement, 2),
        "media_quality_score": avg_quality_score,
        "top_3": [
            {
                "titulo": v.get("title") or v.get("theme", "Sem título"),
                "tema": v.get("theme"),
                "views": v.get("views", 0),
                "likes": v.get("likes", 0),
                "comments": v.get("comments", 0),
                "engagement_pct": round(v.get("engagement", 0.0), 2),
                "viral_rate_pct": round(v.get("viral_rate", 0.0), 2),
                "quality_score": v.get("quality_score"),
                "video_id": v.get("video_id"),
            }
            for v in top3
        ],
        "bottom_3": [
            {
                "titulo": v.get("title") or v.get("theme", "Sem título"),
                "tema": v.get("theme"),
                "views": v.get("views", 0),
                "likes": v.get("likes", 0),
                "engagement_pct": round(v.get("engagement", 0.0), 2),
                "viral_rate_pct": round(v.get("viral_rate", 0.0), 2),
                "quality_score": v.get("quality_score"),
                "video_id": v.get("video_id"),
            }
            for v in bottom3
        ],

        "alertas": alerts,
        "recomendacoes": recommendations,
        "historico_4_semanas": history,
    }

    # ---- Gera Markdown ----
    md = _render_markdown(report_data, top3, bottom3, alerts, recommendations, history)

    # Salva Markdown
    md_filename = f"semana_{periodo_inicio}.md"
    md_path = os.path.join(REPORTS_DIR, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    # Salva JSON para histórico
    json_filename = f"semana_{periodo_inicio}.json"
    json_path = os.path.join(REPORTS_DIR, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Relatorio salvo em: {md_path}")
    report_data["markdown_path"] = md_path
    report_data["json_path"] = json_path
    return report_data



def _render_markdown(data: dict, top3: list, bottom3: list, alerts: list,
                     recommendations: list, history: list) -> str:
    lines = [
        f"# 📊 Relatório ShortBot — {data['periodo_inicio']} a {data['periodo_fim']}",
        "",
        "## Resumo Geral",
        f"- **Total de Shorts postados:** {data['total_videos']}",
        f"- **Views totais da semana:** {data['views_totais']:,}",
        f"- **Likes totais:** {data['likes_totais']:,}",
        f"- **Comentários totais:** {data['comments_totais']:,}",
        f"- **Engajamento médio:** {data['media_engagement_pct']}%",
        f"- **Quality Score médio (IA):** {data['media_quality_score'] or 'N/A'}/10",
        "",
        "---",
        "",
        "## 🏆 Top 3 Melhores",
    ]
    for i, v in enumerate(top3, 1):
        yt_link = f"https://youtube.com/shorts/{v.get('video_id', '')}" if v.get("video_id") else ""
        lines.append(
            f"{i}. **{v.get('titulo', 'Sem título')}** | "
            f"Views: {v.get('views', 0):,} | "
            f"Likes: {v.get('likes', 0):,} | "
            f"Engajamento: {v.get('engagement_pct', 0)}% | "
            f"QScore: {v.get('quality_score', 'N/A')} | "
            f"[Ver no YouTube]({yt_link})" if yt_link else
            f"{i}. **{v.get('titulo', 'Sem título')}** | Views: {v.get('views', 0):,}"
        )

    lines += ["", "## 📉 Bottom 3 (Atenção)"]
    for i, v in enumerate(bottom3, 1):
        yt_link = f"https://youtube.com/shorts/{v.get('video_id', '')}" if v.get("video_id") else ""
        lines.append(
            f"{i}. **{v.get('titulo', 'Sem título')}** | "
            f"Views: {v.get('views', 0):,} | "
            f"Engajamento: {v.get('engagement_pct', 0)}% | "
            f"QScore: {v.get('quality_score', 'N/A')} | "
            f"Tema: {v.get('tema', '?')}"
        )

    lines += ["", "---", "", "## 🚨 Sinais de Alerta"]
    for alert in alerts:
        lines.append(f"- {alert}")

    lines += ["", "---", "", "## 💡 Recomendações para Próxima Semana"]
    for rec in recommendations:
        lines.append(f"- {rec}")

    if history:
        lines += ["", "---", "", "## 📅 Histórico (últimas semanas)", ""]
        lines.append("| Semana | Vídeos | Views Totais | Alertas |")
        lines.append("|--------|--------|-------------|---------|")
        for h in history:
            lines.append(
                f"| {h['semana']} | {h['total_videos']} | {h['views_totais']:,} | {h['alertas']} |"
            )

    lines += [
        "",
        "---",
        f"*Gerado automaticamente pelo ShortBot em {data['gerado_em'][:16].replace('T', ' ')}*",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    result = generate_report()
    summary = {
        k: v for k, v in result.items()
        if k not in ("markdown_path", "json_path", "top_3", "bottom_3", "historico_4_semanas")
    }
    output = "\n--- DADOS DO RELATORIO ---\n" + json.dumps(summary, ensure_ascii=False, indent=2)
    output += f"\n\nMarkdown: {result.get('markdown_path')}\n"
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.flush()

