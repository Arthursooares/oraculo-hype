import os
import sys
from datetime import date
from typing import Any

print("Script iniciado: promote_evaluated_titles.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/promote_evaluated_titles.py"
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


def fetch_titles_to_review() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "status": "in.(discovered,monitoring)",
        "media_type": "eq.game",
        "select": (
            "id,name,status,rawg_rating,rawg_metacritic,"
            "steam_appid,igdb_id,release_date"
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


def count_related_rows(table: str, title_id: str) -> int:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/{table}"

    params = {
        "title_id": f"eq.{title_id}",
        "select": "id",
    }

    headers = {
        **supabase_headers(),
        "Prefer": "count=exact",
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    content_range = response.headers.get("content-range", "")

    if "/" in content_range:
        try:
            return int(content_range.split("/")[-1])
        except ValueError:
            pass

    return len(response.json())


def should_promote_title(
    title: dict[str, Any],
    youtube_count: int,
    mention_count: int,
) -> bool:
    rawg_rating = float(title.get("rawg_rating") or 0)
    rawg_metacritic = int(title.get("rawg_metacritic") or 0)

    if title.get("igdb_id"):
        return True

    if title.get("steam_appid"):
        return True

    if youtube_count > 0:
        return True

    if mention_count > 0:
        return True

    if rawg_rating >= 3.5:
        return True

    if rawg_metacritic >= 70:
        return True

    return False


def should_archive_title(
    title: dict[str, Any],
    youtube_count: int,
    mention_count: int,
) -> bool:
    rawg_rating = float(title.get("rawg_rating") or 0)

    if title.get("igdb_id"):
        return False

    if title.get("steam_appid"):
        return False

    if youtube_count > 0:
        return False

    if mention_count > 0:
        return False

    if rawg_rating > 0:
        return False

    return True


def update_title_status(title_id: str, status: str) -> bool:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "id": f"eq.{title_id}",
    }

    payload = {
        "status": status,
        "last_synced_at": date.today().isoformat(),
    }

    response = requests.patch(
        endpoint,
        params=params,
        headers=supabase_headers("return=representation"),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 204]:
        print("Erro ao atualizar status do título.")
        print(response.status_code)
        print(response.text)
        return False

    return True


def process_title(title: dict[str, Any]) -> str:
    title_id = title["id"]
    title_name = title["name"]
    current_status = title["status"]

    youtube_count = count_related_rows("youtube_videos", title_id)
    mention_count = count_related_rows("mentions", title_id)

    print(
        f"{title_name}: status={current_status} | "
        f"youtube={youtube_count} | mentions={mention_count}"
    )

    if should_promote_title(title, youtube_count, mention_count):
        if current_status != "monitoring":
            update_title_status(title_id, "monitoring")
            return "promoted"

        return "already_monitoring"

    if current_status == "discovered" and should_archive_title(
        title,
        youtube_count,
        mention_count,
    ):
        update_title_status(title_id, "archived")
        return "archived"

    if current_status == "monitoring":
        update_title_status(title_id, "discovered")
        return "demoted"

    return "kept_discovered"


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    titles = fetch_titles_to_review()

    print(f"Títulos encontrados para promoção/revisão: {len(titles)}")

    results = {
        "promoted": 0,
        "already_monitoring": 0,
        "archived": 0,
        "demoted": 0,
        "kept_discovered": 0,
    }

    for title in titles:
        try:
            result = process_title(title)
            results[result] += 1
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {title.get('name')}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {title.get('name')}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {title.get('name')}: {error}")

    print("\n------------------------------")
    print("Revisão de status finalizada.")
    print(results)


if __name__ == "__main__":
    main()