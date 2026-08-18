#!/usr/bin/env python3
"""
refresh_token.py — Instagram 장기 액세스 토큰(60일)을 갱신한다.

토큰은 60일마다 만료된다. GitHub Actions에서 30일 주기로 돌려
GitHub Secret(IG_ACCESS_TOKEN)을 자동으로 덮어쓴다.

환경변수
  IG_ACCESS_TOKEN   현재 장기 토큰 (최소 24시간 이상 사용된 토큰이어야 갱신 가능)
  GH_REPO           예) steve/ig-studio   (Secret 자동 업데이트용, 선택)
  GH_TOKEN          repo secrets 쓰기 권한 PAT      (선택)

출력: 새 토큰을 stdout과 GITHUB_OUTPUT에 기록
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

REFRESH = "https://graph.instagram.com/refresh_access_token"


def refresh(token: str) -> dict:
    url = f"{REFRESH}?{urllib.parse.urlencode({'grant_type': 'ig_refresh_token', 'access_token': token})}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"토큰 갱신 실패 HTTP {e.code}\n{e.read().decode(errors='replace')}")


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        sys.exit("IG_ACCESS_TOKEN이 없습니다.")

    data = refresh(token)
    new_token = data["access_token"]
    days = int(data.get("expires_in", 0)) // 86400
    print(f"새 토큰 발급 완료 · 만료까지 {days}일")

    repo, gh_token = os.environ.get("GH_REPO"), os.environ.get("GH_TOKEN")
    if repo and gh_token:
        env = {**os.environ, "GH_TOKEN": gh_token}
        subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN",
                        "--repo", repo, "--body", new_token],
                       check=True, env=env)
        print(f"GitHub Secret 업데이트 완료: {repo} / IG_ACCESS_TOKEN")
    else:
        print("GH_REPO/GH_TOKEN이 없어 Secret은 수동으로 갱신해야 합니다.")
        print(new_token)


if __name__ == "__main__":
    main()
