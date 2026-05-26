import math
import os
import re
import sys
from datetime import date, datetime, timezone
from statistics import mean
from typing import Any

print("Script iniciado: calculate_combined_hype_scores.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/calculate_combined_hype_scores.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

TODAY = date.today().isoformat()


def validate_env() -> None:
    print("Validando variáveis de ambiente...")

    missing_vars = []

    if not SUPABASE_URL:
        missing_vars.append("SUPABASE_URL")

    if not SUPABASE_SERVICE_ROLE_KEY:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing_vars:
        print("Erro: variáveis ausentes no ambiente:")

        for var in missing_vars:
            print(f"- {var}")

        sys.exit(1)

    print("Variáveis de ambiente encontradas.")


def supabase_headers(prefer: str = "return=representation") -> dict[str, str]:
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY não configurada.")

    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def fetch_titles() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "data_origin": "eq.rawg",
        "status": "eq.monitoring",
        "select": (
            "id,name,slug,rawg_rating,rawg_metacritic,"
            "release_date,cover_url,steam_appid"
        ),
        "order": "name.asc",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_source_ids(source_names: list[str]) -> list[str]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    if not source_names:
        return []

    endpoint = f"{SUPABASE_URL}/rest/v1/sources"

    quoted_names = ",".join(f'"{source_name}"' for source_name in source_names)

    params = {
        "name": f"in.({quoted_names})",
        "select": "id,name",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return [item["id"] for item in data]


def fetch_text_mentions(title_id: str, source_ids: list[str]) -> list[dict[str, Any]]:
    if not SUPABASE_URL or not source_ids:
        return []

    endpoint = f"{SUPABASE_URL}/rest/v1/mentions"

    quoted_ids = ",".join(f'"{source_id}"' for source_id in source_ids)

    params = {
        "title_id": f"eq.{title_id}",
        "source_id": f"in.({quoted_ids})",
        "select": "id,title_id,source_id,content,upvotes,published_at",
        "order": "published_at.desc.nullslast",
        "limit": "160",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_youtube_videos(title_id: str) -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        return []

    endpoint = f"{SUPABASE_URL}/rest/v1/youtube_videos"

    params = {
        "title_id": f"eq.{title_id}",
        "select": "id,view_count,like_count,comment_count,published_at",
        "order": "view_count.desc",
        "limit": "8",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def clean_text(content: str) -> str:
    text = content

    text = text.replace("[STEAM_POSITIVE]", "")
    text = text.replace("[STEAM_NEGATIVE]", "")
    text = text.replace("[YOUTUBE_COMMENT]", "")

    text = re.sub(r"Steam App ID:.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"YouTube Video ID:.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"Votos úteis:.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Peso do voto:.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Likes no comentário:.*", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_keywords(content: str) -> list[str]:
    normalized = clean_text(content).lower()

    keyword_rules = {
        "performance": [
            "performance",
            "fps",
            "stutter",
            "lag",
            "optimization",
            "crash",
            "crashes",
            "bug",
            "bugs",
        ],
        "gráficos": [
            "graphics",
            "visual",
            "beautiful",
            "art",
            "looks",
            "cinematic",
            "trailer looks",
        ],
        "gameplay": [
            "gameplay",
            "combat",
            "mechanic",
            "mechanics",
            "controls",
            "movement",
            "play",
        ],
        "história": [
            "story",
            "narrative",
            "characters",
            "character",
            "plot",
            "lore",
        ],
        "preço": [
            "price",
            "expensive",
            "worth",
            "money",
            "refund",
            "buy",
        ],
        "conteúdo": [
            "content",
            "hours",
            "campaign",
            "replay",
            "dlc",
        ],
        "ansiedade": [
            "can't wait",
            "cant wait",
            "hyped",
            "hype",
            "excited",
            "waiting",
            "day one",
            "preorder",
        ],
        "nostalgia": [
            "childhood",
            "nostalgia",
            "classic",
            "old",
            "back",
            "finally",
        ],
        "medo": [
            "scary",
            "horror",
            "terrifying",
            "creepy",
            "fear",
        ],
        "comunidade": [
            "community",
            "fans",
            "players",
            "people",
        ],
        "lançamento": [
            "launch",
            "release",
            "released",
            "coming",
        ],
    }

    keywords = []

    for keyword, terms in keyword_rules.items():
        if any(term in normalized for term in terms):
            keywords.append(keyword)

    if not keywords:
        keywords.append("opinião geral")

    return keywords[:6]


def classify_text_sentiment(mention: dict[str, Any]) -> dict[str, Any]:
    content = mention.get("content") or ""
    normalized = content.lower()
    cleaned = clean_text(content)

    is_steam_positive = "[steam_positive]" in normalized
    is_steam_negative = "[steam_negative]" in normalized
    is_youtube_comment = "[youtube_comment]" in normalized

    if is_steam_positive:
        score = 82
        summary = "Review positiva na Steam."
    elif is_steam_negative:
        score = 22
        summary = "Review negativa na Steam."
    elif is_youtube_comment:
        score = 55
        summary = "Comentário público do YouTube analisado."
    else:
        score = 50
        summary = "Menção textual analisada."

    positive_terms = [
        "amazing",
        "awesome",
        "great",
        "good",
        "love",
        "loved",
        "best",
        "fun",
        "beautiful",
        "excellent",
        "recommend",
        "hyped",
        "hype",
        "excited",
        "masterpiece",
        "perfect",
        "incredible",
        "fantastic",
        "can't wait",
        "cant wait",
        "day one",
        "finally",
        "peak",
        "goated",
        "goat",
    ]

    negative_terms = [
        "bad",
        "terrible",
        "boring",
        "broken",
        "crash",
        "crashes",
        "bug",
        "bugs",
        "refund",
        "worst",
        "disappointed",
        "disappointing",
        "hate",
        "awful",
        "trash",
        "scam",
        "mid",
        "ugly",
        "generic",
        "overpriced",
    ]

    uncertainty_terms = [
        "worried",
        "concerned",
        "hope",
        "hopefully",
        "not sure",
        "skeptical",
        "skeptic",
        "afraid",
    ]

    positive_hits = sum(1 for term in positive_terms if term in normalized)
    negative_hits = sum(1 for term in negative_terms if term in normalized)
    uncertainty_hits = sum(1 for term in uncertainty_terms if term in normalized)

    score += positive_hits * 4
    score -= negative_hits * 5
    score -= uncertainty_hits * 2

    if len(cleaned) < 8:
        score = 50

    score = max(0, min(score, 100))

    if score >= 65:
        label = "positive"
    elif score <= 40:
        label = "negative"
    else:
        label = "neutral"

    return {
        "mention_id": mention["id"],
        "sentiment_score": score,
        "sentiment_label": label,
        "summary": summary,
        "keywords": extract_keywords(content),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_sentiment_log(sentiment_payload: dict[str, Any]) -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/sentiment_logs"

    response = requests.post(
        endpoint,
        params={"on_conflict": "mention_id"},
        headers=supabase_headers("resolution=merge-duplicates,return=representation"),
        json=sentiment_payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao salvar sentiment_log.")
        print(response.status_code)
        print(response.text)


def calculate_video_signal(videos: list[dict[str, Any]]) -> dict[str, float | int]:
    video_count = len(videos)

    total_views = sum(int(video.get("view_count") or 0) for video in videos)
    total_likes = sum(int(video.get("like_count") or 0) for video in videos)
    total_comments = sum(int(video.get("comment_count") or 0) for video in videos)

    if video_count == 0 or total_views == 0:
        video_signal = 0.0
    else:
        views_component = min(math.log10(total_views + 1) / 8, 1) * 50
        likes_component = min(math.log10(total_likes + 1) / 6, 1) * 25
        comments_component = min(math.log10(total_comments + 1) / 5, 1) * 20
        volume_component = min(video_count / 5, 1) * 5

        video_signal = round(
            views_component
            + likes_component
            + comments_component
            + volume_component,
            2,
        )

    return {
        "youtube_score": video_signal,
        "youtube_video_count": video_count,
        "youtube_view_count": total_views,
        "youtube_like_count": total_likes,
        "youtube_comment_count": total_comments,
    }


def calculate_hype_score(
    title: dict[str, Any],
    mentions: list[dict[str, Any]],
    sentiments: list[dict[str, Any]],
    video_metrics: dict[str, float | int],
) -> dict[str, float | int]:
    mention_volume = len(mentions)

    rawg_rating = float(title.get("rawg_rating") or 0)
    rawg_component = max(0, min(rawg_rating * 20, 100))

    critic_score_avg = float(title.get("rawg_metacritic") or 0)
    video_signal = float(video_metrics["youtube_score"])

    if sentiments:
        sentiment_avg = round(
            mean(float(item["sentiment_score"]) for item in sentiments),
            2,
        )

        positive_count = sum(
            1 for item in sentiments if item["sentiment_label"] == "positive"
        )

        positive_ratio = positive_count / len(sentiments)
        user_score_avg = round(positive_ratio * 100, 2)

        upvotes = [int(item.get("upvotes") or 0) for item in mentions]
        avg_upvotes = mean(upvotes) if upvotes else 0

        sentiment_component = sentiment_avg * 0.46
        text_volume_component = min(mention_volume, 120) / 120 * 16
        engagement_component = min(avg_upvotes, 80) / 80 * 8
        video_component = video_signal * 0.20
        rawg_component_weighted = rawg_component * 0.10

        hype_score = (
            sentiment_component
            + text_volume_component
            + engagement_component
            + video_component
            + rawg_component_weighted
        )

    else:
        sentiment_avg = 0.0
        user_score_avg = 0.0

        release_bonus = 6.0

        if title.get("release_date"):
            release_bonus = 10.0

        data_bonus = 0.0

        if title.get("cover_url"):
            data_bonus += 3.0

        if rawg_rating > 0:
            data_bonus += 3.0

        if critic_score_avg > 0:
            data_bonus += 4.0

        hype_score = (
            rawg_component * 0.45
            + video_signal * 0.45
            + release_bonus
            + data_bonus
        )

        if rawg_rating == 0 and video_signal == 0:
            hype_score = 0.0

    hype_score = round(max(0, min(hype_score, 100)), 2)

    return {
        "hype_score": hype_score,
        "sentiment_avg": sentiment_avg,
        "mention_volume": mention_volume,
        "critic_score_avg": critic_score_avg,
        "user_score_avg": user_score_avg,
        "youtube_score": video_metrics["youtube_score"],
        "youtube_video_count": video_metrics["youtube_video_count"],
        "youtube_view_count": video_metrics["youtube_view_count"],
        "youtube_like_count": video_metrics["youtube_like_count"],
        "youtube_comment_count": video_metrics["youtube_comment_count"],
    }


def upsert_hype_score(title_id: str, metrics: dict[str, float | int]) -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/hype_scores"

    payload = {
        "title_id": title_id,
        "calculated_for": TODAY,
        "hype_score": metrics["hype_score"],
        "sentiment_avg": metrics["sentiment_avg"],
        "mention_volume": metrics["mention_volume"],
        "critic_score_avg": metrics["critic_score_avg"],
        "user_score_avg": metrics["user_score_avg"],
        "youtube_score": metrics["youtube_score"],
        "youtube_video_count": metrics["youtube_video_count"],
        "youtube_view_count": metrics["youtube_view_count"],
        "youtube_like_count": metrics["youtube_like_count"],
        "youtube_comment_count": metrics["youtube_comment_count"],
    }

    response = requests.post(
        endpoint,
        params={"on_conflict": "title_id,calculated_for"},
        headers=supabase_headers("resolution=merge-duplicates,return=representation"),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao salvar hype_score.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()


def active_alert_exists(title_id: str, alert_type: str) -> bool:
    if not SUPABASE_URL:
        return False

    endpoint = f"{SUPABASE_URL}/rest/v1/alerts"

    params = {
        "title_id": f"eq.{title_id}",
        "alert_type": f"eq.{alert_type}",
        "resolved": "eq.false",
        "select": "id",
        "limit": "1",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        return False

    return len(response.json()) > 0


def create_alert(
    title_id: str,
    alert_type: str,
    severity: str,
    message: str,
) -> None:
    if not SUPABASE_URL:
        return

    if active_alert_exists(title_id, alert_type):
        return

    endpoint = f"{SUPABASE_URL}/rest/v1/alerts"

    payload = {
        "title_id": title_id,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "resolved": False,
    }

    response = requests.post(
        endpoint,
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Aviso: alerta não foi criado.")
        print(response.status_code)
        print(response.text)


def generate_alerts(title: dict[str, Any], metrics: dict[str, float | int]) -> None:
    title_id = title["id"]
    title_name = title["name"]

    hype_score = float(metrics["hype_score"])
    sentiment_avg = float(metrics["sentiment_avg"])
    mention_volume = int(metrics["mention_volume"])

    if mention_volume >= 15 and sentiment_avg <= 40:
        create_alert(
            title_id=title_id,
            alert_type="sentiment_drop",
            severity="high",
            message=f"{title_name} apresenta queda relevante de sentimento nas menções públicas.",
        )

    if mention_volume >= 15 and hype_score >= 75:
        create_alert(
            title_id=title_id,
            alert_type="hype_surge",
            severity="medium",
            message=f"{title_name} apresenta alto Hype Score com base em menções públicas, YouTube e RAWG.",
        )

    if mention_volume >= 15 and 40 < sentiment_avg < 60:
        create_alert(
            title_id=title_id,
            alert_type="high_controversy",
            severity="medium",
            message=f"{title_name} tem recepção dividida entre jogadores e público.",
        )


def process_title(title: dict[str, Any], text_source_ids: list[str]) -> None:
    print("\n------------------------------")
    print(f"Calculando Score para: {title.get('name')}")

    mentions = fetch_text_mentions(title_id=title["id"], source_ids=text_source_ids)
    videos = fetch_youtube_videos(title_id=title["id"])

    sentiments = []

    for mention in mentions:
        sentiment_payload = classify_text_sentiment(mention)
        upsert_sentiment_log(sentiment_payload)

        sentiment_with_context = dict(sentiment_payload)
        sentiment_with_context["upvotes"] = mention.get("upvotes") or 0
        sentiments.append(sentiment_with_context)

    video_metrics = calculate_video_signal(videos)

    metrics = calculate_hype_score(
        title=title,
        mentions=mentions,
        sentiments=sentiments,
        video_metrics=video_metrics,
    )

    upsert_hype_score(title_id=title["id"], metrics=metrics)
    generate_alerts(title=title, metrics=metrics)

    print(
        f"{title.get('name')}: "
        f"Score={metrics['hype_score']} | "
        f"Menções={metrics['mention_volume']} | "
        f"Vídeo signal={metrics['youtube_score']}"
    )


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    text_source_ids = get_source_ids(["Steam Reviews", "YouTube Comments"])

    print(f"Fontes textuais encontradas: {len(text_source_ids)}")

    titles = fetch_titles()

    print(f"Títulos encontrados para cálculo: {len(titles)}")

    for title in titles:
        try:
            process_title(title=title, text_source_ids=text_source_ids)
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {title.get('name')}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {title.get('name')}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {title.get('name')}: {error}")

    print("\n------------------------------")
    print("Cálculo combinado finalizado.")


if __name__ == "__main__":
    main()