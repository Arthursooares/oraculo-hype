import os
import re
import sys
from datetime import date
from statistics import mean
from typing import Any

print("Script iniciado: calculate_steam_community_scores.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/calculate_steam_community_scores.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def validate_env() -> None:
    print("Validando variáveis de ambiente...")

    missing_vars = []

    if not SUPABASE_URL:
        missing_vars.append("SUPABASE_URL")

    if not SUPABASE_SERVICE_ROLE_KEY:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing_vars:
        print("Erro: variáveis ausentes no arquivo .env:")

        for var in missing_vars:
            print(f"- {var}")

        sys.exit(1)

    print("Variáveis de ambiente encontradas.")


def supabase_headers() -> dict[str, str]:
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY não configurada.")

    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def get_source_id() -> str:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/sources"

    params = {
        "name": "eq.Steam Reviews",
        "select": "id,name",
        "limit": "1",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        raise RuntimeError("Fonte Steam Reviews não encontrada.")

    return data[0]["id"]


def fetch_rawg_titles() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "data_origin": "eq.rawg",
        "select": (
            "id,name,slug,rawg_rating,rawg_metacritic,"
            "release_date,cover_url,data_origin"
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


def fetch_mentions_for_title(title_id: str, source_id: str) -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/mentions"

    params = {
        "title_id": f"eq.{title_id}",
        "source_id": f"eq.{source_id}",
        "select": "id,title_id,source_id,external_id,content,upvotes,published_at",
        "order": "published_at.desc",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def clean_review_text(content: str) -> str:
    content = content.replace("[STEAM_POSITIVE]", "")
    content = content.replace("[STEAM_NEGATIVE]", "")
    content = re.sub(r"Steam App ID:.*", "", content, flags=re.DOTALL)
    content = re.sub(r"\s+", " ", content)

    return content.strip()


def extract_keywords(content: str) -> list[str]:
    normalized = content.lower()

    keyword_rules = {
        "desempenho": [
            "performance",
            "fps",
            "stutter",
            "optimization",
            "optimized",
            "lag",
            "crash",
            "crashes",
            "bug",
            "bugs",
        ],
        "gráficos": [
            "graphics",
            "visuals",
            "beautiful",
            "art",
            "world",
            "environment",
        ],
        "gameplay": [
            "gameplay",
            "combat",
            "mechanics",
            "controls",
            "movement",
            "build",
        ],
        "história": [
            "story",
            "narrative",
            "characters",
            "writing",
            "ending",
            "dialogue",
        ],
        "preço": [
            "price",
            "expensive",
            "worth",
            "money",
            "refund",
            "sale",
        ],
        "conteúdo": [
            "content",
            "hours",
            "campaign",
            "missions",
            "quests",
            "replay",
        ],
        "comunidade": [
            "fans",
            "community",
            "players",
            "reviews",
            "mixed",
        ],
        "lançamento": [
            "launch",
            "release",
            "day one",
            "early access",
            "preorder",
        ],
    }

    keywords = []

    for label, terms in keyword_rules.items():
        if any(term in normalized for term in terms):
            keywords.append(label)

    if not keywords:
        keywords.append("opinião geral")

    return keywords[:6]


def classify_steam_sentiment(content: str) -> dict[str, Any]:
    normalized = content.lower()

    is_positive = "[steam_positive]" in normalized
    is_negative = "[steam_negative]" in normalized

    clean_text = clean_review_text(content)
    keywords = extract_keywords(clean_text)

    if is_positive:
        score = 82.0
        label = "positive"
        summary = "Review positiva da Steam. Usuário recomenda o jogo."
    elif is_negative:
        score = 22.0
        label = "negative"
        summary = "Review negativa da Steam. Usuário não recomenda o jogo."
    else:
        score = 50.0
        label = "neutral"
        summary = "Review sem sinal explícito suficiente para classificação automática."

    criticism_terms = [
        "bad",
        "bug",
        "bugs",
        "crash",
        "crashes",
        "boring",
        "refund",
        "unplayable",
        "broken",
        "stutter",
        "poorly optimized",
    ]

    praise_terms = [
        "great",
        "amazing",
        "excellent",
        "love",
        "loved",
        "masterpiece",
        "fun",
        "beautiful",
        "recommend",
    ]

    if is_positive and any(term in normalized for term in criticism_terms):
        score = 68.0
        summary = "Review recomenda o jogo, mas menciona críticas ou problemas técnicos."

    if is_negative and any(term in normalized for term in praise_terms):
        score = 38.0
        summary = "Review não recomenda o jogo, mas reconhece aspectos positivos."

    return {
        "sentiment_score": score,
        "sentiment_label": label,
        "summary": summary,
        "keywords": keywords,
    }


def upsert_sentiment_log(mention: dict[str, Any], sentiment: dict[str, Any]) -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/sentiment_logs"

    payload = {
        "mention_id": mention["id"],
        "sentiment_score": sentiment["sentiment_score"],
        "sentiment_label": sentiment["sentiment_label"],
        "summary": sentiment["summary"],
        "keywords": sentiment["keywords"],
    }

    params = {
        "on_conflict": "mention_id",
    }

    response = requests.post(
        endpoint,
        params=params,
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao salvar sentiment_log.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()


def calculate_hype_score(
    title: dict[str, Any],
    mentions: list[dict[str, Any]],
    sentiments: list[dict[str, Any]],
) -> dict[str, float | int]:
    mention_volume = len(mentions)

    if sentiments:
        sentiment_avg = round(
            mean(float(item["sentiment_score"]) for item in sentiments),
            2,
        )
    else:
        sentiment_avg = 0.0

    rawg_rating = float(title.get("rawg_rating") or 0)
    rawg_component = min(rawg_rating * 20, 100)

    upvotes = [int(item.get("upvotes") or 0) for item in mentions]
    avg_upvotes = mean(upvotes) if upvotes else 0

    sentiment_component = sentiment_avg * 0.55
    volume_component = min(mention_volume, 50) / 50 * 25
    engagement_component = min(avg_upvotes, 50) / 50 * 10
    rawg_component_weighted = rawg_component * 0.10

    hype_score = (
        sentiment_component
        + volume_component
        + engagement_component
        + rawg_component_weighted
    )

    hype_score = round(max(0, min(hype_score, 100)), 2)

    positive_count = sum(
        1 for item in sentiments if item["sentiment_label"] == "positive"
    )

    positive_ratio = positive_count / len(sentiments) if sentiments else 0

    user_score_avg = round(positive_ratio * 100, 2)

    critic_score_avg = float(title.get("rawg_metacritic") or 0)

    return {
        "hype_score": hype_score,
        "sentiment_avg": sentiment_avg,
        "mention_volume": mention_volume,
        "critic_score_avg": critic_score_avg,
        "user_score_avg": user_score_avg,
    }


def upsert_hype_score(title: dict[str, Any], score: dict[str, float | int]) -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/hype_scores"

    payload = {
        "title_id": title["id"],
        "hype_score": score["hype_score"],
        "sentiment_avg": score["sentiment_avg"],
        "mention_volume": score["mention_volume"],
        "critic_score_avg": score["critic_score_avg"],
        "user_score_avg": score["user_score_avg"],
        "calculated_for": date.today().isoformat(),
    }

    params = {
        "on_conflict": "title_id,calculated_for",
    }

    response = requests.post(
        endpoint,
        params=params,
        headers=supabase_headers(),
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
        raise RuntimeError("SUPABASE_URL não configurada.")

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

    response.raise_for_status()

    return bool(response.json())


def create_alert(
    title: dict[str, Any],
    alert_type: str,
    severity: str,
    message: str,
) -> None:
    if active_alert_exists(title["id"], alert_type):
        return

    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/alerts"

    payload = {
        "title_id": title["id"],
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "resolved": False,
    }

    response = requests.post(
        endpoint,
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao criar alerta.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()


def generate_alerts(
    title: dict[str, Any],
    mentions: list[dict[str, Any]],
    sentiments: list[dict[str, Any]],
    score: dict[str, float | int],
) -> None:
    mention_volume = int(score["mention_volume"])
    user_score_avg = float(score["user_score_avg"])
    sentiment_avg = float(score["sentiment_avg"])

    if mention_volume >= 10 and user_score_avg >= 75:
        create_alert(
            title=title,
            alert_type="hype_surge",
            severity="high",
            message=(
                f"{title['name']} apresenta forte recepção positiva nas reviews "
                "recentes da Steam."
            ),
        )

    if mention_volume >= 10 and user_score_avg <= 35:
        create_alert(
            title=title,
            alert_type="sentiment_drop",
            severity="high",
            message=(
                f"{title['name']} apresenta queda de sentimento nas reviews "
                "recentes da Steam."
            ),
        )

    if mention_volume >= 10 and 35 < user_score_avg < 65:
        create_alert(
            title=title,
            alert_type="high_controversy",
            severity="medium",
            message=(
                f"{title['name']} apresenta recepção dividida nas reviews "
                "recentes da Steam."
            ),
        )

    if mention_volume >= 10 and sentiment_avg < 40:
        create_alert(
            title=title,
            alert_type="review_bombing",
            severity="medium",
            message=(
                f"{title['name']} tem concentração relevante de reviews negativas "
                "recentes e merece monitoramento."
            ),
        )


def process_title(title: dict[str, Any], source_id: str) -> None:
    print("\n------------------------------")
    print(f"Processando: {title['name']}")

    mentions = fetch_mentions_for_title(title["id"], source_id)

    print(f"Menções encontradas: {len(mentions)}")

    sentiments = []

    for mention in mentions:
        sentiment = classify_steam_sentiment(mention["content"])
        upsert_sentiment_log(mention, sentiment)
        sentiments.append(sentiment)

    score = calculate_hype_score(title, mentions, sentiments)
    upsert_hype_score(title, score)
    generate_alerts(title, mentions, sentiments, score)

    print(
        f"Resultado: {title['name']} | "
        f"Hype {score['hype_score']} | "
        f"Sentimento {score['sentiment_avg']} | "
        f"Menções {score['mention_volume']} | "
        f"Usuários {score['user_score_avg']}"
    )


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    source_id = get_source_id()

    titles = fetch_rawg_titles()

    print(f"Títulos RAWG encontrados: {len(titles)}")

    for title in titles:
        process_title(title, source_id)

    print("\nCálculo de comunidade Steam finalizado.")


if __name__ == "__main__":
    main()