#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
connect.py — 인스타그램 계정 연동 (최초 1회, 내 컴퓨터에서 실행)

파이썬 3.8+ 만 있으면 됩니다. 설치할 패키지 없음.

    python3 scripts/connect.py

리디렉션 URI
  Meta는 등록 시 해당 주소에 실제로 접속해 검증합니다.
  따라서 localhost 는 등록할 수 없고, 공개 HTTPS 주소가 필요합니다.
  이 프로젝트는 GitHub Pages 를 씁니다 (docs/oauth/index.html):

      https://<GitHub사용자명>.github.io/<리포이름>/oauth/

  자세한 설정은 CONNECT-GUIDE.md 의 "리디렉션 URI" 섹션 참고.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

AUTH_URL = "https://www.instagram.com/oauth/authorize"
AUTH_URL_ALT = "https://api.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH = "https://graph.instagram.com"
SCOPE = "instagram_business_basic,instagram_business_content_publish"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")

C_OK, C_ERR, C_DIM, C_B, C_0 = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def ok(m):   print(f"{C_OK}✓{C_0} {m}")
def err(m):  print(f"{C_ERR}✗{C_0} {m}")
def dim(m):  print(f"{C_DIM}{m}{C_0}")
def head(m): print(f"\n{C_B}{m}{C_0}")


