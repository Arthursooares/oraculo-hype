import os
import re
import sys
import time
from datetime import date
from typing import Any

print("Script iniciado: enrich_steam_appids.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/enrich_steam_appids.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch"

MAX_TITLES_PER_RUN = 50


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
        "Prefer": "return=representation",
    }


def normalize_name(value: str) -> str:
    value = value.lower()
    value = value.replace("’", "'")
    value = value.replace("™", "")
    value = value.replace("®", "")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def remove_common_suffixes(value: str) -> str:
    value = normalize_name(value)

    suffixes = [
        "deluxe edition",
        "standard edition",
        "ultimate edition",
        "complete edition",
        "digital deluxe",
        "game of the year edition",
        "demo",
        "playtest",
        "beta",
    ]

    for suffix in suffixes:
        value = value.replace(suffix, "")

    value = re.sub(r"\s+", " ", value).strip()

    return value


def fetch_titles_without_steam_appid() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/dashboard_titles"

    params = {
        "media_type": "eq.game",
        "status": "eq.monitoring",
        "steam_appid": "is.null",
        "select": "id,name,slug,release_date,rawg_rating,hype_score",
        "order": "hype_score.desc",
        "limit": str(MAX_TITLES_PER_RUN),
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao buscar títulos sem Steam App ID.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    return response.json()


def search_steam_store(title_name: str) -> list[dict[str, Any]]:
    print(f"Buscando Steam App ID para: {title_name}")

    params = {
        "term": title_name,
        "cc": "us",
        "l": "english",
    }

    response = requests.get(
        STEAM_SEARCH_URL,
        params=params,
        timeout=30,
        headers={
            "User-Agent": "oraculo-hype/0.1 educational portfolio project",
        },
    )

    print(f"Status Steam Store Search para {title_name}: {response.status_code}")

    if response.status_code not in [200, 201]:
        print(response.text)
        response.raise_for_status()

    payload = response.json()

    return payload.get("items", [])


def score_steam_result(title_name: str, steam_item: dict[str, Any]) -> int:
    original = remove_common_suffixes(title_name)
    candidate = remove_common_suffixes(steam_item.get("name") or "")

    if not candidate:
        return -999

    score = 0

    if candidate == original:
        score += 100

    if original in candidate:
        score += 50

    if candidate in original:
        score += 35

    original_words = set(original.split())
    candidate_words = set(candidate.split())

    if original_words:
        overlap = len(original_words.intersection(candidate_words))
        score += int((overlap / len(original_words)) * 40)

    item_type = steam_item.get("type")

    if item_type == "app":
        score += 10

    name = candidate.lower()

    bad_terms = [
        "soundtrack",
        "demo",
        "playtest",
        "dlc",
        "bonus",
        "artbook",
        "wallpaper",
        "pack",
        "bundle",
    ]

    for term in bad_terms:
        if term in name:
            score -= 35

    return score


def choose_best_steam_match(
    title: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    title_name = title.get("name") or ""

    if not items:
        return None

    scored_items = sorted(
        items,
        key=lambda item: score_steam_result(title_name, item),
        reverse=True,
    )

    best_item = scored_items[0]
    best_score = score_steam_result(title_name, best_item)

    print(f"Melhor resultado Steam: {best_item.get('name')} | score {best_score}")

    if best_score < 55:
        print("Resultado ignorado por baixa confiança.")
        return None

    appid = best_item.get("id")

    if not appid:
        return None

    return best_item


def update_title_steam_appid(title_id: str, steam_appid: int) -> bool:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "id": f"eq.{title_id}",
    }

    payload = {
        "steam_appid": steam_appid,
        "last_synced_at": date.today().isoformat(),
    }

    response = requests.patch(
        endpoint,
        params=params,
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 204]:
        print("Erro ao atualizar Steam App ID.")
        print(response.status_code)
        print(response.text)
        return False

    return True


def process_title(title: dict[str, Any]) -> bool:
    title_id = title.get("id")
    title_name = title.get("name")

    if not title_id or not title_name:
        return False

    items = search_steam_store(title_name)
    best_match = choose_best_steam_match(title, items)

    if not best_match:
        print(f"Nenhum Steam App ID confiável encontrado para: {title_name}")
        return False

    steam_appid = int(best_match["id"])

    updated = update_title_steam_appid(
        title_id=title_id,
        steam_appid=steam_appid,
    )

    if updated:
        print(
            f"Steam App ID atualizado para {title_name}: "
            f"{steam_appid} / {best_match.get('name')}"
        )

    return updated


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    titles = fetch_titles_without_steam_appid()

    print(f"Títulos sem Steam App ID encontrados: {len(titles)}")

    updated_count = 0

    for title in titles:
        print("\n------------------------------")
        print(f"Processando: {title.get('name')}")

        try:
            if process_title(title):
                updated_count += 1
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {title.get('name')}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {title.get('name')}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {title.get('name')}: {error}")

        time.sleep(1)

    print("\n------------------------------")
    print(f"Enriquecimento finalizado. Títulos atualizados: {updated_count}")


if __name__ == "__main__":
    main()