# ig-studio

롱제비티 · 라이프스타일 · 패션 카드뉴스를 만들어 인스타그램에 자동 발행하는 파이프라인.

```
content/*.json      글 하나 = JSON 하나 (슬라이드 + 캡션 + 해시태그)
scripts/cardnews.py 1080×1350 슬라이드 렌더러 (Pretendard, 필러별 테마)
scripts/publish.py  캐러셀 발행 (Instagram API with Instagram Login)
scripts/connect.py  계정 연동 (최초 1회) — 토큰 발급 + 검증 + .env 저장
scripts/refresh_token.py  60일 토큰 자동 갱신
queue.json          발행 큐
.github/workflows/  렌더 · 발행(월수금 19:00 KST) · 토큰 갱신(월 1회)
```

- **전체 셋업**: [SETUP.md](SETUP.md) — 약 40분, 한 번만
- **GitHub 세팅**: [GITHUB-SETUP.md](GITHUB-SETUP.md) — 리포 · Pages · Actions · Secrets
- **계정 연동**: [CONNECT-GUIDE.md](CONNECT-GUIDE.md) — Meta 앱 · 토큰 · 오류 해결
- **운영**: [CONTENT.md](CONTENT.md) — 톤 규칙, 카드뉴스 구조, 8주 로드맵

## 로컬에서 미리보기

```bash
pip install pillow
python3 scripts/cardnews.py content/2026-08-17-vo2max.json out/
```

## 발행 리허설

```bash
IMAGE_BASE_URL=https://raw.githubusercontent.com/<user>/<repo>/main \
  python3 scripts/publish.py --dry-run --slug 2026-08-17-vo2max
```

## 슬라이드 타입

| type | 용도 | 필드 |
|---|---|---|
| `cover` | 표지 | `headline`, `subline`, `badge` |
| `stat` | 핵심 수치 (액센트 배경) | `value`, `label`, `eyebrow`, `note` |
| `point` | 본문 한 덩어리 | `title`, `body`, `index` |
| `list` | 항목 나열 | `title`, `items[{t,d}]` |
| `quote` | 인용 / 한계 언급 | `text`, `by` |
| `source` | 출처 + CTA | `title`, `sources[]`, `cta` |

`pillar`는 `longevity` / `lifestyle` / `fashion` — 액센트 컬러가 바뀝니다.
