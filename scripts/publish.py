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
  python3 scripts/publish.py              # 큐에서 발행할 차례인 글을 전부 발행
  python3 scripts/publish.py --max 1      # 이번 실행에서 1건만 발행
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

# 한 번의 실행에서 발행할 최대 건수.
# 정상 운영은 하루 2건이므로, 이 수를 넘게 밀렸다는 건 파이프라인이 어딘가
# 고장났다는 뜻이다. 그런 상태에서 큐를 통째로 쏟아내면 계정이 스팸으로 보인다.
# 남은 건은 다음 크론(30분 뒤)이 이어서 발행하므로 결국 다 빠진다.
DEFAULT_MAX_PER_RUN = 5
# 연속 발행 사이 간격(초). 캐러셀 1건 자체가 수 분 걸리므로 크게 잡을 필요는 없다.
DEFAULT_DELAY = 30


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
# 릴스 오디오 페이지에 표시될 이름 — 필러별로 한 줄
AUDIO_NAME = {
    "longevity": "롱제비티 — 근거로 뒷받침되는 선택지",
    "aging_news": "노화·의학 뉴스 — 근거로 뒷받침되는 선택지",
    "ai_news": "AI 소식 — 근거로 뒷받침되는 선택지",
    "food": "한국 맛집 — 근거로 뒷받침되는 선택지",
    "success": "성공하는 법 — 근거로 뒷받침되는 선택지",
    "fashion": "패션 트렌드 — 근거로 뒷받침되는 선택지",
    "relationships": "연애심리 — 근거로 뒷받침되는 선택지",
}
# 구 lifestyle 필러 — reel.py 의 배경음 매핑과 맞춘다
AUDIO_NAME["lifestyle"] = AUDIO_NAME["aging_news"]


def reel_audio_name(spec: dict) -> str:
    handle = spec.get("handle", "@your_ground_zero").lstrip("@")
    label = AUDIO_NAME.get(spec.get("pillar", ""), "근거로 뒷받침되는 선택지")
    return f"{label} · {handle}"


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

    # 배경음은 reel.py 가 필러에 맞춰 직접 합성한 오리지널 오디오다.
    # audio_name 은 오리지널 오디오에만 붙일 수 있고 한 번 정하면 못 바꾼다.
    # 이름 붙이기는 부가 기능이므로, 거부당하면 이름 없이 그대로 발행한다 —
    # 무인 실행에서 이것 때문에 발행 자체가 실패하면 안 된다.
    fields = dict(media_type="REELS", video_url=url, caption=caption, access_token=token)
    try:
        container = post(f"/{ig_id}/media", audio_name=reel_audio_name(spec), **fields)
    except RuntimeError as e:
        print(f"  audio_name 거부됨 — 이름 없이 발행합니다: {str(e).splitlines()[0]}")
        container = post(f"/{ig_id}/media", **fields)
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


def due_candidates(q: list[dict], now: datetime) -> list[tuple[str, dict, str]]:
    """예정 시각이 지난 pending 을 전부, 오래된 순으로 돌려준다.

    같은 글의 캐러셀/릴스는 각각 독립된 항목으로 취급한다.
    """
    due: list[tuple[str, dict, str]] = []
    for e in q:
        if (e.get("status") == "pending"
                and datetime.fromisoformat(e["publish_at"]) <= now):
            due.append(("carousel", e, e["publish_at"]))
        if (e.get("reel_status") == "pending"
                and e.get("reel_publish_at")
                and datetime.fromisoformat(e["reel_publish_at"]) <= now):
            due.append(("reel", e, e["reel_publish_at"]))
    due.sort(key=lambda c: c[2])
    return due


