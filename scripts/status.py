#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
status.py — 지금 어디까지 됐는지 한 번에 확인

    python3 scripts/status.py

토큰이 살아 있는지, 이미지가 공개되어 있는지, 발행 준비가 됐는지를
실제로 찔러보고 남은 할 일을 알려줍니다. 아무것도 발행하지 않습니다.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

G, R, Y, D, B, Z = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = "https://graph.instagram.com"
CTX = ssl.create_default_context()
KST = timezone(timedelta(hours=9))

todo: list[str] = []


def ok(m):   print(f"{G}✓{Z} {m}")
def bad(m):  print(f"{R}✗{Z} {m}")
def warn(m): print(f"{Y}!{Z} {m}")
def dim(m):  print(f"{D}{m}{Z}")
def head(m): print(f"\n{B}{m}{Z}")


def load_env() -> dict:
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        return {}
    d = {}
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def probe(url, head_only=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"},
                                 method="HEAD" if head_only else "GET")
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            return r.status, (b"" if head_only else r.read(2000)).decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return -1, str(e)


def repo_info():
    try:
        url = subprocess.check_output(["git", "-C", ROOT, "remote", "get-url", "origin"],
                                      text=True, stderr=subprocess.DEVNULL).strip()
        br = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
                                     text=True, stderr=subprocess.DEVNULL).strip()
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        return (m.group(1), m.group(2), br or "main") if m else None
    except Exception:
        return None


# ── 1. 연동 ──────────────────────────────────────────────────
def check_link(env) -> bool:
    head("1. 인스타그램 연동")
    if not env.get("IG_ACCESS_TOKEN"):
        bad(".env 가 없거나 토큰이 없습니다 — 아직 연동되지 않았습니다")
        todo.append("python3 scripts/connect.py 실행")
        return False

    st, body = probe(f"{GRAPH}/me?" + urllib.parse.urlencode({
        "fields": "user_id,username,account_type,media_count",
        "access_token": env["IG_ACCESS_TOKEN"],
    }))
    if st != 200:
        bad(f"토큰이 유효하지 않습니다 (HTTP {st})")
        dim("  만료되었을 수 있습니다. python3 scripts/connect.py 로 다시 발급하세요")
        todo.append("토큰 재발급 (connect.py)")
        return False

    me = json.loads(body)
    ok(f"연결됨 → @{me.get('username')} · {me.get('account_type')} · 게시물 {me.get('media_count')}개")
    if str(me.get("account_type", "")).upper() not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
        warn("프로페셔널 계정이 아닙니다 — 발행이 거부될 수 있습니다")
    return True


# ── 2. 이미지 공개 ───────────────────────────────────────────
def check_images(info) -> bool:
    head("2. 슬라이드 이미지 공개 여부")
    if not info:
        warn("git remote 를 읽을 수 없습니다")
        return False
    user, repo, br = info
    base = f"https://raw.githubusercontent.com/{user}/{repo}/{br}"

    try:
        queue = json.load(open(os.path.join(ROOT, "queue.json"), encoding="utf-8"))
    except Exception:
        bad("queue.json 을 읽을 수 없습니다")
        return False

    pending = [e for e in queue if e.get("status") == "pending"]
    if not pending:
        warn("대기 중인 글이 없습니다")
        return True

    all_ok = True
    for e in pending[:2]:
        slug = e["slug"]
        spec_path = os.path.join(ROOT, "content", f"{slug}.json")
        if not os.path.exists(spec_path):
            bad(f"{slug}: content/{slug}.json 이 없습니다")
            all_ok = False
            continue
        n = len(json.load(open(spec_path, encoding="utf-8"))["slides"])
        first = f"{base}/out/{slug}/{slug}_01.jpg"
        st, _ = probe(first, head_only=True)
        if st == 200:
            ok(f"{slug}: 슬라이드 {n}장 공개 확인")
        elif st == 404:
            bad(f"{slug}: 이미지에 접근할 수 없습니다 (404)")
            dim(f"  {first}")
            dim("  리포가 Private 이거나, Render 워크플로가 아직 안 돌았습니다")
            todo.append("Actions → Render cardnews 실행")
            all_ok = False
        else:
            warn(f"{slug}: 응답 {st}")
            all_ok = False
    return all_ok


# ── 3. 콜백 페이지 ───────────────────────────────────────────
def check_pages(env):
    head("3. OAuth 콜백 페이지")
    uri = env.get("IG_REDIRECT_URI")
    if not uri:
        dim("  등록된 리디렉션 URI 정보가 없습니다 (연동 후에는 불필요)")
        return
    st, _ = probe(uri)
    if st == 200:
        ok(f"살아 있음 → {uri}")
    else:
        warn(f"응답 {st} → {uri}")
        dim("  이미 연동이 끝났다면 문제되지 않습니다 (재연동 시에만 필요)")


# ── 4. 발행 큐 ───────────────────────────────────────────────
def check_queue():
    head("4. 발행 큐")
    try:
        queue = json.load(open(os.path.join(ROOT, "queue.json"), encoding="utf-8"))
    except Exception:
        bad("queue.json 을 읽을 수 없습니다")
        return
    now = datetime.now(KST)
    for e in queue:
        when = datetime.fromisoformat(e["publish_at"])
        mark = "발행됨" if e.get("status") == "published" else \
               ("발행 대기(시각 도래)" if when <= now else "예약")
        line = f"  {e['slug']}  ·  {when.strftime('%Y-%m-%d %H:%M')}  ·  {mark}"
        print(f"{G}{line}{Z}" if e.get("status") == "published" else line)
    if not any(e.get("status") == "published" for e in queue):
        todo.append("Actions → Publish to Instagram (먼저 dry_run 으로 리허설)")


# ── main ─────────────────────────────────────────────────────
def main():
    env = load_env()
    info = repo_info()
    print(f"\n{B}ig-studio 상태 점검{Z}")
    if info:
        dim(f"리포지토리  {info[0]}/{info[1]} ({info[2]})")

    linked = check_link(env)
    check_images(info)
    check_pages(env)
    check_queue()

    head("남은 할 일")
    if not todo:
        print(f"{G}  없습니다. 예약 시각이 되면 자동으로 발행됩니다.{Z}")
    else:
        for i, t in enumerate(todo, 1):
            print(f"  {i}. {t}")
        dim("\n  GitHub Secrets(IG_USER_ID, IG_ACCESS_TOKEN) 등록과")
        dim("  Actions 쓰기 권한은 여기서 확인할 수 없습니다. 웹에서 직접 확인하세요.")
        if info:
            dim(f"    https://github.com/{info[0]}/{info[1]}/settings/secrets/actions")
            dim(f"    https://github.com/{info[0]}/{info[1]}/settings/actions")
    print()


if __name__ == "__main__":
    main()
