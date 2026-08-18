#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages_doctor.py — "There isn't a GitHub Pages site here" 원인 찾기

세 곳을 순서대로 찔러보고 어느 단계에서 끊겼는지 알려줍니다.

    ① 리포지토리가 공개 상태로 존재하는가
    ② docs/ 파일이 실제로 push 되었는가
    ③ Pages 가 배포되었는가

사용:
    python3 scripts/pages_doctor.py                 # git remote 에서 자동 인식
    python3 scripts/pages_doctor.py steveoh ig-studio
"""
from __future__ import annotations

import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

G, R, Y, D, B, Z = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context()


def ok(m):   print(f"{G}✓{Z} {m}")
def bad(m):  print(f"{R}✗{Z} {m}")
def warn(m): print(f"{Y}!{Z} {m}")
def dim(m):  print(f"{D}{m}{Z}")


def probe(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            return r.status, r.read(3000).decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return -1, str(e)


def from_git() -> tuple[str, str] | None:
    try:
        url = subprocess.check_output(
            ["git", "-C", ROOT, "remote", "get-url", "origin"],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
    return (m.group(1), m.group(2)) if m else None


def branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL).strip() or "main"
    except Exception:
        return "main"


def main():
    if len(sys.argv) >= 3:
        user, repo = sys.argv[1], sys.argv[2]
    else:
        got = from_git()
        if not got:
            sys.exit("사용법: python3 scripts/pages_doctor.py <GitHub사용자명> <리포이름>")
        user, repo = got

    br = branch()
    print(f"\n{B}진단 대상{Z}  {user}/{repo}  (브랜치 {br})\n")

    repo_url = f"https://github.com/{user}/{repo}"
    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{br}/docs/oauth/index.html"
    pages_url = f"https://{user.lower()}.github.io/{repo}/oauth/"

    # ① 리포지토리
    print(f"{B}① 리포지토리{Z}  {D}{repo_url}{Z}")
    s1, _ = probe(repo_url)
    if s1 == 200:
        ok("공개 상태로 존재합니다")
    elif s1 == 404:
        bad("찾을 수 없습니다")
        dim("  · 사용자명 / 리포 이름 철자를 확인하세요")
        dim("  · 리포가 Private 이면 Pages(무료 플랜)가 동작하지 않습니다")
        dim("    Settings → Danger Zone → Change visibility → Public")
        print()
        return
    else:
        warn(f"응답 {s1}")

    # ② push 여부
    print(f"\n{B}② docs/ 파일 push 여부{Z}  {D}{raw_url}{Z}")
    s2, body = probe(raw_url)
    if s2 == 200 and "URLSearchParams" in body:
        ok("docs/oauth/index.html 이 원격에 있습니다")
    elif s2 == 404:
        bad("원격에 파일이 없습니다 — 아직 push 되지 않았습니다")
        dim("  cd ~/Documents/ig-studio")
        dim("  git add -A && git commit -m 'add docs' && git push -u origin " + br)
        dim(f"\n  브랜치 이름이 {br} 가 맞는지도 확인하세요 (master 라면 Pages 설정도 master 로)")
        print()
        return
    else:
        warn(f"응답 {s2}")

    # ③ Pages
    print(f"\n{B}③ Pages 배포{Z}  {D}{pages_url}{Z}")
    s3, body3 = probe(pages_url)
    if s3 == 200:
        ok("Pages 가 살아 있습니다")
        if "인증 코드" in body3 or "OAUTH" in body3.upper():
            ok("콜백 페이지가 정상 표시됩니다")
            print(f"\n{G}{B}이 주소를 Meta 앱의 리디렉션 URI 로 등록하세요:{Z}")
            print(f"  {B}{pages_url}{Z}\n")
        else:
            warn("응답은 되는데 콜백 페이지가 아닙니다. 경로에 /oauth/ 가 있는지 확인하세요")
    elif s3 == 404:
        bad("Pages 사이트가 없습니다")
        print()
        dim("  파일은 올라갔는데 Pages 가 안 뜬다면 원인은 셋 중 하나입니다:")
        dim("")
        dim("  1) Pages 를 아직 켜지 않았다")
        dim(f"     {repo_url}/settings/pages")
        dim(f"     Source: Deploy from a branch / Branch: {br} / Folder: /docs → Save")
        dim("")
        dim("  2) 폴더를 / (root) 로 잡았다")
        dim("     반드시 /docs 여야 합니다. 바꾸고 Save 하면 재배포됩니다")
        dim("")
        dim("  3) 아직 배포 중이다 (첫 배포는 1~3분)")
        dim(f"     {repo_url}/actions 에서 'pages build and deployment' 확인")
        print()
    else:
        warn(f"응답 {s3}")

    print(f"{D}점검 주소{Z}")
    print(f"  Pages 설정  {repo_url}/settings/pages")
    print(f"  배포 로그    {repo_url}/actions")
    print()


if __name__ == "__main__":
    main()
