import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

print("Script iniciado: collect_youtube_trailer_metrics.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/collect_youtube_trailer_metrics.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"

MAX_TITLES_PER_RUN = 15
MAX_VIDEOS_PER_TITLE = 3


def validate_env() -> None:
    print("Validando variáveis de ambiente...")

    missing_vars = []

    if not SUPABASE_URL:
        missing_vars.append("SUPABASE_URL")

    if not SUPABASE_SERVICE_ROLE_KEY:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")

    if not YOUTUBE_API_KEY:
        missing_vars.append("YOUTUBE_API_KEY")

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


def fetch_titles_to_monitor() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/dashboard_titles"

    params = {
        "status": "eq.monitoring",
        "media_type": "eq.game",
        "select": "id,name,slug,release_date,hype_score,mention_volume,rawg_rating,steam_appid",
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
        print("Erro ao buscar títulos no Supabase.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    data = response.json()

    return data


def search_youtube_videos(title_name: str) -> list[str]:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY não configurada.")

    query = f"{title_name} official trailer game"

    print(f"Buscando no YouTube: {query}")

    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": MAX_VIDEOS_PER_TITLE,
        "videoEmbeddable": "true",
        "safeSearch": "none",
        "order": "relevance",
    }

    response = requests.get(
        f"{YOUTUBE_BASE_URL}/search",
        params=params,
        timeout=30,
    )

    print(f"Status YouTube Search para {title_name}: {response.status_code}")

    if response.status_code not in [200, 201]:
        print(response.text)
        response.raise_for_status()

    payload = response.json()
    items = payload.get("items", [])

    video_ids = []

    for item in items:
        video_id = item.get("id", {}).get("videoId")

        if video_id:
            video_ids.append(video_id)

    return video_ids


def fetch_video_details(video_ids: list[str]) -> list[dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY não configurada.")

    if not video_ids:
        return []

    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
    }

    response = requests.get(
        f"{YOUTUBE_BASE_URL}/videos",
        params=params,
        timeout=30,
    )

    print(f"Status YouTube Videos: {response.status_code}")

    if response.status_code not in [200, 201]:
        print(response.text)
        response.raise_for_status()

    payload = response.json()

    return payload.get("items", [])


def parse_youtube_datetime(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def parse_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_youtube_payload(title_id: str, video: dict[str, Any]) -> dict[str, Any]:
    video_id = video.get("id")
    snippet = video.get("snippet") or {}
    statistics = video.get("statistics") or {}
    thumbnails = snippet.get("thumbnails") or {}

    thumbnail_url = None

    for thumbnail_key in ["maxres", "standard", "high", "medium", "default"]:
        thumbnail = thumbnails.get(thumbnail_key)

        if thumbnail and thumbnail.get("url"):
            thumbnail_url = thumbnail.get("url")
            break

    return {
        "title_id": title_id,
        "youtube_video_id": video_id,
        "video_title": snippet.get("title") or "Vídeo sem título",
        "channel_title": snippet.get("channelTitle"),
        "published_at": parse_youtube_datetime(snippet.get("publishedAt")),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": thumbnail_url,
        "view_count": parse_int(statistics.get("viewCount")),
        "like_count": parse_int(statistics.get("likeCount")),
        "comment_count": parse_int(statistics.get("commentCount")),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def save_youtube_video(payload: dict[str, Any]) -> bool:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/youtube_videos"

    params = {
        "on_conflict": "title_id,youtube_video_id",
    }

    response = requests.post(
        endpoint,
        params=params,
        headers=supabase_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao salvar vídeo do YouTube.")
        print(response.status_code)
        print(response.text)
        return False

    return True


def process_title(title: dict[str, Any]) -> int:
    title_id = title.get("id")
    title_name = title.get("name")

    if not title_id or not title_name:
        return 0

    video_ids = search_youtube_videos(title_name)

    if not video_ids:
        print(f"Nenhum vídeo encontrado para: {title_name}")
        return 0

    videos = fetch_video_details(video_ids)

    saved_count = 0

    for video in videos:
        payload = build_youtube_payload(title_id=title_id, video=video)
        saved = save_youtube_video(payload)

        if saved:
            saved_count += 1

    print(f"Vídeos salvos para {title_name}: {saved_count}")

    return saved_count


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    titles = fetch_titles_to_monitor()

    print(f"Títulos encontrados para YouTube: {len(titles)}")

    total_saved = 0

    for title in titles:
        print("\n------------------------------")
        print(f"Processando YouTube para: {title.get('name')}")

        try:
            total_saved += process_title(title)
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar {title.get('name')}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar {title.get('name')}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar {title.get('name')}: {error}")

        time.sleep(1)

    print("\n------------------------------")
    print(f"Coleta YouTube finalizada. Vídeos salvos: {total_saved}")


if __name__ == "__main__":
    main()