def publish_entry(kind: str, entry: dict, q: list[dict], ig_id: str, token: str,
                  base: str, dry: bool) -> None:
    """1건을 발행하고 결과를 큐에 즉시 기록한다.

    save_queue 를 건건이 부르는 게 핵심이다. 여러 건을 도는 중에 러너가 죽어도,
    이미 인스타에 나간 글은 published 로 남아야 다음 실행이 같은 글을 또 올리지
    않는다(2026-08-22 bib-gourmand 중복 발행 참고).
    """
    spec_path = os.path.join(ROOT, "content", f"{entry['slug']}.json")
    spec = json.load(open(spec_path, encoding="utf-8"))

    if kind == "reel":
        media_id = publish_reel(spec, ig_id, token, base, dry=dry)
        if media_id and entry in q:
            entry["reel_status"] = "published"
            entry["reel_media_id"] = media_id
            entry["reel_published_at"] = datetime.now(KST).isoformat()
            entry.pop("error", None)
            save_queue(q)
        return

    media_id = publish(spec, ig_id, token, base, dry=dry)
    if media_id and entry in q:
        entry["status"] = "published"
        entry["media_id"] = media_id
        entry["published_at"] = datetime.now(KST).isoformat()
        entry.pop("error", None)
        save_queue(q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--slug", help="큐를 무시하고 특정 글 발행")
    ap.add_argument("--reel", action="store_true", help="캐러셀 대신 릴스(mp4)로 발행 (--slug 필수)")
    ap.add_argument("--max", type=int, default=DEFAULT_MAX_PER_RUN,
                    help=f"한 실행에서 발행할 최대 건수 (기본 {DEFAULT_MAX_PER_RUN}, 0이면 무제한)")
    ap.add_argument("--delay", type=int, default=DEFAULT_DELAY,
                    help=f"연속 발행 사이 대기 초 (기본 {DEFAULT_DELAY})")
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

    # --slug 는 사람이 특정 글을 콕 집어 올리는 경로다. 큐를 무시하고 1건만.
    if args.slug:
        entry = next((e for e in q if e["slug"] == args.slug),
                     {"slug": args.slug, "status": "pending"})
        publish_entry("reel" if args.reel else "carousel", entry, q,
                      ig_id, token, base, args.dry_run)
        return

    # 자동 모드: 발행할 차례가 된 건을 오래된 순으로 전부 처리한다.
    # 크론이 드롭돼 큐가 밀려도 다음 실행 한 번으로 따라잡히도록.
    candidates = due_candidates(q, now)
    if not candidates:
        print("발행할 차례인 글이 없습니다. 종료.")
        return

    batch = candidates if args.max <= 0 else candidates[:args.max]
    print(f"발행 대기 {len(candidates)}건 — 이번 실행에서 {len(batch)}건 처리")
    if len(batch) < len(candidates):
        skipped = [e["slug"] for _, e, _ in candidates[len(batch):]]
        print(f"⚠️ --max {args.max} 상한으로 {len(skipped)}건은 이번에 건너뜁니다 "
              f"(다음 실행에서 이어서 발행): {', '.join(skipped)}")

    failed: list[str] = []
    for i, (kind, entry, _) in enumerate(batch, 1):
        print(f"\n[{i}/{len(batch)}] {entry['slug']} ({kind})")
        try:
            publish_entry(kind, entry, q, ig_id, token, base, args.dry_run)
        except Exception as e:
            # 1건이 깨져도 나머지는 계속 발행한다. 실패한 건은 pending 으로 남겨
            # 다음 실행이 재시도하되, error 를 남겨 눈에 띄게 한다.
            msg = str(e).splitlines()[0]
            print(f"❌ {entry['slug']} 발행 실패: {msg}", file=sys.stderr)
            failed.append(entry["slug"])
            if entry in q and not args.dry_run:
                entry["error"] = msg
                save_queue(q)
            continue

        if i < len(batch) and args.delay > 0 and not args.dry_run:
            print(f"  다음 발행까지 {args.delay}초 대기")
            time.sleep(args.delay)

    if failed:
        sys.exit(f"발행 실패 {len(failed)}건: {', '.join(failed)}")


if __name__ == "__main__":
    main()
