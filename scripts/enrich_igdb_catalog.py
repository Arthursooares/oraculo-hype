import os
import re
import sys
import time
from datetime import date, datetime, timezone
from typing import Any

print("Script iniciado: enrich_igdb_catalog.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/enrich_igdb_catalog.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_BASE_URL = "https://api.igdb.com/v4"

MAX_TITLES_PER_RUN = 50


TITLE_ALIASES = {
    "Resident Evil 9: Requiem": [
        "Resident Evil Requiem",
        "Resident Evil 9",
        "RE9",
    ],
    "Grand Theft Auto VI": [
        "GTA VI",
        "GTA 6",
        "Grand Theft Auto 6",
    ],
    "Death Stranding 2: On The Beach": [
        "Death Stranding 2",
        "Death Stranding II",
    ],
    "Doom: The Dark Ages": [
        "DOOM: The Dark Ages",
        "Doom The Dark Ages",
    ],
    "Sid Meier’s Civilization VII": [
        "Civilization VII",
        "Sid Meier's Civilization VII",
        "Civilization 7",
    ],
    "Kingdom Come: Deliverance II": [
        "Kingdom Come Deliverance II",
        "Kingdom Come Deliverance 2",
    ],
    "Hades II": [
        "Hades 2",
    ],
    "Metroid Prime 4": [
        "Metroid Prime 4: Beyond",
        "Metroid Prime 4",
    ],
}


def validate_env() -> None:
    print("Validando variáveis de ambiente...")

    missing_vars = []

    if not SUPABASE_URL:
        missing_vars.append("SUPABASE_URL")

    if not SUPABASE_SERVICE_ROLE_KEY:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")

    if not IGDB_CLIENT_ID:
        missing_vars.append("IGDB_CLIENT_ID")

    if not IGDB_CLIENT_SECRET:
        missing_vars.append("IGDB_CLIENT_SECRET")

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


def get_igdb_access_token() -> str:
    if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
        raise RuntimeError("Credenciais IGDB/Twitch não configuradas.")

    print("Gerando token de acesso IGDB/Twitch...")

    params = {
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    response = requests.post(
        TWITCH_TOKEN_URL,
        params=params,
        timeout=30,
    )

    print(f"Status Twitch OAuth: {response.status_code}")

    if response.status_code not in [200, 201]:
        print(response.text)
        response.raise_for_status()

    payload = response.json()
    access_token = payload.get("access_token")

    if not access_token:
        raise RuntimeError("Token IGDB/Twitch não retornado.")

    return access_token


def igdb_headers(access_token: str) -> dict[str, str]:
    if not IGDB_CLIENT_ID:
        raise RuntimeError("IGDB_CLIENT_ID não configurado.")

    return {
        "Client-ID": IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


def normalize_name(value: str) -> str:
    value = value.lower()
    value = value.replace("’", "'")
    value = value.replace("™", "")
    value = value.replace("®", "")
    value = value.replace(":", " ")
    value = value.replace("-", " ")
    value = re.sub(r"\bvi\b", "6", value)
    value = re.sub(r"\bvii\b", "7", value)
    value = re.sub(r"\bii\b", "2", value)
    value = re.sub(r"\bix\b", "9", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def get_search_terms(title_name: str) -> list[str]:
    terms = [title_name]

    if title_name in TITLE_ALIASES:
        terms.extend(TITLE_ALIASES[title_name])

    normalized = title_name.replace(":", " ").replace("’", "'")

    if normalized not in terms:
        terms.append(normalized)

    without_subtitle = title_name.split(":")[0].strip()

    if without_subtitle and without_subtitle not in terms:
        terms.append(without_subtitle)

    roman_replacements = [
        (" VI", " 6"),
        (" VII", " 7"),
        (" II", " 2"),
        (" IX", " 9"),
    ]

    for old, new in roman_replacements:
        if old in title_name:
            replaced = title_name.replace(old, new)
            if replaced not in terms:
                terms.append(replaced)

    unique_terms = []

    for term in terms:
        cleaned = term.strip()

        if cleaned and cleaned not in unique_terms:
            unique_terms.append(cleaned)

    return unique_terms


def fetch_titles_to_enrich() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "status": "eq.monitoring",
        "media_type": "eq.game",
        "select": (
            "id,name,slug,release_date,rawg_rating,rawg_metacritic,"
            "igdb_id,catalog_confidence"
        ),
        "order": "igdb_id.asc.nullslast",
        "limit": str(MAX_TITLES_PER_RUN),
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao buscar títulos para IGDB.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    return response.json()


def igdb_search_game(
    access_token: str,
    search_term: str,
) -> list[dict[str, Any]]:
    endpoint = f"{IGDB_BASE_URL}/games"

    safe_search_term = search_term.replace('"', '\\"')

    query = f'''
search "{safe_search_term}";
fields
  id,
  name,
  slug,
  summary,
  first_release_date,
  rating,
  total_rating,
  hypes,
  genres.name,
  platforms.name,
  involved_companies.company.name,
  involved_companies.developer,
  involved_companies.publisher,
  cover.url,
  category,
  version_parent,
  parent_game.name;
limit 15;
'''

    response = requests.post(
        endpoint,
        headers=igdb_headers(access_token),
        data=query,
        timeout=30,
    )

    print(f"Status IGDB busca '{search_term}': {response.status_code}")

    if response.status_code not in [200, 201]:
        print(response.text)
        response.raise_for_status()

    return response.json()


def score_igdb_result(title_name: str, candidate: dict[str, Any]) -> int:
    original = normalize_name(title_name)
    candidate_name = normalize_name(candidate.get("name") or "")

    if not candidate_name:
        return -999

    score = 0

    if candidate_name == original:
        score += 120

    if original in candidate_name:
        score += 55

    if candidate_name in original:
        score += 45

    original_words = set(original.split())
    candidate_words = set(candidate_name.split())

    if original_words:
        overlap = len(original_words.intersection(candidate_words))
        score += int((overlap / len(original_words)) * 60)

    title_aliases = get_search_terms(title_name)

    for alias in title_aliases:
        normalized_alias = normalize_name(alias)

        if candidate_name == normalized_alias:
            score += 80

        if normalized_alias in candidate_name:
            score += 35

        if candidate_name in normalized_alias:
            score += 25

    bad_terms = [
        "demo",
        "soundtrack",
        "beta",
        "playtest",
        "dlc",
        "pack",
        "bundle",
        "wallpaper",
        "artbook",
    ]

    for term in bad_terms:
        if term in candidate_name:
            score -= 45

    category = candidate.get("category")

    if category == 0:
        score += 15

    if category in [8, 9]:
        score += 8

    if candidate.get("version_parent"):
        score -= 18

    if candidate.get("parent_game"):
        score -= 8

    if candidate.get("first_release_date"):
        score += 8

    if candidate.get("cover"):
        score += 8

    if candidate.get("summary"):
        score += 5

    return score


def choose_best_igdb_match(
    title: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, int]:
    if not candidates:
        return None, 0

    title_name = title.get("name") or ""

    scored_candidates = sorted(
        candidates,
        key=lambda candidate: score_igdb_result(title_name, candidate),
        reverse=True,
    )

    print("Top resultados IGDB:")

    for candidate in scored_candidates[:5]:
        print(
            f"- {candidate.get('name')} | "
            f"ID {candidate.get('id')} | "
            f"score {score_igdb_result(title_name, candidate)}"
        )

    best_candidate = scored_candidates[0]
    best_score = score_igdb_result(title_name, best_candidate)

    print(
        f"Melhor IGDB: {best_candidate.get('name')} "
        f"| score de matching {best_score}"
    )

    if best_score < 45:
        print("IGDB ignorado por baixa confiança de matching.")
        return None, best_score

    return best_candidate, best_score


def timestamp_to_date(value: int | None) -> str | None:
    if not value:
        return None

    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    except (ValueError, OSError):
        return None


def normalize_cover_url(cover: dict[str, Any] | None) -> str | None:
    if not cover:
        return None

    url = cover.get("url")

    if not url:
        return None

    if url.startswith("//"):
        url = f"https:{url}"

    url = url.replace("t_thumb", "t_cover_big")

    return url


def extract_company_names(
    involved_companies: list[dict[str, Any]] | None,
    company_type: str,
) -> list[str]:
    if not involved_companies:
        return []

    names = []

    for item in involved_companies:
        if not item.get(company_type):
            continue

        company = item.get("company") or {}
        name = company.get("name")

        if name and name not in names:
            names.append(name)

    return names[:8]


def extract_names(items: list[dict[str, Any]] | None) -> list[str]:
    if not items:
        return []

    names = []

    for item in items:
        name = item.get("name")

        if name and name not in names:
            names.append(name)

    return names[:12]


def build_update_payload(
    igdb_game: dict[str, Any],
    match_score: int,
) -> dict[str, Any]:
    catalog_confidence = "igdb_matched"

    if match_score >= 100:
        catalog_confidence = "igdb_high_confidence"
    elif match_score < 65:
        catalog_confidence = "igdb_low_confidence"

    return {
        "igdb_id": igdb_game.get("id"),
        "igdb_rating": igdb_game.get("rating"),
        "igdb_hypes": igdb_game.get("hypes"),
        "igdb_total_rating": igdb_game.get("total_rating"),
        "igdb_first_release_date": timestamp_to_date(
            igdb_game.get("first_release_date")
        ),
        "igdb_genres": extract_names(igdb_game.get("genres")),
        "igdb_platforms": extract_names(igdb_game.get("platforms")),
        "igdb_developers": extract_company_names(
            igdb_game.get("involved_companies"),
            "developer",
        ),
        "igdb_publishers": extract_company_names(
            igdb_game.get("involved_companies"),
            "publisher",
        ),
        "igdb_cover_url": normalize_cover_url(igdb_game.get("cover")),
        "igdb_summary": igdb_game.get("summary"),
        "catalog_confidence": catalog_confidence,
        "last_synced_at": date.today().isoformat(),
    }


def update_title_with_igdb(title_id: str, payload: dict[str, Any]) -> bool:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/titles"

    params = {
        "id": f"eq.{title_id}",
    }

    response = requests.patch(
        endpoint,
        params=params,
        headers=supabase_headers("return=representation"),
        json=payload,
        timeout=30,
    )

    print(f"Status update Supabase IGDB: {response.status_code}")

    if response.status_code not in [200, 204]:
        print("Erro ao atualizar título com IGDB.")
        print(response.status_code)
        print(response.text)
        return False

    return True


def process_title(access_token: str, title: dict[str, Any]) -> bool:
    title_id = title.get("id")
    title_name = title.get("name")

    if not title_id or not title_name:
        return False

    print("\n------------------------------")
    print(f"Enriquecendo IGDB: {title_name}")

    all_candidates = []
    seen_ids = set()

    search_terms = get_search_terms(title_name)

    print(f"Termos de busca: {search_terms}")

    for search_term in search_terms:
        candidates = igdb_search_game(access_token, search_term)

        for candidate in candidates:
            candidate_id = candidate.get("id")

            if candidate_id and candidate_id not in seen_ids:
                seen_ids.add(candidate_id)
                all_candidates.append(candidate)

        time.sleep(0.35)

    print(f"Candidatos IGDB encontrados: {len(all_candidates)}")

    best_match, match_score = choose_best_igdb_match(title, all_candidates)

    if not best_match:
        print(f"Nenhum match IGDB confiável para: {title_name}")
        return False

    payload = build_update_payload(best_match, match_score)

    updated = update_title_with_igdb(title_id, payload)

    if updated:
        print(
            f"IGDB atualizado para {title_name}: "
            f"{best_match.get('name')} / ID {best_match.get('id')}"
        )

    return updated


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    access_token = get_igdb_access_token()
    titles = fetch_titles_to_enrich()

    print(f"Títulos encontrados para enriquecer com IGDB: {len(titles)}")

    updated_count = 0

    for title in titles:
        try:
            if process_title(access_token=access_token, title=title):
                updated_count += 1
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {title.get('name')}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {title.get('name')}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {title.get('name')}: {error}")

        time.sleep(0.8)

    print("\n------------------------------")
    print(f"Enriquecimento IGDB finalizado. Títulos atualizados: {updated_count}")


if __name__ == "__main__":
    main()