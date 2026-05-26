import os
import re
import sys
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

print("Script iniciado: seed_games_rawg.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/seed_games_rawg.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RAWG_API_KEY = os.getenv("RAWG_API_KEY")

RAWG_BASE_URL = "https://api.rawg.io/api"

CURATED_GAMES_TO_IMPORT = [
    "Resident Evil Requiem",
    "Civilization VII",
    "Monster Hunter Wilds",
    "Death Stranding 2",
    "Kingdom Come Deliverance II",
    "Doom The Dark Ages",
    "Grand Theft Auto VI",
    "Metroid Prime 4",
    "Fable",
]

AUTO_DISCOVERY_PAGE_SIZE = 20
MAX_AUTO_DISCOVERED_GAMES = 20


def validate_env() -> None:
    print("Validando variáveis de ambiente...")

    missing_vars = []

    if not SUPABASE_URL:
        missing_vars.append("SUPABASE_URL")

    if not SUPABASE_SERVICE_ROLE_KEY:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")

    if not RAWG_API_KEY:
        missing_vars.append("RAWG_API_KEY")

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


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value)

    return value


def normalize_release_date(raw_date: str | None) -> str | None:
    if not raw_date:
        return None

    try:
        date.fromisoformat(raw_date)
        return raw_date
    except ValueError:
        return None


def get_franchise_guess(game_name: str) -> str | None:
    franchise_map = {
        "Resident Evil Requiem": "Resident Evil",
        "Resident Evil 9: Requiem": "Resident Evil",
        "Civilization VII": "Civilization",
        "Sid Meier’s Civilization VII": "Civilization",
        "Monster Hunter Wilds": "Monster Hunter",
        "Death Stranding 2": "Death Stranding",
        "Death Stranding 2: On The Beach": "Death Stranding",
        "Kingdom Come Deliverance II": "Kingdom Come",
        "Kingdom Come: Deliverance II": "Kingdom Come",
        "Doom The Dark Ages": "Doom",
        "Doom: The Dark Ages": "Doom",
        "Grand Theft Auto VI": "Grand Theft Auto",
        "Metroid Prime 4": "Metroid",
        "Fable": "Fable",
    }

    return franchise_map.get(game_name)


def extract_steam_appid_from_url(url: str | None) -> int | None:
    if not url:
        return None

    match = re.search(r"store\.steampowered\.com/app/(\d+)", url)

    if not match:
        return None

    return int(match.group(1))


def extract_steam_appid_from_details(details: dict[str, Any]) -> int | None:
    stores = details.get("stores") or []

    for store_item in stores:
        store = store_item.get("store") or {}
        store_id = store.get("id")
        url = store_item.get("url")

        if store_id == 1:
            steam_appid = extract_steam_appid_from_url(url)

            if steam_appid:
                return steam_appid

    return None


def get_rawg_game_by_name(game_name: str) -> dict[str, Any] | None:
    if not RAWG_API_KEY:
        raise RuntimeError("RAWG_API_KEY não configurada.")

    params = {
        "key": RAWG_API_KEY,
        "search": game_name,
        "page_size": 5,
        "search_precise": "true",
    }

    print(f"Chamando RAWG por busca direta: {game_name}")

    response = requests.get(
        f"{RAWG_BASE_URL}/games",
        params=params,
        timeout=30,
    )

    print(f"Status RAWG para {game_name}: {response.status_code}")

    response.raise_for_status()

    payload = response.json()
    results = payload.get("results", [])

    if not results:
        print(f"Nenhum resultado encontrado para: {game_name}")
        return None

    return choose_best_search_result(game_name, results)


