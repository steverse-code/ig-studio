# 인스타그램 계정 연동 — 상세 가이드

이 문서는 `SETUP.md`의 3번 항목(계정 연동)만 떼어내 화면 단위로 풀어쓴 것입니다.
처음 하면 헷갈리는 지점이 세 군데 정도 있는데, 그 부분에 ⚠️ 표시를 해뒀습니다.

---

## 0. 먼저 — 지금 무엇을 연결하는 건가

인스타그램은 "아이디/비밀번호를 프로그램에 넣어서 로그인" 하는 방식을 **허용하지 않습니다.**
대신 이런 구조를 씁니다.

```
                    ①                        ②                        ③
  Steve의 IG 계정  ──승인──▶  Meta 앱  ──발급──▶  액세스 토큰  ──사용──▶  GitHub Actions
  (프로페셔널)              (내가 만든                (60일짜리                  (월·수·금
                            빈 껍데기)                 출입증)                    자동 발행)
```

- **Meta 앱**은 기능이 있는 프로그램이 아닙니다. "이 인스타 계정에 글을 올릴 권한을
  누구에게 줄 것인지"를 등록해두는 **신원 등록증** 같은 것입니다. 앱을 만든다고 뭔가
  개발하는 게 아니고, 양식 몇 개 채우는 게 전부입니다.
- **액세스 토큰**은 비밀번호 대신 쓰는 **출입증**입니다. 60일마다 갱신되고,
  권한 범위가 "기본 정보 읽기 + 콘텐츠 게시"로 제한돼 있습니다. 유출돼도 비밀번호가
  털리는 것과는 다르고, 언제든 Meta 대시보드에서 무효화할 수 있습니다.
- 그래서 **비밀번호를 어디에도 입력하지 않습니다.** 승인은 인스타그램 공식 화면에서만 일어납니다.

### 제가 이 과정을 대신 못 하는 이유

두 가지가 겹칩니다.

1. **승인 주체가 Steve님이어야 합니다.** OAuth 승인은 계정 소유자가 직접 하는 절차이고,
   저는 다른 사람 계정에 로그인하거나 대신 권한을 승인하지 않습니다.
2. **이 세션이 도는 클라우드 샌드박스는 Meta 서버에 접근이 차단돼 있습니다.**
   실제로 확인한 결과입니다:

   ```
   graph.instagram.com    → 연결 차단
   api.instagram.com      → 연결 차단
   ```

   토큰 교환은 이 두 주소와 통신해야 하므로, Steve님 Mac에서 실행돼야 합니다.

그래서 **Mac에서 명령어 한 줄로 끝나도록** 스크립트를 만들어 `~/Documents/ig-studio/`에
넣어뒀고, 그 컴퓨터에서 실제로 실행되는 것까지 확인했습니다.

---

## 1단계 — 인스타그램 계정을 프로페셔널로 전환

**소요 2분 · 인스타그램 모바일 앱에서**

1. 내 프로필 → 우측 상단 **☰** → **설정 및 개인정보**
2. 아래로 스크롤 → **계정 유형 및 도구**
3. **프로페셔널 계정으로 전환**
4. 카테고리 선택 (예: *디지털 크리에이터*, *건강/웰니스*)
5. **크리에이터** 또는 **비즈니스** 선택
   - 어느 쪽이든 콘텐츠 게시 API는 동일하게 동작합니다
   - 광고를 돌릴 계획이 있으면 비즈니스, 아니면 크리에이터가 무난합니다
6. 이후 나오는 "Facebook 페이지 연결" 화면은 **건너뛰기** 해도 됩니다

> ⚠️ **헷갈리는 지점 1 — Facebook 페이지**
> 예전(Instagram Graph API) 방식은 Facebook 페이지 연결이 필수였습니다.
> 우리가 쓰는 **Instagram API with Instagram Login**은 2024년 7월부터
> 페이지 없이 동작합니다. 인터넷의 오래된 글들이 "페이지를 만들어야 한다"고
> 하는데, 지금은 필요 없습니다.

