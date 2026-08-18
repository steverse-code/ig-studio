#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doctor.py — "Invalid redirect_uri" 원인 찾기

Meta에 등록한 값과 스크립트가 보내는 값이 한 글자라도 다르면 이 오류가 납니다.
눈으로는 잘 안 보이는 차이(끝 슬래시, 대소문자, 공백)를 찾아줍니다.

    python3 scripts/doctor.py
"""
from __future__ import annotations

import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")

G, R, Y, D, B, Z = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"


def ok(m):   print(f"{G}✓{Z} {m}")
def bad(m):  print(f"{R}✗{Z} {m}")
def warn(m): print(f"{Y}!{Z} {m}")
def dim(m):  print(f"{D}{m}{Z}")


def reveal(s: str) -> str:
    """보이지 않는 문자를 눈에 보이게 바꾼다."""
    out = []
    for ch in s:
        if ch == " ":
            out.append(f"{R}␣{Z}")
        elif ch in "\t\r\n":
            out.append(f"{R}⏎{Z}")
        else:
            out.append(ch)
    return "".join(out)


def load_env() -> dict:
    if not os.path.exists(ENV_PATH):
        return {}
    d = {}
    for line in open(ENV_PATH, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def check_shape(label: str, uri: str) -> list[str]:
    """형태만 보고 잡히는 문제들"""
    problems = []
    print(f"\n{B}{label}{Z}")
    print(f"  [{reveal(uri)}]   ← 대괄호 안이 실제 값입니다 (길이 {len(uri)})")

    if uri != uri.strip():
        problems.append("앞뒤에 공백이 있습니다")
    if not uri.startswith("https://"):
        problems.append("https:// 로 시작해야 합니다")
    p = urllib.parse.urlparse(uri)
    if p.hostname and p.hostname != p.hostname.lower():
        problems.append(f"호스트에 대문자가 있습니다 → {p.hostname.lower()} 로 통일하세요")
    if p.query or p.fragment:
        problems.append("? 나 # 뒤에 붙은 값이 있으면 안 됩니다")
    if p.path and not p.path.endswith("/"):
        problems.append("끝에 슬래시(/)가 없습니다 — 등록값과 형태를 맞추세요")
    return problems


def check_live(uri: str):
    try:
        req = urllib.request.Request(uri, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
            body = r.read(4000).decode(errors="replace")
            ok(f"페이지 응답 {r.status} — Meta가 접속할 수 있는 주소입니다")
            if "OAUTH" in body.upper() or "인증 코드" in body:
                ok("콜백 페이지가 맞습니다 (docs/oauth/index.html)")
            else:
                warn("응답은 되는데 콜백 페이지가 아닌 것 같습니다. 경로에 /oauth/ 가 빠졌는지 확인하세요")
    except urllib.error.HTTPError as e:
        bad(f"페이지 응답 HTTP {e.code} — Meta도 접속하지 못합니다")
        if e.code == 404:
            dim("  GitHub Pages 배포가 아직 안 끝났거나, Settings→Pages 폴더가 /docs 가 아닙니다")
    except Exception as e:
        bad(f"접속 실패: {e}")


def diff(a: str, b: str):
    if a == b:
        ok("두 값이 완전히 동일합니다")
        return True
    bad("두 값이 다릅니다")
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    print(f"\n  {i+1}번째 글자부터 갈립니다:")
    print(f"    등록값   …{reveal(a[max(0,i-12):i])}{R}{B}{reveal(a[i:i+14]) or '(여기서 끝)'}{Z}")
    print(f"    입력값   …{reveal(b[max(0,i-12):i])}{R}{B}{reveal(b[i:i+14]) or '(여기서 끝)'}{Z}")
    if a.rstrip("/") == b.rstrip("/"):
        print(f"\n  {Y}→ 끝 슬래시(/) 차이뿐입니다. 둘 중 하나로 통일하세요.{Z}")
    elif a.lower() == b.lower():
        print(f"\n  {Y}→ 대소문자 차이뿐입니다. 등록값 쪽으로 맞추세요.{Z}")
    return False


def main():
    env = load_env()
    print(f"\n{B}redirect_uri 진단{Z}")
    dim("Meta 앱 → Instagram → 비즈니스 로그인 설정 → OAuth 리디렉션 URI 에 등록한 값과")
    dim("스크립트에 입력한 값을 비교합니다.\n")

    registered = input("① Meta에 등록한 값을 그대로 붙여넣기 : ").strip("\n")
    default = env.get("IG_REDIRECT_URI", "")
    prompt = f"② 스크립트에 입력한 값{f' (엔터=저장된 값 {default})' if default else ''} : "
    entered = input(prompt).strip("\n") or default

    if not registered or not entered:
        sys.exit("두 값 모두 필요합니다.")

    problems = []
    for label, uri in (("① 등록값", registered), ("② 입력값", entered)):
        for p in check_shape(label, uri):
            problems.append(f"{label}: {p}")

    print(f"\n{B}두 값 비교{Z}")
    same = diff(registered, entered)

    print(f"\n{B}페이지 접속 확인{Z}  {D}{registered}{Z}")
    check_live(registered)

    if problems:
        print(f"\n{B}형태 문제{Z}")
        for p in problems:
            warn(p)

    print(f"\n{B}그래도 안 되면 확인할 것{Z}")
    for line in [
        "Meta에서 값을 넣은 칸이 'OAuth 리디렉션 URI' 가 맞는지",
        "  (Deauthorize callback URL / Data deletion request URL 칸이 아닌지)",
        "Facebook 로그인 제품의 '유효한 OAuth 리디렉션 URI' 에 넣은 건 아닌지",
        "  → Instagram 제품의 '비즈니스 로그인 설정' 안이어야 합니다",
        "입력 후 '변경 내용 저장' 을 눌렀는지 (인증 버튼만 누르면 저장이 안 됩니다)",
        "저장 후 페이지를 새로고침했을 때 값이 그대로 남아 있는지",
    ]:
        dim("  · " + line)

    if same and not problems:
        print(f"\n{G}값 자체는 문제가 없습니다. 위 4가지를 확인해 보세요.{Z}\n")
    else:
        print(f"\n{Y}위에서 표시된 차이를 맞춘 뒤 connect.py 를 다시 실행하세요.{Z}\n")


if __name__ == "__main__":
    main()
