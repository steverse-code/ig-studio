# GitHub 리포지토리 세팅

이 리포지토리는 세 가지 역할을 합니다.

| 역할 | 왜 필요한가 |
|---|---|
| **이미지 호스팅** | 인스타그램은 파일 업로드가 아니라 **공개 URL**에서 이미지를 가져갑니다 |
| **OAuth 콜백 페이지** | Meta는 리디렉션 URI를 실제로 접속해 검증합니다 (localhost 불가) |
| **자동 발행 스케줄러** | GitHub Actions가 월·수·금 19:00에 발행합니다 (내 Mac이 꺼져 있어도 동작) |

**Public 이어야 합니다.** 첫 번째 역할 때문입니다. `raw.githubusercontent.com` 은
Private 리포에서는 인증 없이 접근되지 않고, 인스타그램은 인증을 걸 수 없습니다.
비밀값(토큰)은 Public 리포에서도 **GitHub Secrets** 에 암호화되어 보관되며
코드나 로그에 노출되지 않습니다.

---

## A. 리포지토리 만들기

[github.com/new](https://github.com/new)

| 항목 | 값 |
|---|---|
| Repository name | `ig-studio` |
| Description | (비워도 됨) |
| 공개 범위 | **Public** ← 중요 |
| Add a README file | **체크 해제** |
| Add .gitignore | **None** |
| Choose a license | **None** |

> 아래 세 개를 체크하면 빈 리포가 아니게 되어 첫 push 가 충돌합니다.
> 반드시 **완전히 빈 상태**로 만드세요.

**Create repository** 를 누르면 나오는 안내 화면은 그냥 두고 다음으로 갑니다.

### "이미 ig-studio 라는 이름이 있습니다" 가 뜬다면

한 계정 안에서 리포 이름은 중복될 수 없습니다. 기존 것을 먼저 확인하세요.

`https://github.com/<사용자명>/ig-studio`

**① 비어 있거나 이전 시도 흔적이라면 — 새로 만들지 말고 그대로 씁니다.**

이름이 같으니 Pages 주소와 리디렉션 URI도 그대로입니다. B 단계로 바로 가되,
push 가 거부되면 아래 "기존 리포에 덮어쓰기" 를 보세요.

**② 다른 작업이 들어 있다면 — 이름만 바꿉니다.**

```bash
bash scripts/setup-repo.sh <사용자명> ig-cardnews
```

리포 이름을 바꾸면 **리디렉션 URI도 같이 바뀝니다.** Meta 앱에 등록할 주소는
`https://<사용자명>.github.io/ig-cardnews/oauth/` 가 됩니다.

**③ 기존 것을 지우고 싶다면**

Settings → 맨 아래 Danger Zone → Delete this repository.
되돌릴 수 없으니, 안에 아무것도 없는 게 확실할 때만 하세요.

### 기존 리포에 덮어쓰기

기존 리포에 커밋이 하나라도 있으면 (README 등) 첫 push 가 이렇게 거부됩니다:

```
! [rejected] main -> main (fetch first)
```

원격 내용을 살릴 게 없다면 — 합치기:

```bash
git pull --rebase origin main
git push -u origin main
```

`refusing to merge unrelated histories` 가 나오면:

```bash
git pull --rebase --allow-unrelated-histories origin main
git push -u origin main
```

그래도 꼬이면, **원격에 남길 게 없다는 게 확실할 때만** 강제로 덮어씁니다:

```bash
git push -u --force origin main
```

> `--force` 는 원격의 기존 커밋을 지웁니다. 되돌릴 수 없습니다.

---

## B. 로컬 폴더를 올리기

Mac **터미널** 앱에서:

```bash
cd ~/Documents/ig-studio
bash scripts/setup-repo.sh <GitHub사용자명>
```

이 스크립트가 `git init` → 커밋 → 원격 주소 설정까지 해주고,
`.env` 가 실수로 커밋되지 않는지도 확인합니다.

그다음 업로드:

```bash
git push -u origin main
```

### 인증 — 여기서 한 번 막힙니다

GitHub는 2021년부터 **계정 비밀번호로는 push 할 수 없습니다.** 두 가지 방법이 있습니다.

**방법 1 — GitHub CLI (권장, 한 번만 하면 끝)**

```bash
brew install gh
gh auth login
```

- `GitHub.com` → `HTTPS` → `Login with a web browser` 선택
- 화면에 뜬 8자리 코드를 브라우저에 입력하고 승인

이후 `git push` 할 때 아무것도 묻지 않습니다.

**방법 2 — Personal Access Token**

1. [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)**
2. Note: `ig-studio`, Expiration: 원하는 기간
3. 권한: **`repo`** 체크 (workflow 도 함께 체크해두면 편합니다)
4. 생성된 토큰을 복사 (한 번만 보입니다)
5. `git push` 시 물어보는 **Password 자리에 이 토큰을 붙여넣기**
   (Username 은 GitHub 사용자명)

macOS 키체인에 저장되어 다음부터는 다시 묻지 않습니다.

> 토큰은 비밀번호와 같습니다. 채팅·메모·코드에 남기지 마세요.

### 업로드 확인

`https://github.com/<사용자명>/ig-studio` 에 파일 33개가 보이면 성공입니다.
`.env` 가 목록에 **없어야** 합니다.

---

## C. GitHub Pages 켜기 — OAuth 콜백 페이지

리포지토리 → **Settings** → 좌측 메뉴 **Pages**

| 항목 | 값 |
|---|---|
| Source | `Deploy from a branch` |
| Branch | `main` |
| Folder | **`/docs`** ← 루트가 아니라 docs |

**Save** 를 누르고 1~2분 기다린 뒤 접속:

```
https://<사용자명(소문자)>.github.io/ig-studio/oauth/
```

**"인증 코드가 없습니다"** 화면이 뜨면 정상입니다.
이 주소가 Meta 앱에 등록할 **리디렉션 URI** 입니다. (끝 슬래시 포함)

> 404 라면 아직 배포 중입니다. **Actions** 탭에서 `pages build and deployment`
> 가 초록색으로 끝났는지 확인하세요. 폴더를 `/docs` 가 아니라 `/ (root)` 로
> 잡았다면 다시 설정하세요.

---

## D. Actions 쓰기 권한 켜기 ★ 빠뜨리면 발행이 실패합니다

**Settings** → **Actions** → **General** → 페이지 맨 아래 **Workflow permissions**

- ⦿ **Read and write permissions** 선택
- **Save**

왜 필요한가: 렌더 워크플로가 만든 슬라이드 이미지를 리포에 **되커밋**하고,
발행 워크플로가 `queue.json` 의 상태를 `published` 로 바꿔 커밋하기 때문입니다.
기본값(읽기 전용)이면 이 커밋이 거부됩니다.

---

## E. Secrets 등록

**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| 이름 | 값 | 출처 |
|---|---|---|
| `IG_USER_ID` | `178414...` | `connect.py` 실행 결과 |
| `IG_ACCESS_TOKEN` | `IGQVJYQ...` | `connect.py` 실행 결과 |
| `GH_PAT` | (선택) | 토큰 자동 갱신용 — 아래 참고 |

### GH_PAT (선택이지만 권장)

이걸 넣지 않으면 60일마다 `connect.py` 를 손으로 다시 실행해야 합니다.

1. [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens)
   → **Fine-grained token** 생성
2. Repository access: **Only select repositories** → `ig-studio`
3. Permissions → Repository permissions → **Secrets: Read and write**
4. 생성된 토큰을 `GH_PAT` 이름으로 등록

매월 1일에 워크플로가 토큰을 갱신하고 `IG_ACCESS_TOKEN` 을 덮어씁니다.

---

## F. 동작 확인

**Actions** 탭으로 갑니다. 처음이면 워크플로 실행 허용 버튼이 나올 수 있으니 승인합니다.

**1) 렌더링**

