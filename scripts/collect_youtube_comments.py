import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

print("Script iniciado: collect_youtube_comments.py")

try:
    import requests
    from dotenv import load_dotenv
except ImportError as error:
    print("Erro ao importar dependências.")
    print("Detalhe:", error)
    print(
        "Rode: uv run --with requests --with python-dotenv python scripts/collect_youtube_comments.py"
    )
    sys.exit(1)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"

MAX_VIDEOS_PER_RUN = 20
MAX_COMMENTS_PER_VIDEO = 25


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


def supabase_headers(prefer: str = "return=representation") -> dict[str, str]:
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY não configurada.")

    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def ensure_youtube_comments_source() -> str:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/sources"

    payload = {
        "name": "YouTube Comments",
        "source_type": "community",
        "base_url": "https://www.youtube.com",
    }

    response = requests.post(
        endpoint,
        params={"on_conflict": "name"},
        headers=supabase_headers("resolution=merge-duplicates,return=representation"),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Aviso: não foi possível criar/atualizar a fonte YouTube Comments.")
        print(response.status_code)
        print(response.text)

    return get_source_id("YouTube Comments")


def get_source_id(source_name: str) -> str:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/sources"

    params = {
        "name": f"eq.{source_name}",
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
        raise RuntimeError(f"Fonte não encontrada: {source_name}")

    return data[0]["id"]


def fetch_youtube_videos_to_scan() -> list[dict[str, Any]]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/dashboard_youtube_metrics"

    params = {
        "select": "id,title_id,title_name,slug,youtube_video_id,video_title,comment_count,view_count",
        "order": "view_count.desc",
        "limit": str(MAX_VIDEOS_PER_RUN),
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=supabase_headers(),
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao buscar vídeos do YouTube no Supabase.")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    return response.json()


def fetch_youtube_comments(video_id: str) -> list[dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY não configurada.")

    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "videoId": video_id,
        "maxResults": MAX_COMMENTS_PER_VIDEO,
        "order": "relevance",
        "textFormat": "plainText",
    }

    print(f"Buscando comentários do vídeo: {video_id}")

    response = requests.get(
        f"{YOUTUBE_BASE_URL}/commentThreads",
        params=params,
        timeout=30,
    )

    print(f"Status YouTube Comments para {video_id}: {response.status_code}")

    if response.status_code == 403:
        print("Comentários indisponíveis ou quota/permissão insuficiente para este vídeo.")
        print(response.text)
        return []

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


def build_comment_mention_payload(
    comment_thread: dict[str, Any],
    title_id: str,
    source_id: str,
    video_id: str,
) -> dict[str, Any] | None:
    snippet = comment_thread.get("snippet") or {}
    top_level_comment = snippet.get("topLevelComment") or {}
    comment_id = top_level_comment.get("id")
    comment_snippet = top_level_comment.get("snippet") or {}

    if not comment_id:
        return None

    text = comment_snippet.get("textDisplay") or comment_snippet.get("textOriginal") or ""

    if not text.strip():
        return None

    author = comment_snippet.get("authorDisplayName") or "YouTube User"
    like_count = int(comment_snippet.get("likeCount") or 0)
    published_at = parse_youtube_datetime(comment_snippet.get("publishedAt"))

    content = (
        "[YOUTUBE_COMMENT]\n"
        f"{text.strip()}\n\n"
        f"YouTube Video ID: {video_id}\n"
        f"Likes no comentário: {like_count}"
    )

    return {
        "title_id": title_id,
        "source_id": source_id,
        "external_id": f"youtube_comment_{comment_id}",
        "author": author[:180],
        "content": content[:5000],
        "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
        "upvotes": like_count,
        "published_at": published_at,
    }


def save_mention(payload: dict[str, Any]) -> bool:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada.")

    endpoint = f"{SUPABASE_URL}/rest/v1/mentions"

    response = requests.post(
        endpoint,
        params={"on_conflict": "external_id,source_id"},
        headers=supabase_headers("resolution=merge-duplicates,return=representation"),
        json=payload,
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        print("Erro ao salvar comentário como menção.")
        print(response.status_code)
        print(response.text)
        return False

    return True


def process_video(video: dict[str, Any], source_id: str) -> int:
    title_id = video.get("title_id")
    video_id = video.get("youtube_video_id")
    title_name = video.get("title_name")

    if not title_id or not video_id:
        return 0

    print(f"Processando comentários de {title_name}: {video_id}")

    comments = fetch_youtube_comments(video_id)

    saved_count = 0

    for comment_thread in comments:
        payload = build_comment_mention_payload(
            comment_thread=comment_thread,
            title_id=title_id,
            source_id=source_id,
            video_id=video_id,
        )

        if not payload:
            continue

        if save_mention(payload):
            saved_count += 1

    print(f"Comentários salvos para {title_name}: {saved_count}")

    return saved_count


def main() -> None:
    print("Entrou na função main().")

    validate_env()

    source_id = ensure_youtube_comments_source()
    videos = fetch_youtube_videos_to_scan()

    print(f"Vídeos encontrados para coletar comentários: {len(videos)}")

    total_saved = 0

    for video in videos:
        print("\n------------------------------")

        try:
            total_saved += process_video(video=video, source_id=source_id)
        except requests.HTTPError as error:
            print(f"Erro HTTP ao processar vídeo {video.get('youtube_video_id')}: {error}")
        except requests.RequestException as error:
            print(f"Erro de conexão ao processar vídeo {video.get('youtube_video_id')}: {error}")
        except Exception as error:
            print(f"Erro inesperado ao processar vídeo {video.get('youtube_video_id')}: {error}")

        time.sleep(1)

    print("\n------------------------------")
    print(f"Coleta de comentários finalizada. Comentários salvos: {total_saved}")


if __name__ == "__main__":
    main()