def choose_best_search_result(
    original_name: str,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_original = normalize_name(original_name)

    def score_result(game: dict[str, Any]) -> tuple[int, float]:
        raw_name = game.get("name") or ""
        normalized_name = normalize_name(raw_name)
        rating = float(game.get("rating") or 0)

        exact_score = 0

        if normalized_name == normalized_original:
            exact_score += 100

        if normalized_original in normalized_name:
            exact_score += 50

        if normalized_name in normalized_original:
            exact_score += 25

        if "2001" in normalized_name:
            exact_score -= 100

        return exact_score, rating

    sorted_results = sorted(results, key=score_result, reverse=True)

    return sorted_results[0]


def normalize_name(value: str) -> str:
    value = value.lower()
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9\s]", "", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def get_rawg_game_details(rawg_id: int) -> dict[str, Any]:
    if not RAWG_API_KEY:
        raise RuntimeError("RAWG_API_KEY não configurada.")

    response = requests.get(
        f"{RAWG_BASE_URL}/games/{rawg_id}",
        params={"key": RAWG_API_KEY},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def discover_games_from_rawg() -> list[dict[str, Any]]:
    if not RAWG_API_KEY:
        raise RuntimeError("RAWG_API_KEY não configurada.")

    today = date.today()
    start_date = today - timedelta(days=60)
    end_date = today + timedelta(days=365)

    params = {
        "key": RAWG_API_KEY,
        "dates": f"{start_date.isoformat()},{end_date.isoformat()}",
        "ordering": "-added",
        "page_size": AUTO_DISCOVERY_PAGE_SIZE,
        "platforms": "4",
        "stores": "1",
    }

    print("Buscando jogos automaticamente na RAWG...")
    print(f"Janela: {start_date.isoformat()} até {end_date.isoformat()}")

    response = requests.get(
        f"{RAWG_BASE_URL}/games",
        params=params,
        timeout=30,
    )

    print(f"Status RAWG descoberta automática: {response.status_code}")

    response.raise_for_status()

    payload = response.json()
    results = payload.get("results", [])

    return results[:MAX_AUTO_DISCOVERED_GAMES]


def build_title_payload(
    rawg_game: dict[str, Any],
    details: dict[str, Any] | None = None,
    original_search_name: str | None = None,
) -> dict[str, Any]:
    rawg_name = rawg_game.get("name") or original_search_name or "Título sem nome"
    rawg_id = rawg_game.get("id")

    steam_appid = None

    if details:
        steam_appid = extract_steam_appid_from_details(details)

    return {
        "rawg_id": rawg_id,
        "name": rawg_name,
        "slug": rawg_game.get("slug") or slugify(rawg_name),
        "media_type": "game",
        "franchise": get_franchise_guess(original_search_name or rawg_name),
        "release_date": normalize_release_date(rawg_game.get("released")),
        "cover_url": rawg_game.get("background_image"),
        "status": "monitoring",
        "rawg_rating": rawg_game.get("rating"),
        "rawg_rating_top": rawg_game.get("rating_top"),
        "rawg_metacritic": rawg_game.get("metacritic"),
        "steam_appid": steam_appid,
        "data_origin": "rawg",
        "last_synced_at": "now()",
    }


def normalize_payload_for_supabase(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    if normalized.get("last_synced_at") == "now()":
        normalized["last_synced_at"] = None

    return normalized


def upsert_title_to_supabase(title_payload: dict[str, Any]) -> bool:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase não configurado corretamente.")

    rawg_id = title_payload.get("rawg_id")
    name = title_payload.get("name")

    if rawg_id is None:
        print(f"Ignorando título sem rawg_id: {name}")
        return False

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "on_conflict": "rawg_id",
    }

    headers = supabase_headers()

    payload = normalize_payload_for_supabase(title_payload)

    print(f"Salvando no Supabase: {name}")

    response = requests.post(
        endpoint,
        params=params,
        headers=headers,
        json=payload,
        timeout=30,
    )

    print(f"Status Supabase para {name}: {response.status_code}")

    if response.status_code not in [200, 201]:
        print("Erro ao salvar no Supabase.")
        print("Resposta:")
        print(response.text)
        response.raise_for_status()

    print(f"Salvo/atualizado com sucesso: {name}")

    return True


def update_last_synced_at(rawg_id: int) -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "rawg_id": f"eq.{rawg_id}",
    }

    payload = {
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
        print("Aviso: não foi possível atualizar last_synced_at.")
        print(response.status_code)
        print(response.text)


def import_curated_games() -> int:
    imported_count = 0

    for game_name in CURATED_GAMES_TO_IMPORT:
        try:
            print("\n------------------------------")
            print(f"Buscando jogo curado: {game_name}")

            rawg_game = get_rawg_game_by_name(game_name)

            if not rawg_game:
                continue

            rawg_id = rawg_game.get("id")

            if not rawg_id:
                continue

            details = get_rawg_game_details(rawg_id)

            title_payload = build_title_payload(
                rawg_game=rawg_game,
                details=details,
                original_search_name=game_name,
            )

            saved = upsert_title_to_supabase(title_payload)

            if saved:
                update_last_synced_at(rawg_id)
                imported_count += 1

        except requests.HTTPError as error:
            print(f"Erro HTTP ao buscar {game_name}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao buscar {game_name}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {game_name}: {error}")

    return imported_count


def import_discovered_games() -> int:
    imported_count = 0

    try:
        discovered_games = discover_games_from_rawg()
    except Exception as error:
        print(f"Erro ao descobrir jogos automaticamente: {error}")
        return 0

    for rawg_game in discovered_games:
        try:
            print("\n------------------------------")
            print(f"Processando jogo descoberto: {rawg_game.get('name')}")

            rawg_id = rawg_game.get("id")

            if not rawg_id:
                continue

            details = get_rawg_game_details(rawg_id)

            title_payload = build_title_payload(
                rawg_game=rawg_game,
                details=details,
                original_search_name=rawg_game.get("name"),
            )

            saved = upsert_title_to_supabase(title_payload)

            if saved:
                update_last_synced_at(rawg_id)
                imported_count += 1

        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar jogo descoberto: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar jogo descoberto: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar jogo descoberto: {error}")

    return imported_count


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    print("Iniciando importação de jogos via RAWG...")

    curated_count = import_curated_games()
    discovered_count = import_discovered_games()

    print("\n------------------------------")
    print("Importação finalizada.")
    print(f"Títulos curados processados: {curated_count}")
    print(f"Títulos descobertos automaticamente: {discovered_count}")


if __name__ == "__main__":
    main()