`Render cardnews` → **Run workflow** → main → 실행
→ 초록불이 되고, `out/2026-08-17-vo2max/` 에 JPEG 7장이 커밋되면 성공

**2) 발행 리허설**

`Publish to Instagram` → **Run workflow**
- `slug`: `2026-08-17-vo2max`
- `dry_run`: **체크(true)**

로그에 이렇게 나오면 준비 완료입니다:

```
▸ 2026-08-17-vo2max · 슬라이드 7장 · 캡션 829자
  이미지 접근 확인 완료
  [dry-run] 여기서 중단합니다.
```

**3) 실제 발행**

같은 워크플로를 `dry_run` **해제**하고 실행 → 인스타그램에 올라갑니다.

이후로는 손대지 않아도 **월·수·금 19:00 KST** 에 큐의 다음 글이 자동 발행됩니다.

---

## 문제 해결

| 증상 | 원인 · 조치 |
|---|---|
| `push` 시 `Authentication failed` | 비밀번호 대신 PAT를 넣어야 합니다. B의 인증 항목 참고 |
| `push` 시 `rejected / fetch first` | 원격에 이미 커밋이 있음. A의 "기존 리포에 덮어쓰기" 참고 |
| 리포 이름이 이미 있다고 나옴 | A의 "이미 ig-studio 라는 이름이 있습니다" 참고 |
| Pages 주소가 404 | 폴더를 `/docs` 로 설정했는지, 배포가 끝났는지 확인 |
| 렌더 워크플로가 `permission denied` | D의 **Read and write permissions** 를 안 켠 것입니다 |
| `이미지에 접근할 수 없습니다` | 리포가 Private 이거나 렌더 워크플로가 아직 안 돌았습니다 |
| Actions 탭이 비어 있음 | 워크플로 파일이 push 되지 않았습니다. `.github/workflows/` 확인 |

---

## 요약 체크리스트

```
[ ] A. Public 리포 생성 (README 등 체크 해제)
[ ] B. setup-repo.sh 실행 → git push -u origin main
[ ] C. Settings → Pages → main / /docs
[ ] D. Settings → Actions → General → Read and write permissions   ★
[ ] E. Secrets: IG_USER_ID, IG_ACCESS_TOKEN (+ GH_PAT)
[ ] F. Render 실행 → Publish dry-run → 실제 발행
```
