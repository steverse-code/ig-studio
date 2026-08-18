#!/usr/bin/env bash
# setup-repo.sh — 로컬 폴더를 GitHub 리포지토리로 올릴 준비를 한다.
#
# 사용 (Mac 터미널에서):
#     cd ~/Documents/ig-studio
#     bash scripts/setup-repo.sh <GitHub사용자명> [리포이름]
#
# 이 스크립트는 커밋까지만 합니다. push 는 인증이 필요해서 마지막에 명령어를 안내합니다.

set -e
cd "$(dirname "$0")/.."

G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; B=$'\033[1m'; Z=$'\033[0m'
ok()   { echo "${G}✓${Z} $1"; }
warn() { echo "${Y}!${Z} $1"; }
die()  { echo "${R}✗${Z} $1"; exit 1; }

USER_NAME="$1"
REPO="${2:-ig-studio}"

if [ -z "$USER_NAME" ]; then
  echo "사용법: bash scripts/setup-repo.sh <GitHub사용자명> [리포이름]"
  echo "예:     bash scripts/setup-repo.sh steveoh ig-studio"
  exit 1
fi

echo
echo "${B}1. git 사용자 정보${Z}"
if ! git config user.name >/dev/null 2>&1 && ! git config --global user.name >/dev/null 2>&1; then
  warn "user.name 이 없습니다. 지금 설정합니다."
  read -r -p "   이름 (커밋에 표시): " GN
  read -r -p "   이메일 (GitHub 계정 이메일): " GE
  git config --global user.name "$GN"
  git config --global user.email "$GE"
fi
ok "$(git config user.name 2>/dev/null || git config --global user.name) <$(git config user.email 2>/dev/null || git config --global user.email)>"

echo
echo "${B}2. .env 보호 확인${Z}"
grep -q '^\.env$' .gitignore || die ".gitignore 에 .env 가 없습니다. 중단합니다."
ok ".env 는 커밋되지 않습니다"

echo
echo "${B}3. 저장소 초기화${Z}"
if [ -d .git ]; then
  ok "이미 git 저장소입니다"
else
  git init -q
  ok "git init 완료"
fi
git branch -M main 2>/dev/null || true

echo
echo "${B}4. 커밋${Z}"
git add -A
if git diff --staged --quiet; then
  ok "커밋할 변경 사항이 없습니다"
else
  git commit -q -m "ig-studio: 카드뉴스 자동 발행 파이프라인"
  ok "커밋 완료"
fi
echo "${D}   추적 파일 $(git ls-files | wc -l | tr -d ' ')개${Z}"

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  die ".env 가 추적되고 있습니다! 'git rm --cached .env' 후 다시 실행하세요."
fi
ok ".env 미추적 확인"

echo
echo "${B}5. 원격 저장소${Z}"
URL="https://github.com/${USER_NAME}/${REPO}.git"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$URL"
else
  git remote add origin "$URL"
fi
ok "origin → $URL"

PAGES="https://$(echo "$USER_NAME" | tr '[:upper:]' '[:lower:]').github.io/${REPO}/oauth/"

cat <<EOF

${B}────────────────────────────────────────────────────────${Z}
${B}다음 단계${Z}

${B}A.${Z} github.com/new 에서 리포지토리를 만드세요
     이름      : ${REPO}
     공개 범위 : ${G}Public${Z}   ← 반드시 Public
     README / .gitignore / license ${R}모두 체크 해제${Z}

${B}B.${Z} 아래 명령으로 업로드

     ${B}git push -u origin main${Z}

     비밀번호를 물어보면 계정 비밀번호가 아니라
     ${Y}Personal Access Token${Z} 을 넣어야 합니다.
     (github.com/settings/tokens 에서 발급, repo 권한 체크)

     더 쉬운 방법:
       brew install gh && gh auth login
     로 인증해두면 push 할 때 아무것도 안 물어봅니다.

${B}C.${Z} 업로드 후 웹에서 세 가지를 설정합니다 — GITHUB-SETUP.md 참고
     · Settings → Pages          : main / ${B}/docs${Z}
     · Settings → Actions → General : ${B}Read and write permissions${Z}
     · Settings → Secrets           : IG_USER_ID, IG_ACCESS_TOKEN

${B}D.${Z} 리디렉션 URI 는 이 주소가 됩니다 (Meta 앱에 등록)

     ${B}${PAGES}${Z}

${B}────────────────────────────────────────────────────────${Z}
EOF
