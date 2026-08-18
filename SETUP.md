# 인스타그램 자동 발행 셋업 가이드

한 번만 세팅해두면 이후에는 `content/` 폴더에 JSON 하나 추가하는 것으로 발행이 끝납니다.

```
content/*.json  →  [렌더]  →  out/*.jpg  →  [월·수·금 19:00 KST]  →  인스타그램 발행
   (내용)          GitHub Actions            GitHub Actions cron
```

전체 소요 시간: **약 40분** (대부분은 Meta 개발자 앱 설정)

---

## 0. 미리 알아둘 것

- **인스타그램은 이미지를 "공개 URL"에서 가져갑니다.** 파일을 직접 업로드하는 방식이 아닙니다.
  그래서 이 파이프라인은 슬라이드 이미지를 GitHub 리포지토리에 커밋하고
  `raw.githubusercontent.com` 주소로 인스타그램에 넘깁니다.
  → **리포지토리는 Public이어야 합니다.** (비밀 값은 Public 리포에서도 GitHub Secrets에 안전하게 보관됩니다)
  → 예약된 글을 비공개로 두고 싶다면 8번 항목의 대안을 보세요.
- **본인 계정에 올리는 것은 Meta 앱 심사(App Review)가 필요 없습니다.** 앱을 만든 본인 계정이면 바로 됩니다.
- 계정당 24시간에 API 발행 100건 제한. 주 3회는 여유롭습니다.

---

## 1. 인스타그램 계정을 프로페셔널로 전환 (5분)

인스타그램 앱 → 설정 → 계정 유형 및 도구 → **프로페셔널 계정으로 전환** → 크리에이터 또는 비즈니스.

> Facebook 페이지 연결은 **필요 없습니다.** (Instagram Login 방식을 쓰기 때문)

---

## 2. Meta 개발자 앱 만들기 (15분)

1. https://developers.facebook.com/apps → **앱 만들기**
2. 앱 유형: **비즈니스(Business)**
3. 앱 대시보드 → 제품 추가 → **Instagram** → **API setup with Instagram login** 선택
4. **Instagram 앱 ID**와 **Instagram 앱 시크릿**을 복사해 둡니다.
5. 리디렉션 URI 등록 — **localhost는 등록되지 않습니다.** Meta가 실제로 접속해
   검증하기 때문입니다. 이 프로젝트의 `docs/` 를 GitHub Pages로 띄우고
   그 주소를 등록하세요:

   ```
   https://<GitHub사용자명>.github.io/ig-studio/oauth/
   ```

   자세한 절차는 **[CONNECT-GUIDE.md](CONNECT-GUIDE.md)** 2-5 섹션을 보세요.

6. 권한(scope) 확인 — 아래 두 개가 필요합니다:
   - `instagram_business_basic`
   - `instagram_business_content_publish`

---

## 3. 계정 연동 (3분)

내 Mac에서 이 폴더를 열고 터미널에:

```bash
python3 scripts/connect.py
```

앱 ID와 시크릿을 물어보고, 브라우저가 열립니다. 인스타그램 계정으로 승인하면 끝입니다.

```
✓ 장기 토큰 발급 · 유효기간 59일
✓ 연결 확인 → @your_handle · BUSINESS · 게시물 12개
✓ .env 저장 완료

  IG_USER_ID       = 178414...
  IG_ACCESS_TOKEN  = IGQVJYQ...
```

> 브라우저가 localhost로 못 돌아오는 환경이면 `python3 scripts/connect.py --manual` 로 실행하고
> 주소창 URL만 붙여넣으면 됩니다.

> 이 토큰은 **60일짜리**입니다. 매월 1일 GitHub Actions가 자동 갱신하므로 신경 쓸 필요 없습니다(6번 참고).

---

## 4. GitHub 리포지토리 만들기 (5분)

```bash
gh repo create ig-studio --public --source=. --push
# 또는 github.com에서 Public 리포 생성 후 push
```

---

## 5. Secrets 등록 (2분)

리포지토리 → Settings → Secrets and variables → Actions → **New repository secret**

| 이름 | 값 |
|---|---|
| `IG_USER_ID` | 3번에서 나온 값 |
| `IG_ACCESS_TOKEN` | 3번에서 나온 값 |
| `GH_PAT` | (선택) 토큰 자동 갱신용. 아래 6번 참고 |

---

## 6. 토큰 자동 갱신 켜기 (선택, 3분)

이걸 안 하면 60일마다 3번 과정을 손으로 다시 해야 합니다. 켜두는 걸 권합니다.

1. GitHub → Settings → Developer settings → **Fine-grained personal access token** 발급
   - Repository access: 이 리포만
   - Permissions: **Secrets → Read and write**
2. 그 토큰을 `GH_PAT` 라는 이름의 Secret으로 등록

이제 매월 1일 03:00 UTC에 토큰이 자동으로 갱신되고 Secret이 덮어써집니다.

---

## 7. 동작 확인 (5분)

1. **렌더 확인**: Actions 탭 → `Render cardnews` → Run workflow
   → `out/2026-08-17-vo2max/` 아래 JPEG 7장이 커밋되면 성공
2. **발행 리허설**: Actions 탭 → `Publish to Instagram` → Run workflow
   → `slug`에 `2026-08-17-vo2max`, `dry_run`은 **체크(true)**
   → 로그에 "이미지 접근 확인 완료"가 뜨면 준비 끝
3. **실제 발행**: 같은 워크플로를 `dry_run` 해제하고 실행

이후에는 손댈 필요 없이 **월·수·금 19:00 KST**에 큐의 다음 글이 자동으로 올라갑니다.

---

## 8. 예약분을 비공개로 두고 싶다면

Public 리포가 부담스러우면 이미지 호스팅만 분리하면 됩니다.

- 리포는 Private으로 두고, 이미지는 **Cloudinary 무료 플랜**이나 **Cloudflare R2** 같은 곳에 업로드
- `IMAGE_BASE_URL` Secret을 그 호스트 주소로 바꾸면 나머지 코드는 그대로 동작합니다
- (`publish.py`는 `IMAGE_BASE_URL` 환경변수만 보고 URL을 만듭니다)

---

## 매주 하는 일

새 글 하나 = JSON 파일 하나입니다.

```bash
content/2026-08-19-protein.json   # 내용 작성
```

```json
[ ... queue.json 에 한 줄 추가 ... ]
{ "slug": "2026-08-19-protein", "publish_at": "2026-08-19T19:00:00+09:00", "status": "pending" }
```

push하면 이미지는 자동으로 렌더링되고, 예약 시각에 자동으로 올라갑니다.

---

## 문제가 생기면

| 증상 | 원인 / 조치 |
|---|---|
| `이미지에 접근할 수 없습니다` | 리포가 Private이거나 `render` 워크플로가 아직 안 돌았습니다 |
| `HTTP 400 · OAuthException` | 토큰 만료. `Refresh Instagram token` 워크플로를 수동 실행 |
| `컨테이너 처리 실패` | JPEG가 아니거나 파일이 8MB를 넘는 경우. 렌더러 출력은 기본적으로 안전 범위입니다 |
| `발행할 차례인 글이 없습니다` | `queue.json`에 `status: pending`이고 시각이 지난 글이 없습니다 |
| 발행은 됐는데 순서가 뒤죽박죽 | 파일명 `_01`, `_02` 순서를 따릅니다. 렌더러가 자동 처리하므로 손대지 마세요 |

---

## 참고 문서

- [Publish Content — Instagram Platform (Meta)](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Instagram API with Instagram Login (Meta)](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/)
