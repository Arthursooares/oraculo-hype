import os
import re
import sys
from datetime import date
from typing import Any

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


GAMES_TO_IMPORT = [
    "Resident Evil Requiem",
    "Civilization VII",
    "Monster Hunter Wilds",
    "Death Stranding 2",
    "Hades II",
    "Kingdom Come Deliverance II",
    "Doom The Dark Ages",
    "Grand Theft Auto VI",
    "Metroid Prime 4",
    "Fable",
]


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
        print("Erro: variáveis ausentes no arquivo .env:")

        for var in missing_vars:
            print(f"- {var}")

        print("\nO arquivo .env precisa estar na raiz do projeto, no mesmo nível de package.json.")
        sys.exit(1)

    print("Variáveis de ambiente encontradas.")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value)

    return value


def get_rawg_game_by_name(game_name: str) -> dict[str, Any] | None:
    if not RAWG_API_KEY:
        raise RuntimeError("RAWG_API_KEY não configurada.")

    params = {
        "key": RAWG_API_KEY,
        "search": game_name,
        "page_size": 1,
        "search_precise": "true",
    }

    print(f"Chamando RAWG para: {game_name}")

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

    return results[0]


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
        "Civilization VII": "Civilization",
        "Monster Hunter Wilds": "Monster Hunter",
        "Death Stranding 2": "Death Stranding",
        "Hades II": "Hades",
        "Kingdom Come Deliverance II": "Kingdom Come",
        "Doom The Dark Ages": "Doom",
        "Grand Theft Auto VI": "Grand Theft Auto",
        "Metroid Prime 4": "Metroid",
        "Fable": "Fable",
    }

    return franchise_map.get(game_name)


def build_title_payload(
    rawg_game: dict[str, Any],
    original_search_name: str,
) -> dict[str, Any]:
    rawg_name = rawg_game.get("name") or original_search_name

    return {
        "rawg_id": rawg_game.get("id"),
        "name": rawg_name,
        "slug": rawg_game.get("slug") or slugify(rawg_name),
        "media_type": "game",
        "franchise": get_franchise_guess(original_search_name),
        "release_date": normalize_release_date(rawg_game.get("released")),
        "cover_url": rawg_game.get("background_image"),
        "status": "monitoring",
        "rawg_rating": rawg_game.get("rating"),
        "rawg_rating_top": rawg_game.get("rating_top"),
        "rawg_metacritic": rawg_game.get("metacritic"),
        "data_origin": "rawg",
    }


def upsert_title_to_supabase(title_payload: dict[str, Any]) -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase não configurado corretamente.")

    rawg_id = title_payload.get("rawg_id")
    name = title_payload.get("name")

    if rawg_id is None:
        print(f"Ignorando título sem rawg_id: {name}")
        return

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "on_conflict": "rawg_id",
    }

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    print(f"Salvando no Supabase: {name}")

    response = requests.post(
        endpoint,
        params=params,
        headers=headers,
        json=title_payload,
        timeout=30,
    )

    print(f"Status Supabase para {name}: {response.status_code}")

    if response.status_code not in [200, 201]:
        print("Erro ao salvar no Supabase.")
        print("Resposta:")
        print(response.text)
        response.raise_for_status()

    saved_data = response.json()

    if saved_data:
        print(f"Salvo/atualizado com sucesso: {name}")
    else:
        print(f"Processado, mas sem retorno de dados: {name}")


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    print("Iniciando importação de jogos reais via RAWG...")

    imported_count = 0

    for game_name in GAMES_TO_IMPORT:
        try:
            print("\n------------------------------")
            print(f"Buscando jogo: {game_name}")

            rawg_game = get_rawg_game_by_name(game_name)

            if not rawg_game:
                continue

            title_payload = build_title_payload(rawg_game, game_name)

            print("Payload montado:")
            print(title_payload)

            upsert_title_to_supabase(title_payload)

            imported_count += 1

        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {game_name}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {game_name}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {game_name}: {error}")

    print("\n------------------------------")
    print(f"Importação finalizada. Títulos processados: {imported_count}")


if __name__ == "__main__":
    main()