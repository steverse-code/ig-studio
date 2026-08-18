#!/usr/bin/env python3
"""
publish.py — 카드뉴스 캐러셀을 Instagram에 발행한다.

Instagram API with Instagram Login (Facebook 페이지 불필요)
  base: https://graph.instagram.com/v24.0

필요한 환경변수
  IG_USER_ID        Instagram 프로페셔널 계정 ID
  IG_ACCESS_TOKEN   장기 액세스 토큰 (60일, refresh_token.py로 자동 갱신)
  IMAGE_BASE_URL    슬라이드 이미지가 공개 서빙되는 베이스 URL
                    예) https://raw.githubusercontent.com/<user>/<repo>/main

사용
  python3 scripts/publish.py              # 큐에서 발행할 차례인 글 1건 발행
  python3 scripts/publish.py --dry-run    # 실제 발행 없이 점검만
  python3 scripts/publish.py --slug 2026-08-17-vo2max   # 특정 글 강제 발행
  python3 scripts/publish.py --slug 2026-08-17-vo2max --reel   # 같은 글을 릴스(mp4)로 발행
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://graph.instagram.com/v24.0"
KST = timezone(timedelta(hours=9))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue.json")

MAX_CAPTION = 2200
MAX_HASHTAGS = 30
MAX_SLIDES = 10          # 인스타 캐러셀 상한
MIN_SLIDES = 2


# ─────────────────────────────────────────────────────────────
def _req(method: str, url: str, data: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url.split('?')[0]} → HTTP {e.code}\n{detail}") from None


def get(path: str, **params) -> dict:
    return _req("GET", f"{API}{path}?{urllib.parse.urlencode(params)}")


def post(path: str, **data) -> dict:
    return _req("POST", f"{API}{path}", data)


# ─────────────────────────────────────────────────────────────
def build_caption(spec: dict) -> str:
    tags = spec.get("hashtags", [])
    if len(tags) > MAX_HASHTAGS:
        raise ValueError(f"해시태그 {len(tags)}개 — 인스타그램 상한은 {MAX_HASHTAGS}개입니다.")
    caption = spec["caption"].rstrip()
    if tags:
        caption += "\n\n" + " ".join(tags)
    if len(caption) > MAX_CAPTION:
        raise ValueError(f"캡션 {len(caption)}자 — 상한 {MAX_CAPTION}자를 넘습니다.")
    return caption


def slide_urls(spec: dict, base: str) -> list[str]:
    n = len(spec["slides"])
    if not (MIN_SLIDES <= n <= MAX_SLIDES):
        raise ValueError(f"슬라이드 {n}장 — 캐러셀은 {MIN_SLIDES}~{MAX_SLIDES}장이어야 합니다.")
    base = base.rstrip("/")
    return [f"{base}/out/{spec['slug']}/{spec['slug']}_{i+1:02d}.jpg" for i in range(n)]


def check_reachable(urls: list[str], expect: tuple[str, ...] | None = ("jpeg", "jpg")) -> None:
    """인스타그램은 공개 URL에서 미디어를 가져간다. 미리 확인.

    GitHub raw는 mp4에 Content-Type을 application/octet-stream으로 내려줘서
    (jpeg와 달리) 타입 검증이 무의미하다 — expect=None이면 200 응답만 확인한다.
    """
    for u in urls:
        req = urllib.request.Request(u, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if expect is None:
                    continue
                ct = r.headers.get("Content-Type", "")
                if not any(e in ct for e in expect):
                    raise RuntimeError(f"{'/'.join(expect)}가 아닙니다 ({ct}): {u}")
        except Exception as e:
            raise RuntimeError(f"미디어에 접근할 수 없습니다: {u}\n  {e}") from None


def wait_ready(container_id: str, token: str, tries: int = 30, delay: int = 5) -> None:
    """컨테이너가 FINISHED 될 때까지 대기."""
    for _ in range(tries):
        st = get(f"/{container_id}", fields="status_code,status", access_token=token)
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"컨테이너 처리 실패: {st}")
        time.sleep(delay)
    raise RuntimeError(f"컨테이너 {container_id} 준비 시간 초과")


# ─────────────────────────────────────────────────────────────
def publish(spec: dict, ig_id: str, token: str, base_url: str, dry: bool = False) -> str | None:
    caption = build_caption(spec)
    urls = slide_urls(spec, base_url)

    print(f"▸ {spec['slug']} · 슬라이드 {len(urls)}장 · 캡션 {len(caption)}자")
    check_reachable(urls)
    print("  이미지 접근 확인 완료")

    if dry:
        print("  [dry-run] 여기서 중단합니다.")
        for u in urls:
            print("   ", u)
        return None

    children = []
    for i, u in enumerate(urls, 1):
        r = post(f"/{ig_id}/media", image_url=u, is_carousel_item="true", access_token=token)
        children.append(r["id"])
        print(f"  슬라이드 {i}/{len(urls)} 업로드 → {r['id']}")

    for cid in children:
        wait_ready(cid, token)

    carousel = post(f"/{ig_id}/media",
                    media_type="CAROUSEL",
                    children=",".join(children),
                    caption=caption,
                    access_token=token)
    print(f"  캐러셀 컨테이너 {carousel['id']}")
    wait_ready(carousel["id"], token)

    published = post(f"/{ig_id}/media_publish", creation_id=carousel["id"], access_token=token)
    media_id = published["id"]

    info = get(f"/{media_id}", fields="permalink,timestamp", access_token=token)
    print(f"✅ 발행 완료 → {info.get('permalink')}")
    return media_id


# ─────────────────────────────────────────────────────────────
def publish_reel(spec: dict, ig_id: str, token: str, base_url: str, dry: bool = False) -> str | None:
    """카드뉴스 슬라이드로 만든 릴스(mp4)를 발행한다."""
    caption = build_caption(spec)
    url = f"{base_url.rstrip('/')}/out/{spec['slug']}/{spec['slug']}_reel.mp4"

    print(f"▸ [릴스] {spec['slug']} · 캡션 {len(caption)}자")
    check_reachable([url], expect=None)
    print("  영상 접근 확인 완료")

    if dry:
        print("  [dry-run] 여기서 중단합니다.")
        print("   ", url)
        return None

    container = post(f"/{ig_id}/media",
                     media_type="REELS",
                     video_url=url,
                     caption=caption,
                     access_token=token)
    print(f"  릴스 컨테이너 {container['id']} — 영상 처리 대기 중")
    wait_ready(container["id"], token, tries=60, delay=10)

    published = post(f"/{ig_id}/media_publish", creation_id=container["id"], access_token=token)
    media_id = published["id"]

    info = get(f"/{media_id}", fields="permalink,timestamp", access_token=token)
    print(f"✅ 릴스 발행 완료 → {info.get('permalink')}")
    return media_id


# ─────────────────────────────────────────────────────────────
def load_queue() -> list[dict]:
    if not os.path.exists(QUEUE):
        return []
    return json.load(open(QUEUE, encoding="utf-8"))


def save_queue(q: list[dict]) -> None:
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def pick_due(q: list[dict], now: datetime) -> dict | None:
    """예정 시각이 지난 pending 중 가장 오래된 1건."""
    due = [e for e in q
           if e.get("status") == "pending"
           and datetime.fromisoformat(e["publish_at"]) <= now]
    return min(due, key=lambda e: e["publish_at"]) if due else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--slug", help="큐를 무시하고 특정 글 발행")
    ap.add_argument("--reel", action="store_true", help="캐러셀 대신 릴스(mp4)로 발행 (--slug 필수)")
    args = ap.parse_args()

    if args.reel and not args.slug:
        sys.exit("--reel 은 --slug 와 함께 사용해야 합니다.")

    ig_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    base = os.environ.get("IMAGE_BASE_URL")
    missing = [k for k, v in
               {"IG_USER_ID": ig_id, "IG_ACCESS_TOKEN": token, "IMAGE_BASE_URL": base}.items()
               if not v]
    if missing and not args.dry_run:
        sys.exit(f"환경변수가 없습니다: {', '.join(missing)}")
    if not base:
        sys.exit("IMAGE_BASE_URL이 필요합니다.")

    q = load_queue()
    now = datetime.now(KST)

    if args.slug:
        entry = next((e for e in q if e["slug"] == args.slug), {"slug": args.slug, "status": "pending"})
    else:
        entry = pick_due(q, now)
        if not entry:
            print("발행할 차례인 글이 없습니다. 종료.")
            return

    spec_path = os.path.join(ROOT, "content", f"{entry['slug']}.json")
    spec = json.load(open(spec_path, encoding="utf-8"))

    if args.reel:
        media_id = publish_reel(spec, ig_id, token, base, dry=args.dry_run)
        if media_id and entry in q:
            entry["reel_status"] = "published"
            entry["reel_media_id"] = media_id
            entry["reel_published_at"] = now.isoformat()
            save_queue(q)
        return

    media_id = publish(spec, ig_id, token, base, dry=args.dry_run)

    if media_id and entry in q:
        entry["status"] = "published"
        entry["media_id"] = media_id
        entry["published_at"] = now.isoformat()
        save_queue(q)


if __name__ == "__main__":
    main()
