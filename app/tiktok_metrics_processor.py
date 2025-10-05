# tiktok_metrics_processor.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, parse_qs

LIMA_TZ = ZoneInfo("America/Lima")

@dataclass
class TiktokMetricOut:
    postId: str
    datePosted: str
    hourPosted: str
    usernameTiktokAccount: str
    postURL: str
    views: int
    likes: int
    comments: int
    saves: int
    reposts: int
    totalInteractions: int
    engagement: float
    numberHashtags: int
    hashtags: str
    soundId: str
    soundURL: str
    regionPost: str
    dateTracking: str
    timeTracking: str

def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def _na_if_blank(s: Optional[str]) -> str:
    return s.strip() if isinstance(s, str) and s.strip() else "N/A"



def _parse_dt_optional(create_time_iso: Optional[str], create_time_epoch: Optional[int]) -> Optional[datetime]:
    # Devuelve None si no hay datos de fecha/hora en lugar de “inventar” ahora.
    if create_time_iso:
        try:
            dt = datetime.fromisoformat(create_time_iso.replace("Z", "+00:00"))
            return dt.astimezone(LIMA_TZ)
        except Exception:
            pass
    if create_time_epoch:
        try:
            return datetime.fromtimestamp(int(create_time_epoch), tz=ZoneInfo("UTC")).astimezone(LIMA_TZ)
        except Exception:
            pass
    return None

def _join_hashtags(hashtags: List[Dict[str, Any]]) -> str:
    print(hashtags)
    tags = []
    for h in hashtags or []:
        name = h.get("name")
        if isinstance(name, str) and name.strip():
            if not name.startswith("#"):
                name = "#" + name
            tags.append(name)
    return " ".join(tags) if tags else "N/A"

def transform_item(item: Dict[str, Any], username_fallback: Optional[str] = None) -> TiktokMetricOut:
    # postId
    post_id = _na_if_blank(str(item.get("id", "")))

    # fecha/hora del post (no inventamos si no viene)
    dt = _parse_dt_optional(item.get("createTimeISO"), item.get("createTime"))
    date_posted = dt.strftime("%Y-%m-%d") if dt else "N/A"
    hour_posted = dt.strftime("%H:%M:%S") if dt else "N/A"

    # username
    author_meta = item.get("authorMeta") or {}
    username = author_meta.get("name") or item.get("input") or username_fallback or ""
    username = _na_if_blank(username)

    # url del post
    post_url = _na_if_blank(item.get("webVideoUrl") or "")

    # métricas
    views = _safe_int(item.get("playCount"))
    likes = _safe_int(item.get("diggCount"))
    comments = _safe_int(item.get("commentCount"))
    saves = _safe_int(item.get("collectCount"))
    reposts = _safe_int(item.get("shareCount"))  # usamos shareCount como 'reposts'
    total_interactions = likes + comments + saves + reposts
    engagement = round((total_interactions / views), 6) if views > 0 else 0.0

    # hashtags
    hashtags_list = item.get("hashtags") or []
    number_hashtags = len(hashtags_list)
    print(hashtags_list)
    hashtags = _join_hashtags(hashtags_list)

    # música
    music = item.get("musicMeta") or {}
    sound_id = _na_if_blank(str(music.get("musicId") or ""))
    sound_url = _na_if_blank(str(music.get("playUrl") or ""))

    # región (si no hay 'idc' en ninguna URL -> "N/A")
    candidate_urls: List[str] = [post_url if post_url != "N/A" else ""]
    vm = item.get("videoMeta") or {}
    if vm.get("coverUrl"): candidate_urls.append(vm["coverUrl"])
    if vm.get("originalCoverUrl"): candidate_urls.append(vm["originalCoverUrl"])
    for link in item.get("slideshowImageLinks") or []:
        for k in ("tiktokLink", "downloadLink"):
            if link.get(k): candidate_urls.append(link[k])
    region = "N/A"

    # tracking ahora (esto sí es interno y siempre lo registramos)
    now = datetime.now(tz=LIMA_TZ)

    return TiktokMetricOut(
        postId=post_id,
        datePosted=date_posted,
        hourPosted=hour_posted,
        usernameTiktokAccount=username,
        postURL=post_url,
        views=views,
        likes=likes,
        comments=comments,
        saves=saves,
        reposts=reposts,
        totalInteractions=total_interactions,
        engagement=engagement,
        numberHashtags=number_hashtags,
        hashtags=hashtags,
        soundId=sound_id,
        soundURL=sound_url,
        regionPost=region,
        dateTracking=now.strftime("%Y-%m-%d"),
        timeTracking=now.strftime("%H:%M:%S"),
    )

def transform_items(apify_response: Dict[str, Any], username_fallback: Optional[str] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    items = (apify_response or {}).get("Success") or []
    out: List[Dict[str, Any]] = []
    for item in items:
        model = transform_item(item, username_fallback=username_fallback)
        record = asdict(model)
        # 👇 Agregar userId, con fallback a "N/A" si no viene
        record["userId"] = user_id if user_id is not None else "N/A"
        out.append(record)
    return out