**확인 방법**: 프로필에 인사이트/프로페셔널 대시보드 메뉴가 보이면 전환된 것입니다.

---

## 2단계 — Meta 개발자 앱 만들기

**소요 10~15분 · 데스크톱 브라우저에서**

여기가 전체 과정에서 제일 손이 많이 가는 부분입니다.

### 2-1. 개발자 계정 등록

[developers.facebook.com](https://developers.facebook.com) 접속 → 우측 상단 **시작하기**
평소 쓰는 Facebook 계정으로 로그인하고, 안내대로 개발자 등록을 마칩니다.
(Facebook 계정이 없으면 하나 만들어야 합니다. 인스타그램 계정과 연결할 필요는 없습니다.)

### 2-2. 앱 생성

1. [developers.facebook.com/apps](https://developers.facebook.com/apps) → **앱 만들기**
2. **사용 사례(use case)** 선택 화면 → **기타 (Other)**
3. **앱 유형** → **비즈니스 (Business)**
4. 앱 이름 입력 (아무거나 — 예: `ig-studio`), 연락처 이메일 확인 → **앱 만들기**

> ⚠️ **헷갈리는 지점 2 — 사용 사례 선택**
> 첫 화면에 "Instagram" 사용 사례가 보일 수 있는데, 그걸 고르면 원하는
> 설정 화면이 안 나오는 경우가 있습니다. **기타 → 비즈니스** 조합이 확실합니다.

### 2-3. Instagram 제품 추가

앱 대시보드 좌측 메뉴 또는 제품 목록에서 **Instagram** 찾기 → **설정하기(Set up)**

들어가면 화면에 번호가 붙은 섹션 세 개가 보입니다:

```
1. 액세스 토큰 생성        ← 여기서 앱 ID / 시크릿을 확인
2. 웹훅 구성               ← 건너뜁니다 (우리는 안 씀)
3. Instagram 비즈니스 로그인 설정   ← 리디렉션 URI를 여기에 등록
```

상단에 **API setup with Instagram login** 과 **API setup with Facebook login**
탭이 있으면 **Instagram login** 쪽을 선택합니다. (보통 기본값입니다)

### 2-4. 앱 ID와 시크릿 복사

**1. 액세스 토큰 생성** 섹션에 이렇게 표시됩니다:

```
Instagram 앱 ID        1234567890123456      [복사]
Instagram 앱 시크릿     ●●●●●●●●●●●●●●●●      [표시] [복사]
```

두 값을 메모장에 복사해 둡니다.

> ⚠️ **헷갈리는 지점 3 — 앱 ID가 두 종류입니다**
> 앱 대시보드 상단이나 **설정 → 기본 설정**에도 "앱 ID / 앱 시크릿"이 있는데,
> 그건 **Facebook 앱** 자격증명이라 이 흐름에서는 동작하지 않습니다.
> 반드시 **Instagram 섹션 안에 있는** "Instagram 앱 ID / Instagram 앱 시크릿"을
> 쓰세요. 이걸 잘못 넣으면 3단계에서 `HTTP 400` 이 납니다.

### 2-5. 리디렉션 URI 등록 ★ 가장 까다로운 단계

> **주의 — localhost 는 등록할 수 없습니다.**
> Meta는 저장할 때 그 주소에 **실제로 접속해서 살아있는지 검증**합니다.
> `http://localhost:8000/callback` 을 넣으면
> *"리디렉션 URI를 저장하는 중 오류가 발생했습니다. 리디렉션 URI를 인증한 후
> 다시 시도하세요"* 가 나옵니다. Meta 서버에서 내 Mac의 localhost에
> 접속할 수 없기 때문이고, 정상 동작입니다.
>
> 그래서 **공개 HTTPS 주소**가 하나 필요합니다.
> 이 프로젝트에는 그 용도의 페이지가 이미 들어 있습니다 → `docs/oauth/index.html`
> GitHub Pages로 띄우면 됩니다. 무료이고, 어차피 리포지토리는 만들어야 합니다.

#### ① GitHub 리포지토리를 먼저 만듭니다

원래 순서상 나중이지만, 리디렉션 URI 때문에 여기서 먼저 합니다.

1. [github.com/new](https://github.com/new) → 이름 `ig-studio` → **Public** → 생성
2. Mac 터미널에서:

   ```bash
   cd ~/Documents/ig-studio
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<GitHub사용자명>/ig-studio.git
   git push -u origin main
   ```

#### ② GitHub Pages 켜기

리포지토리 → **Settings** → 좌측 **Pages**

- **Source**: `Deploy from a branch`
- **Branch**: `main` / 폴더는 **`/docs`** 선택 → **Save**

1~2분 뒤 아래 주소가 열리는지 확인합니다:

```
https://<GitHub사용자명>.github.io/ig-studio/oauth/
```

"인증 코드가 없습니다" 화면이 보이면 정상입니다. (아직 코드가 없으니까요)

> 페이지가 404면 아직 배포 중입니다. Actions 탭에서 `pages build and deployment`가
> 끝났는지 확인하고 1~2분 더 기다리세요.

#### ③ Meta에 이 주소를 등록

**3. Instagram 비즈니스 로그인 설정** → **설정하기(Set up)**
→ **비즈니스 로그인 설정 (Business login settings)**

**OAuth 리디렉션 URI** 칸에 위 주소를 넣고, 옆의 **인증(Validate)** 버튼을 누른 뒤 저장:

```
https://<GitHub사용자명>.github.io/ig-studio/oauth/
```

- **끝의 슬래시(`/`)를 반드시 포함**하세요. 여기서 정한 형태를 나중에 스크립트에도
  똑같이 넣어야 합니다
- "Deauthorize callback URL", "Data deletion request URL"은 비워둬도 됩니다.
  만약 필수라고 나오면 같은 주소를 넣으면 됩니다

#### 이 페이지가 하는 일

승인이 끝나면 인스타그램이 `...?code=XXXX` 형태로 이 주소로 보냅니다.
페이지는 그 코드를 화면에 표시하고 **[코드 복사]** 버튼을 띄웁니다.
정적 HTML이라 **코드가 어디로도 전송되지 않습니다** — 브라우저 안에서만 처리됩니다.

#### GitHub 없이 하고 싶다면

`ngrok`으로 임시 HTTPS 터널을 열어도 됩니다. 다만 무료 플랜은 재시작할 때마다
주소가 바뀌어서 그때마다 Meta에 다시 등록해야 합니다. GitHub Pages 쪽이 편합니다.

```bash
brew install ngrok
python3 -m http.server 8000 --directory docs &
ngrok http 8000
# 출력된 https://xxxx.ngrok-free.app/oauth/ 를 Meta에 등록
```

### 2-6. 권한(scope) 확인 — 켜고 끄는 설정이 아닙니다

여기서 오해하기 쉬운데, **어딘가에서 체크박스를 켜야 하는 게 아닙니다.**

권한은 **로그인 요청 주소(authorization URL)의 `scope` 파라미터로 그때그때 요청**됩니다.
`connect.py` 가 이미 아래 두 개를 담아서 보냅니다:

```
scope=instagram_business_basic,instagram_business_content_publish
        └ 계정 기본 정보 읽기        └ 콘텐츠 게시 (핵심)
```

그리고 이 두 권한은 **표준 액세스(Standard Access)** 라서, 개발 모드의 앱에서
본인 계정(관리자·테스터)에는 **앱 검수 없이 바로 적용**됩니다.
그래서 대부분의 경우 2-6은 그냥 넘어가도 됩니다.

#### 그래도 눈으로 확인하고 싶다면

| 어디서 | 무엇이 보이나 |
|---|---|
| **앱 검수(App Review) → 권한 및 기능(Permissions and Features)** | 검색창에 `instagram_business` 입력 → 두 권한이 **표준 액세스 / 사용 가능** 상태인지 |
| **Instagram → 비즈니스 로그인 설정** | 권한 목록과, 그걸로 만들어지는 로그인 URL |

#### 가장 확실한 확인법 — 승인 화면

3단계에서 인스타그램 승인 화면이 떴을 때 이런 항목이 보이면 정상입니다:

```
○○님의 프로필 정보에 액세스
○○님의 계정에 콘텐츠를 게시          ← 이게 보여야 합니다
```

**"콘텐츠를 게시" 문구가 없다면** 권한이 빠진 것이므로, 그때 위 표의 경로에서
확인하면 됩니다. 있으면 그냥 승인하고 진행하세요.

### 2-7. 앱 심사(App Review)는?

**필요 없습니다.** 앱 심사는 *남의 계정*을 다루는 서비스를 만들 때 요구됩니다.
앱을 만든 본인의 인스타그램 계정에 올리는 것은 개발 모드에서 바로 됩니다.

> 만약 승인 화면에서 계정이 목록에 안 뜨면, 앱 대시보드의
> **앱 역할(App Roles) → 역할(Roles)** 에서 해당 인스타그램 계정을
> 테스터로 추가하고, 인스타그램 앱의 알림에서 초대를 수락하세요.

---

## 3단계 — 연동 실행

**소요 3분 · Mac 터미널에서**

```bash
cd ~/Documents/ig-studio
python3 scripts/connect.py
```

세 가지를 물어봅니다 — **앱 ID**, **앱 시크릿**, **리디렉션 URI**.
리디렉션 URI는 2-5에서 Meta에 등록한 값과 **한 글자도 다르면 안 됩니다** (끝 슬래시 포함).

### 실행하면 순서대로 이런 일이 일어납니다

```
1  앱 ID / 시크릿 / 리디렉션 URI 입력
2  브라우저가 인스타그램 승인 화면으로 이동합니다
3  "○○님의 계정에 콘텐츠를 게시하도록 허용" 승인
4  GitHub Pages 콜백 페이지로 이동 → 인증 코드가 표시됨 (1회용, 몇 분 후 만료)
5  [코드 복사] → 터미널의 "인증 코드:" 프롬프트에 붙여넣기
6  스크립트가 코드 → 단기 토큰(1시간) → 장기 토큰(60일) 로 교환
7  /me 를 호출해 실제로 연결됐는지 검증
8  .env 에 저장하고, GitHub Secrets에 넣을 값을 출력
```

### 성공하면 이렇게 나옵니다

```
✓ 인증 코드 수신
✓ 단기 토큰 발급
✓ 장기 토큰 발급 · 유효기간 59일
✓ 연결 확인 → @your_handle · BUSINESS · 게시물 12개
✓ .env 저장 완료 → /Users/steveoh/Documents/ig-studio/.env

GitHub Secrets 에 등록할 값
  IG_USER_ID       = 17841400000000000
  IG_ACCESS_TOKEN  = IGQVJYQ...
```

### 값을 매번 입력하기 싫다면

```bash
python3 scripts/connect.py \
  --app-id 1234567890 \
  --app-secret abcdef... \
  --redirect-uri https://steveoh.github.io/ig-studio/oauth/
```

한 번 성공하면 `.env`에 저장되므로, 다음부터는 그냥 `python3 scripts/connect.py` 만
실행해도 저장된 값을 재사용합니다.

### 콜백 페이지에 코드가 안 보일 때

주소창의 URL 전체를 복사해서 그대로 붙여넣어도 됩니다.
스크립트가 URL에서 `code` 값을 알아서 뽑아냅니다.

---

## ★ "개발자 역할 권한이 부족합니다" (Insufficient Developer Role)

2단계에서 인스타그램 로그인을 했을 때 가장 흔하게 나오는 오류입니다.
**권한을 더 신청해야 한다는 뜻이 아니라**, 앱이 아직 개발 모드라서
"이 앱을 써도 되는 계정 명단"에 해당 인스타그램 계정이 없다는 뜻입니다.

앱을 만든 본인이고 관리자여도 나옵니다. Facebook 쪽 관리자 권한과
Instagram 쪽 테스터 등록이 **별개**이기 때문입니다.

### 고치는 순서

**A. 앱에 인스타그램 계정을 테스터로 추가**

1. 앱 대시보드 좌측 메뉴 → **앱 역할(App roles)** → **역할(Roles)**
2. 아래로 스크롤 → **Instagram 테스터(Instagram testers)** 섹션
3. **사람 추가(Add people)** → 인스타그램 **사용자명**(@ 없이) 입력 → 추가
4. 목록에 `대기 중(Pending)` 으로 표시됩니다

> Instagram 테스터 섹션이 안 보이면, 아직 Instagram 제품이 앱에 추가되지 않은
> 것입니다. 2-3을 먼저 마치세요.

**B. 인스타그램에서 초대 수락** ← 이 단계를 빠뜨려서 막히는 경우가 대부분입니다

브라우저에서 접속:

```
https://www.instagram.com/accounts/manage_access/
```

→ **테스터 초대(Tester invites)** 탭 → 해당 앱 **수락(Accept)**

모바일 앱이라면: 설정 및 개인정보 → **웹사이트 권한** → **테스터 초대** → 수락

**C. 브라우저에 로그인된 계정 확인**

두 번째로 흔한 원인입니다. 브라우저에 **다른 인스타그램 계정**이 로그인돼
있으면 초대를 수락해도 계속 같은 오류가 납니다.

1. instagram.com 접속 → 우측 상단에 어떤 계정인지 확인
2. 다른 계정이면 로그아웃
3. 가장 확실한 방법: **시크릿 창(⌘⇧N)** 을 열어 목표 계정으로만 로그인한 뒤 진행

**D. 다시 시도**

Meta 앱 대시보드로 돌아가 앱 ID·시크릿 확인 또는 계정 추가를 다시 하면
이번에는 통과합니다.

### 그래도 안 되면 확인할 것

| 확인 항목 | 왜 |
|---|---|
| 계정이 **프로페셔널**인가 | 개인 계정은 테스터로 추가돼도 콘텐츠 게시 권한이 없습니다 |
| 계정이 **공개(Public)** 인가 | 비공개 계정은 테스터 등록이 거부됩니다 |
| 사용자명을 정확히 입력했나 | 표시 이름이 아니라 `@` 뒤의 **사용자명**입니다 |
| 초대 상태가 `수락됨`인가 | 역할(Roles) 화면에서 `대기 중`이면 B가 안 끝난 것입니다 |

---

## ★ "Invalid redirect_uri" (요청 매개변수가 유효하지 않습니다)

승인 화면 대신 이 오류가 뜬다면, **Meta에 등록한 주소와 스크립트가 보낸 주소가
한 글자라도 다르다**는 뜻입니다. Meta는 완전 일치만 인정합니다.

진단 스크립트를 넣어뒀습니다. 두 값을 붙여넣으면 어디서 갈리는지 짚어줍니다.

```bash
cd ~/Documents/ig-studio
python3 scripts/doctor.py
```

```
① Meta에 등록한 값을 그대로 붙여넣기 : https://steveoh.github.io/ig-studio/oauth/
② 스크립트에 입력한 값               : https://SteveOh.github.io/ig-studio/oauth

✗ 두 값이 다릅니다
  9번째 글자부터 갈립니다:
    등록값   …https://steveoh.github
    입력값   …https://SteveOh.github
! 끝에 슬래시(/)가 없습니다
```

### 실제로 걸리는 원인 (빈도순)

| # | 원인 | 확인 |
|---|---|---|
| 1 | **끝 슬래시** `/oauth` vs `/oauth/` | 등록값에 `/` 가 있으면 입력값에도 있어야 합니다 |
| 2 | **대소문자** `SteveOh` vs `steveoh` | GitHub Pages 주소는 전부 **소문자**입니다 |
| 3 | **저장 안 됨** | 인증(Validate) 버튼만 누르고 **변경 내용 저장**을 안 누른 경우. 새로고침해서 값이 남아 있는지 확인 |
| 4 | **엉뚱한 칸에 입력** | `OAuth 리디렉션 URI` 칸이어야 합니다. Deauthorize callback URL / Data deletion request URL 칸이 아닙니다 |
| 5 | **Facebook 로그인 쪽에 입력** | Facebook 로그인 제품의 "유효한 OAuth 리디렉션 URI"가 아니라, **Instagram 제품 → 비즈니스 로그인 설정** 안이어야 합니다 |
| 6 | 리포 이름 오타 | `ig-studio` 철자 확인 |

### 가장 확실한 방법

Meta 설정 화면의 값을 **마우스로 드래그해서 복사**한 뒤, 그대로 터미널에 붙여넣으세요.
직접 타이핑하면 1·2번이 거의 반드시 발생합니다.

```bash
python3 scripts/connect.py --redirect-uri "여기에_붙여넣기"
```

---

## 에러 사전

| 화면에 나오는 것 | 원인 | 조치 |
|---|---|---|
| `리디렉션 URI를 저장하는 중 오류가 발생했습니다` | localhost 등 Meta가 접속할 수 없는 주소 | 2-5 참고 — GitHub Pages 공개 HTTPS 주소를 쓰세요 |
| `Invalid redirect_uri` | 등록값과 스크립트 입력값이 다름 | 바로 위 ★ 섹션 — `python3 scripts/doctor.py` |
| Pages 주소가 404 | 배포가 아직 안 끝남 / 폴더 설정 오류 | Settings → Pages 에서 `/docs` 선택 확인, 1~2분 대기 |
| `개발자 역할 권한이 부족합니다` | 앱이 개발 모드 + 계정이 테스터 명단에 없음 | 바로 위 ★ 섹션 참고 |
| `HTTP 400 · OAuthException` | Facebook 앱 시크릿을 넣었을 가능성 | 2-4의 ⚠️ 참고 — Instagram 섹션의 시크릿을 쓰세요 |
| `code` 관련 오류 반복 | 인증 코드는 1회용 | 스크립트를 처음부터 다시 실행 |
| 승인 화면에 계정이 안 보임 | 프로페셔널 전환이 안 됨 | 1단계 다시 확인 |
| `프로페셔널 계정이 아닌 것 같습니다` | 전환 직후 반영 지연 | 몇 분 뒤 재실행 |
| `localhost:8000 을 열 수 없습니다` | 8000 포트를 다른 앱이 사용 중 | 해당 앱 종료 후 재시도, 또는 `--manual` |

---

## 연동 후 — 남은 것

리포지토리는 2-5에서 이미 만들었으므로, 남은 건 네 가지입니다.

1. **Settings → Secrets and variables → Actions** 에 `IG_USER_ID`, `IG_ACCESS_TOKEN` 등록
2. **Actions → Render cardnews** 수동 실행 → 슬라이드 7장이 커밋되는지 확인
3. **Actions → Publish to Instagram** 을 `dry_run` 체크하고 실행 → 리허설
4. `dry_run` 해제하고 실행 → 첫 글 발행 → 이후 **월·수·금 19:00 KST** 자동 발행

> 리포지토리가 **Public** 이어야 합니다. 인스타그램이 슬라이드 이미지를
> 공개 URL(`raw.githubusercontent.com`)에서 가져가기 때문입니다.
> 비밀값은 Public 리포에서도 GitHub Secrets에 안전하게 보관됩니다.

토큰 갱신은 매월 1일 워크플로가 자동으로 처리합니다 (`GH_PAT` 등록 시).

---

## 보안 메모

- `.env` 파일은 `.gitignore`에 들어 있어 커밋되지 않습니다. 권한도 600으로 설정됩니다.
- **액세스 토큰과 앱 시크릿을 채팅창에 붙여넣지 마세요.** 연동 확인은
  출력의 `@계정명 · BUSINESS` 줄만 알려주시면 충분합니다.
- 토큰을 무효화하고 싶으면: 인스타그램 앱 → 설정 → 웹사이트 권한 →
  앱 및 웹사이트에서 해당 앱을 제거하면 즉시 만료됩니다.

---

## 참고 문서

- [Create an Instagram App — Meta](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app/)
- [Instagram API with Instagram Login — Meta](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/)
- [Publish Content — Meta](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
