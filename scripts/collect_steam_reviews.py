import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

print("Script iniciado: collect_steam_reviews.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/collect_steam_reviews.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

STEAM_REVIEWS_BASE_URL = "https://store.steampowered.com/appreviews"
MAX_REVIEWS_PER_GAME = 40
MAX_GAMES_PER_RUN = 25


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


def supabase_headers() -> dict[str, str]:
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY não configurada.")

    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def ensure_steam_source() -> str:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/sources"

    payload = {
        "name": "Steam Reviews",
        "source_type": "community",
        "base_url": "https://store.steampowered.com",
    }

    response = requests.post(
        endpoint,
        params={"on_conflict": "name"},
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao garantir fonte Steam Reviews.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    return get_source_id()


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
        raise RuntimeError("Fonte Steam Reviews não encontrada na tabela sources.")

    return data[0]["id"]


def fetch_titles_with_steam_appid() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "steam_appid": "not.is.null",
        "select": "id,name,slug,steam_appid",
        "order": "last_synced_at.desc.nullslast",
        "limit": str(MAX_GAMES_PER_RUN),
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_steam_reviews(appid: int, max_reviews: int = MAX_REVIEWS_PER_GAME) -> list[dict[str, Any]]:
    print(f"Buscando reviews Steam para App ID {appid}...")

    reviews: list[dict[str, Any]] = []
    cursor = "*"

    while len(reviews) < max_reviews:
        params = {
            "json": 1,
            "filter": "recent",
            "language": "all",
            "day_range": 30,
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": min(20, max_reviews - len(reviews)),
            "cursor": cursor,
        }

        response = requests.get(
            f"{STEAM_REVIEWS_BASE_URL}/{appid}",
            params=params,
            timeout=30,
            headers={
                "User-Agent": "oraculo-hype/0.1 educational portfolio project",
            },
        )

        print(f"Status Steam App {appid}: {response.status_code}")

        response.raise_for_status()

        payload = response.json()
        batch = payload.get("reviews", [])

        if not batch:
            break

        reviews.extend(batch)

        new_cursor = payload.get("cursor")

        if not new_cursor or new_cursor == cursor:
            break

        cursor = new_cursor

        time.sleep(1)

    print(f"Reviews coletadas para {appid}: {len(reviews)}")

    return reviews


def timestamp_to_iso(timestamp: int | None) -> str | None:
    if not timestamp:
        return None

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def build_mention_payload(
    review: dict[str, Any],
    title_id: str,
    source_id: str,
    steam_appid: int,
) -> dict[str, Any]:
    recommendation_id = str(review.get("recommendationid"))

    voted_up = bool(review.get("voted_up"))
    sentiment_prefix = "[STEAM_POSITIVE]" if voted_up else "[STEAM_NEGATIVE]"

    review_text = review.get("review") or ""

    if not review_text.strip():
        review_text = "Review sem texto."

    weighted_vote_score = review.get("weighted_vote_score") or "0"
    votes_up = review.get("votes_up") or 0

    content = (
        f"{sentiment_prefix}\n"
        f"{review_text.strip()}\n\n"
        f"Steam App ID: {steam_appid}\n"
        f"Votos úteis: {votes_up}\n"
        f"Peso do voto: {weighted_vote_score}"
    )

    return {
        "title_id": title_id,
        "source_id": source_id,
        "external_id": f"steam_review_{recommendation_id}",
        "author": "Steam User",
        "content": content[:5000],
        "url": f"https://steamcommunity.com/app/{steam_appid}/reviews/",
        "upvotes": int(votes_up),
        "published_at": timestamp_to_iso(review.get("timestamp_created")),
    }


def save_mention(payload: dict[str, Any]) -> bool:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/mentions"

    params = {
        "on_conflict": "external_id,source_id",
    }

    response = requests.post(
        endpoint,
        params=params,
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao salvar menção.")
        print(response.status_code)
        print(response.text)
        return False

    return True


def collect_reviews_for_title(
    source_id: str,
    title: dict[str, Any],
    max_reviews: int = MAX_REVIEWS_PER_GAME,
) -> int:
    steam_appid = title.get("steam_appid")

    if not steam_appid:
        return 0

    reviews = fetch_steam_reviews(
        appid=int(steam_appid),
        max_reviews=max_reviews,
    )

    saved_count = 0

    for review in reviews:
        payload = build_mention_payload(
            review=review,
            title_id=title["id"],
            source_id=source_id,
            steam_appid=int(steam_appid),
        )

        saved = save_mention(payload)

        if saved:
            saved_count += 1

    print(f"Total salvo para {title['name']}: {saved_count}")

    return saved_count


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    source_id = ensure_steam_source()

    titles = fetch_titles_with_steam_appid()

    print(f"Títulos com Steam App ID encontrados: {len(titles)}")

    total_saved = 0

    for title in titles:
        print("\n------------------------------")
        print(f"Coletando reviews para: {title['name']}")

        try:
            total_saved += collect_reviews_for_title(
                source_id=source_id,
                title=title,
                max_reviews=MAX_REVIEWS_PER_GAME,
            )
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {title['name']}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {title['name']}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {title['name']}: {error}")

        time.sleep(1)

    print("\n------------------------------")
    print(f"Coleta finalizada. Menções salvas: {total_saved}")


if __name__ == "__main__":
    main()