# ── 저장된 값 ────────────────────────────────────────────────
def load_env() -> dict:
    if not os.path.exists(ENV_PATH):
        return {}
    out = {}
    for line in open(ENV_PATH, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ── HTTP ─────────────────────────────────────────────────────
_CTX = ssl.create_default_context()


def http_get(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=60, context=_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}\n{e.read().decode(errors='replace')}") from None


def http_post(url: str, data: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}\n{e.read().decode(errors='replace')}") from None


# ── localhost 콜백 (리디렉션이 localhost 인 경우에만 사용) ────
_result: dict = {}
_done = threading.Event()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _result.update({k: v[0] for k, v in q.items()})
        body = "<html><body style='font:16px sans-serif;padding:60px;text-align:center'>" \
               + ("연동 승인 완료 — 터미널로 돌아가세요." if "code" in _result else "승인 실패") \
               + "</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())
        _done.set()

    def log_message(self, *a):
        pass


def code_via_server(auth_url: str, port: int) -> str:
    try:
        server = HTTPServer(("localhost", port), Handler)
    except OSError as e:
        sys.exit(f"localhost:{port} 을 열 수 없습니다 ({e})")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\n브라우저에서 승인하세요:\n\n  {auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    print("승인 대기 중...")
    _done.wait(timeout=300)
    server.shutdown()
    if "code" not in _result:
        sys.exit(f"인증 코드를 받지 못했습니다: {_result or '시간 초과'}")
    return _result["code"]


def code_via_paste(auth_url: str) -> str:
    print("\n" + "─" * 68)
    print("1) 아래 주소를 브라우저에서 열고 인스타그램 계정으로 승인하세요.")
    print("   (자동으로 열립니다. 안 열리면 복사해서 붙여넣으세요)\n")
    print(f"   {auth_url}\n")
    print("2) 승인하면 콜백 페이지로 이동하며 인증 코드가 표시됩니다.")
    print("   [코드 복사] 를 누른 뒤 아래에 붙여넣으세요.")
    print("   (페이지 대신 주소창의 전체 URL을 붙여넣어도 됩니다)")
    print("─" * 68)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    raw = input("\n인증 코드: ").strip()
    if not raw:
        sys.exit("입력이 비었습니다.")
    if raw.startswith("http"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        if "code" not in q:
            sys.exit("URL에 code 값이 없습니다.")
        return q["code"][0]
    return raw


# ── 단계 ─────────────────────────────────────────────────────
def exchange(app_id, secret, code, redirect):
    code = code.split("#")[0].strip()          # 인스타그램이 붙이는 #_ 제거
    short = http_post(TOKEN_URL, {
        "client_id": app_id, "client_secret": secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect, "code": code,
    })
    ok("단기 토큰 발급")
    long_ = http_get(f"{GRAPH}/access_token?" + urllib.parse.urlencode({
        "grant_type": "ig_exchange_token",
        "client_secret": secret,
        "access_token": short["access_token"],
    }))
    days = int(long_.get("expires_in", 0)) // 86400
    ok(f"장기 토큰 발급 · 유효기간 {days}일")
    return long_["access_token"]


def verify(token):
    return http_get(f"{GRAPH}/me?" + urllib.parse.urlencode({
        "fields": "user_id,username,account_type,media_count",
        "access_token": token,
    }))


def write_env(**kv):
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("# connect.py 가 생성했습니다. 커밋하지 마세요 (.gitignore 포함).\n")
        for k, v in kv.items():
            f.write(f"{k}={v}\n")
    os.chmod(ENV_PATH, 0o600)
    ok(f".env 저장 완료 → {ENV_PATH}")


def normalize_redirect(uri: str) -> str:
    uri = uri.strip()
    if not re.match(r"^https?://", uri):
        sys.exit(f"리디렉션 URI 형식이 아닙니다: {uri}")
    return uri


def main():
    saved = load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-id", default=saved.get("IG_APP_ID"))
    ap.add_argument("--app-secret", default=saved.get("IG_APP_SECRET"))
    ap.add_argument("--redirect-uri", default=saved.get("IG_REDIRECT_URI"))
    ap.add_argument("--alt-auth", action="store_true", help="api.instagram.com 인증 주소 사용")
    args = ap.parse_args()

    head("인스타그램 계정 연동")
    dim("Meta 개발자 앱 → Instagram → API setup with Instagram login 의 값을 씁니다.")
    dim("Facebook 앱 ID/시크릿이 아니라 Instagram 쪽 값이어야 합니다.\n")

    app_id = args.app_id or input("Instagram 앱 ID       : ").strip()
    secret = args.app_secret or input("Instagram 앱 시크릿    : ").strip()

    if args.redirect_uri:
        redirect = normalize_redirect(args.redirect_uri)
        dim(f"리디렉션 URI          : {redirect}")
    else:
        print("\n리디렉션 URI — Meta 앱에 등록한 값과 한 글자도 다르면 안 됩니다.")
        dim("  예) https://steveoh.github.io/ig-studio/oauth/")
        redirect = normalize_redirect(input("리디렉션 URI          : "))

    if not app_id or not secret:
        sys.exit("앱 ID / 시크릿이 비었습니다.")

    base = AUTH_URL_ALT if args.alt_auth else AUTH_URL
    auth_url = f"{base}?" + urllib.parse.urlencode({
        "client_id": app_id,
        "redirect_uri": redirect,
        "scope": SCOPE,
        "response_type": "code",
    })

    parsed = urllib.parse.urlparse(redirect)
    if parsed.hostname in ("localhost", "127.0.0.1"):
        code = code_via_server(auth_url, parsed.port or 80)
    else:
        code = code_via_paste(auth_url)
    ok("인증 코드 수신")

    try:
        token = exchange(app_id, secret, code, redirect)
        me = verify(token)
    except RuntimeError as e:
        err(str(e))
        dim("\n자주 나오는 원인")
        dim("  · 리디렉션 URI 불일치 — Meta 앱 등록값과 정확히 같아야 합니다 (끝 슬래시 포함)")
        dim("  · Facebook 앱 시크릿을 넣음 — Instagram 앱 시크릿이어야 합니다")
        dim("  · 인증 코드 만료 — 1회용입니다. 처음부터 다시 실행하세요")
        sys.exit(1)

    user_id = me.get("user_id") or me.get("id")
    acct = str(me.get("account_type", "")).upper()
    ok(f"연결 확인 → @{me.get('username')} · {acct} · 게시물 {me.get('media_count')}개")
    if acct not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
        err("프로페셔널 계정이 아닌 것 같습니다. 인스타그램 앱에서 전환 후 다시 실행하세요.")

    write_env(IG_USER_ID=user_id, IG_ACCESS_TOKEN=token,
              IG_APP_ID=app_id, IG_APP_SECRET=secret, IG_REDIRECT_URI=redirect)

    head("GitHub Secrets 에 등록할 값")
    print(f"  IG_USER_ID       = {user_id}")
    print(f"  IG_ACCESS_TOKEN  = {token}")
    head("다음 단계")
    print("  1. Settings → Secrets and variables → Actions 에 위 두 값 등록")
    print("  2. Actions → Render cardnews 실행")
    print("  3. Actions → Publish to Instagram 을 dry_run 으로 리허설")
    print()


if __name__ == "__main__":
    main()
