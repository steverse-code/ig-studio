#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
set_handle.py — 슬라이드 하단의 계정 핸들을 실제 계정명으로 채운다.

.env 의 토큰으로 인스타그램에 내 계정명을 물어본 뒤,
content/*.json 의 handle 값을 바꾸고 슬라이드를 다시 렌더링합니다.

    python3 scripts/set_handle.py              # 계정에서 자동으로 가져오기
    python3 scripts/set_handle.py @my_account  # 직접 지정
"""
from __future__ import annotations

import glob
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

G, R, Y, D, B, Z = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = "https://graph.instagram.com"


def ok(m):   print(f"{G}✓{Z} {m}")
def bad(m):  print(f"{R}✗{Z} {m}")
def dim(m):  print(f"{D}{m}{Z}")


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


def fetch_handle(token: str) -> str:
    url = f"{GRAPH}/me?" + urllib.parse.urlencode(
        {"fields": "username", "access_token": token})
    try:
        with urllib.request.urlopen(url, timeout=30,
                                    context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode())["username"]
    except urllib.error.HTTPError as e:
        bad(f"계정 정보를 가져오지 못했습니다 (HTTP {e.code})")
        dim("  토큰이 만료됐을 수 있습니다. python3 scripts/connect.py 로 재발급하세요.")
        dim("  또는 직접 지정: python3 scripts/set_handle.py @my_account")
        sys.exit(1)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    if len(sys.argv) > 1:
        handle = sys.argv[1].lstrip("@").strip()
        if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", handle):
            bad(f"인스타그램 사용자명 형식이 아닙니다: {sys.argv[1]}")
            dim("  영문/숫자/마침표/밑줄만 가능합니다. 예) python3 scripts/set_handle.py @my_account")
            sys.exit(1)
        ok(f"직접 지정한 핸들: @{handle}")
    else:
        env = load_env()
        token = env.get("IG_ACCESS_TOKEN")
        if not token:
            bad(".env 에 토큰이 없습니다. connect.py 를 먼저 실행하거나 핸들을 직접 넘기세요.")
            dim("  python3 scripts/set_handle.py @my_account")
            sys.exit(1)
        handle = fetch_handle(token)
        ok(f"연결된 계정: @{handle}")

    files = sorted(glob.glob(os.path.join(ROOT, "content", "*.json")))
    if not files:
        bad("content/*.json 이 없습니다.")
        sys.exit(1)

    changed = []
    for path in files:
        spec = json.load(open(path, encoding="utf-8"))
        before = spec.get("handle", "")
        if before == f"@{handle}":
            dim(f"  {os.path.basename(path)} — 이미 @{handle}")
            continue
        spec["handle"] = f"@{handle}"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
            f.write("\n")
        ok(f"  {os.path.basename(path)} — {before or '(없음)'} → @{handle}")
        changed.append((path, spec["slug"]))

    if not changed:
        print(f"\n{G}바꿀 것이 없습니다.{Z}\n")
        return

    print(f"\n{B}슬라이드 다시 렌더링{Z}")
    for path, slug in changed:
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "cardnews.py"),
                        path, os.path.join(ROOT, "out")],
                       check=True, stdout=subprocess.DEVNULL)
        n = len(glob.glob(os.path.join(ROOT, "out", slug, "*.jpg")))
        ok(f"  {slug} — {n}장")

    print(f"\n{B}다음 단계 — GitHub 에 반영{Z}")
    print("  git add -A")
    print(f'  git commit -m "handle: @{handle}"')
    print("  git push")
    print(f"\n{D}push 가 끝난 뒤에 Publish 워크플로를 실행하세요.{Z}")
    print(f"{D}(인스타그램은 GitHub 에 올라간 이미지를 가져갑니다){Z}\n")


if __name__ == "__main__":
    main()
