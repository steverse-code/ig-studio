# 릴스 배경음

릴스 배경음은 두 갈래입니다. `scripts/reel.py` 가 자동으로 고릅니다.

| 상황 | 쓰이는 음원 |
|---|---|
| `tracks.json` 의 `pillars` 에 해당 필러가 있고 파일도 존재 | 그 라이선스 음원 |
| 그 외 (기본값) | 필러별 합성음 — CONTENT.md §6-1 |

합성음은 외부 음원을 전혀 쓰지 않으므로 저작권 문제가 없습니다.
라이선스 음원을 쓰려면 아래 절차를 **먼저** 끝내야 합니다.

---

## 지금 등록된 음원 — Incompetech (Kevin MacLeod)

`tracks.json` 에 등록된 트랙은 [Incompetech](https://incompetech.com)
(Kevin MacLeod) 의 곡으로, **CC BY 3.0** — 출처 표기만 하면 상업적 이용 포함
자유롭게 쓸 수 있습니다. Epidemic Sound 와 달리 구독이나 세이프리스팅이
필요 없습니다. 다운로드는 Internet Archive 미러
(`archive.org/download/Incompetech/mp3-royaltyfree/<곡명>.mp3`)를 통해 받았습니다.

**캡션에 크레딧을 표기하세요**: `Music: <곡명> by Kevin MacLeod (incompetech.com)`
CC BY 라이선스의 표기 조건입니다.

같은 방식으로 다른 필러/카테고리에 곡을 추가하려면 `incompetech.com` 에서
장르·무드로 검색해 곡명을 찾은 뒤, 위 archive.org URL 패턴으로 받아서
`tracks.json` 에 등록하면 됩니다.

---

## Epidemic Sound 음원을 쓰려면 (선택 — 위 무료 음원 대신 쓰고 싶을 때)

### 1. 구독이 있어야 합니다
무료 다운로드가 없습니다. 미리듣기만 무료이고, 파일을 받으려면 활성 구독이나
단일 트랙 라이선스가 필요합니다. 구독 없이 받은 파일은 저작권 침해입니다.

### 2. 인스타그램 채널을 세이프리스팅하세요 — 발행 전에
Epidemic Sound 계정 → **Safelisting** → 인스타그램 계정 연결.
라이선스가 있어도 세이프리스팅을 안 하면 Meta 권리관리에 걸릴 수 있습니다.
**게시 전에** 켜두는 게 중요합니다.

### 3. 파일을 이 폴더에 넣으세요
필러 이름으로 저장하면 관리가 쉽습니다: `ai_news.mp3`, `longevity.mp3` …

### 4. `tracks.json` 에 등록하세요

```json
{
  "pillars": {
    "ai_news": {
      "file": "ai_news.mp3",
      "title": "곡 제목",
      "artist": "아티스트",
      "url": "https://www.epidemicsound.com/track/.../",
      "start": 24
    }
  }
}
```

`start` 는 곡에서 쓸 구간의 시작(초)입니다. 릴스는 22초 안팎이라 인트로가 길면
후렴이 시작되는 지점을 잡아주는 편이 낫습니다.

### 5. 다시 만들고 확인

```bash
python3 scripts/reel.py content/<슬러그>.json out
```

`♪ 라이선스 음원 사용: …` 이 찍히면 적용된 것입니다.
등록만 하고 파일이 없으면 경고를 찍고 합성음으로 넘어갑니다.

---

## 음원 파일은 커밋하지 않습니다

`.gitignore` 가 이 폴더의 오디오 파일을 제외합니다. 라이선스 음원을 공개
저장소에 올리는 것은 재배포에 해당해 라이선스 위반입니다.
`tracks.json` 과 이 문서만 커밋됩니다.

**주의:** 발행 워크플로는 GitHub Actions에서 도는데, 음원 파일이 저장소에 없으면
거기서 릴스를 다시 만들 때 합성음으로 떨어집니다. 라이선스 음원이 들어간 mp4 는
**로컬에서 만들어 커밋**해야 합니다 (지금도 릴스 mp4 는 그렇게 커밋됩니다).

## 곡 고를 때

카드뉴스 릴스는 글자가 주인공입니다. 가사 있는 곡이나 전개가 큰 곡은 읽기를
방해합니다. 보컬 없는 잔잔한 곡, 필러별 성격은 CONTENT.md §6-1 표를 참고하세요.
