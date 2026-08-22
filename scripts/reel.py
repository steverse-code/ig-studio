#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reel.py — 카드뉴스 슬라이드를 이어붙여 Instagram 릴스(세로 영상)를 만든다.

각 슬라이드 이미지에 이미 헤드라인/자막/본문이 디자인되어 있으므로,
슬라이드를 Ken Burns(천천히 줌) 효과로 순서대로 보여주고
배경음을 깔아 mp4로 내보낸다.

배경음은 두 갈래다.

1. assets/music/tracks.json 에 해당 필러 트랙이 등록돼 있으면 그 음원을 쓴다
   (Epidemic Sound 등 라이선스 구매한 음원 — 파일은 직접 내려받아 넣어야 한다)
2. 없으면 필러별 화음·맥박으로 그 자리에서 합성한다 — MUSIC 표 참고.
   외부 음원을 전혀 쓰지 않으므로 저작권 문제가 없다.

사용:
    python3 scripts/reel.py content/2026-08-17-vo2max.json out/
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT_DIR, "assets", "music")
TRACKS_JSON = os.path.join(MUSIC_DIR, "tracks.json")

W, H, FPS = 1080, 1350, 30

# 라이선스 음원 목표 라우드니스 — 인스타그램 사회적 표준에 맞춘 통합 -14 LUFS
TARGET_LUFS = -14.0

# 슬라이드 타입별 노출 시간(초) — 커버/출처는 조금 더 길게
DURATION = {
    "cover": 3.4, "stat": 2.8, "point": 3.0,
    "list": 3.2, "quote": 3.0, "source": 3.6,
}


def run(cmd: list[str]):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"명령 실패: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r


def build_segment(img_path: str, duration: float, out_path: str):
    frames = max(1, int(duration * FPS))
    zoom_per_frame = 0.10 / frames  # 전체 구간에 걸쳐 10% 확대
    vf = (
        f"scale={W * 2}:{H * 2},"
        f"zoompan=z='min(zoom+{zoom_per_frame:.6f},1.10)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        f"format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", img_path,
        "-vf", vf, "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", out_path,
    ])


# ─────────────────────────────────────────────────────────────
# 필러별 배경음 프로파일
#
# 모든 음원은 ffmpeg 의 sine/anoisesrc 로 **매 실행마다 새로 합성**한다.
# 외부 음원·샘플·음악 라이브러리를 일절 쓰지 않으므로 저작권 분쟁 소지가 없다.
# (인스타그램 licensed music 라이브러리는 Graph API 로 붙일 수 없다 —
#  API 발행 릴스는 mp4 에 구워 넣은 오리지널 오디오만 갖는다.)
#
#   tones   : (주파수 Hz, 볼륨) — 화음. 낮은 옥타브 위주로 깔아 무게를 준다
#   pulse   : 맥박 속도(Hz). 1.0 = 60BPM. 느릴수록 정적이다
#   depth   : 맥박의 깊이(0~1). 클수록 리듬이 또렷하다
#   echo    : (in_gain, out_gain, delay_ms, decay) — 공간감
#   air     : 갈색 잡음 레이어 볼륨. 디지털한 정적을 덜어낸다
#   lowpass : 고역 차단(Hz). 낮을수록 어둡고 따뜻하다
# ─────────────────────────────────────────────────────────────
MUSIC = {
    # 롱제비티 — A단조. 안정 심박(약 51BPM)에 맞춘 느린 맥박
    "longevity": {
        # 디튠 금지: 두 음의 차이가 그대로 맥놀이(Hz)가 되고, 그 맥놀이는 진폭이
        # 100%라 tremolo(depth 0.20)를 항상 이긴다. 여기선 심박 맥박이 주인공이라
        # 디튠 대신 5도(E2)를 깔아 두께를 만든다.
        "tones": [(55.00, 0.075), (82.41, 0.045), (110.00, 0.055),
                  (130.81, 0.042), (164.81, 0.036)],
        "pulse": 0.85, "depth": 0.24,
        "echo": (0.85, 0.9, 1600, 0.40), "air": 0.010, "lowpass": 1700,
    },
    # 노화·의학 뉴스 — D단조. 임상적이고 중립적인 톤, 맥박 거의 없음
    "aging_news": {
        "tones": [(73.42, 0.070), (146.83, 0.050), (174.61, 0.040),
                  (220.00, 0.032)],
        "pulse": 0.14, "depth": 0.16,
        "echo": (0.85, 0.9, 1200, 0.38), "air": 0.008, "lowpass": 2100,
    },
    # AI 소식 — E단조 + 미세 디튠. 기계적인 규칙 펄스
    "ai_news": {
        "tones": [(41.20, 0.075), (82.41, 0.060), (82.90, 0.045),
                  (98.00, 0.045), (123.47, 0.040)],
        "pulse": 1.40, "depth": 0.30,
        "echo": (0.85, 0.9, 1400, 0.45), "air": 0.012, "lowpass": 2400,
    },
    # 한국 맛집 — F장조. 유일하게 장조, 따뜻하고 부드럽게
    "food": {
        "tones": [(43.65, 0.070), (87.31, 0.055), (110.00, 0.042),
                  (130.81, 0.038)],
        "pulse": 0.50, "depth": 0.14,
        "echo": (0.85, 0.9, 1100, 0.35), "air": 0.010, "lowpass": 1500,
    },
    # 성공하는 법 — C단조. 단단하고 또렷한 맥박
    "success": {
        "tones": [(65.41, 0.075), (130.81, 0.055), (155.56, 0.042),
                  (196.00, 0.036)],
        "pulse": 1.00, "depth": 0.26,
        "echo": (0.85, 0.9, 1300, 0.40), "air": 0.009, "lowpass": 2200,
    },
    # 패션 트렌드 — B♭단조. 잔향을 길게 잡아 공간감 위주로
    "fashion": {
        "tones": [(58.27, 0.070), (116.54, 0.052), (138.59, 0.040),
                  (174.61, 0.034)],
        "pulse": 0.35, "depth": 0.16,
        "echo": (0.88, 0.9, 1900, 0.50), "air": 0.011, "lowpass": 2000,
    },
    # 연애심리 — G장조. 장3도를 부드럽게, 맥박은 거의 숨긴다
    "relationships": {
        "tones": [(49.00, 0.070), (98.00, 0.055), (123.47, 0.040),
                  (146.83, 0.036)],
        "pulse": 0.45, "depth": 0.14,
        "echo": (0.85, 0.9, 1500, 0.42), "air": 0.010, "lowpass": 1600,
    },
}

# 구 lifestyle 필러(alcohol-limits, coffee-mortality 등)는 CONTENT.md §9 기준
# 노화·의학 뉴스로 재분류 예정이므로 같은 프로파일을 쓴다.
MUSIC["lifestyle"] = MUSIC["aging_news"]

# 필러가 비어 있거나 표에 없을 때
MUSIC_DEFAULT = MUSIC["aging_news"]


# ─────────────────────────────────────────────────────────────
# 라이선스 음원 (Epidemic Sound 등)
#
# assets/music/tracks.json 에 필러별 트랙을 등록하면 합성음 대신 그 음원을 쓴다.
# 음원 파일 자체는 **구독자가 직접 내려받아** assets/music/ 에 넣어야 한다 —
# Epidemic Sound 는 구독 없이 다운로드할 수 없고, 무단 다운로드는 저작권 침해다.
#
# 발행 전 반드시 Epidemic Sound 계정에서 인스타그램 채널을 세이프리스팅할 것.
# 안 하면 라이선스가 있어도 Meta 권리관리에 걸릴 수 있다.
# ─────────────────────────────────────────────────────────────
def load_tracks() -> dict:
    if not os.path.exists(TRACKS_JSON):
        return {}
    try:
        return json.load(open(TRACKS_JSON, encoding="utf-8")).get("pillars", {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ! tracks.json 을 읽지 못했습니다 ({e}) — 합성음으로 진행합니다")
        return {}


def find_track(pillar: str | None) -> dict | None:
    """필러에 등록된 라이선스 음원. 파일이 실제로 있을 때만 돌려준다."""
    entry = load_tracks().get(pillar or "")
    if not entry or not entry.get("file"):
        return None
    path = entry["file"]
    path = path if os.path.isabs(path) else os.path.join(MUSIC_DIR, path)
    if not os.path.exists(path):
        print(f"  ! {pillar}: tracks.json 에 등록됐지만 파일이 없습니다 → {path}")
        return None
    return {**entry, "path": path}


def build_licensed_bed(duration: float, out_path: str, track: dict):
    """구매한 음원을 릴스 길이에 맞춰 자르고 라우드니스를 맞춘다."""
    fade_out = max(0.0, duration - 1.6)
    start = float(track.get("start", 0))  # 곡에서 쓸 구간의 시작(초)
    filt = (
        f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11,"
        f"afade=t=in:d=1.2,afade=t=out:st={fade_out:.3f}:d=1.6"
    )
    run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",          # 곡이 짧으면 이어붙여 길이를 채운다
        "-ss", f"{start:.3f}", "-i", track["path"],
        "-af", filt, "-t", f"{duration:.3f}",
        "-ar", "44100", "-ac", "2", out_path,
    ])
    label = track.get("title") or os.path.basename(track["path"])
    print(f"  ♪ 라이선스 음원 사용: {label}"
          + (f" — {track['artist']}" if track.get("artist") else ""))


def build_music_bed(duration: float, out_path: str, pillar: str | None = None):
    """필러에 맞는 배경음을 그 자리에서 합성한다 — 외부 음원 없음, 저작권 무관."""
    m = MUSIC.get(pillar or "", MUSIC_DEFAULT)
    d = duration + 1.0

    inputs = []
    for freq, vol in m["tones"]:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={d},volume={vol}"]
    if m["air"]:
        inputs += ["-f", "lavfi", "-i", f"anoisesrc=color=brown:duration={d},volume={m['air']}"]

    n = len(m["tones"]) + (1 if m["air"] else 0)
    mix = "".join(f"[{i}]" for i in range(n))
    ig, og, delay, decay = m["echo"]
    fade_out = max(0.0, duration - 1.4)
    filt = (
        f"{mix}amix=inputs={n}:duration=longest,"
        f"tremolo=f={m['pulse']}:d={m['depth']},"
        f"aecho={ig}:{og}:{delay}:{decay},"
        f"lowpass=f={m['lowpass']},"
        f"alimiter=limit=0.7,"
        f"afade=t=in:d=1.4,afade=t=out:st={fade_out:.3f}:d=1.4"
    )
    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filt,
        "-t", f"{duration:.3f}", "-ar", "44100", out_path,
    ])


def build_reel(spec: dict, slides_dir: str, outdir: str) -> str:
    os.makedirs(outdir, exist_ok=True)
    slides = spec["slides"]
    with tempfile.TemporaryDirectory() as tmp:
        seg_paths = []
        total = 0.0
        for i, s in enumerate(slides):
            img = os.path.join(slides_dir, f"{spec['slug']}_{i + 1:02d}.jpg")
            dur = DURATION.get(s["type"], 3.0)
            seg = os.path.join(tmp, f"seg_{i:02d}.mp4")
            build_segment(img, dur, seg)
            seg_paths.append(seg)
            total += dur

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w") as f:
            for p in seg_paths:
                f.write(f"file '{p}'\n")
        video_only = os.path.join(tmp, "video_only.mp4")
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", video_only,
        ])

        audio_path = os.path.join(tmp, "bed.wav")
        pillar = spec.get("pillar")
        track = find_track(pillar)
        if track:
            build_licensed_bed(total, audio_path, track)
        else:
            build_music_bed(total, audio_path, pillar)

        out_path = os.path.join(outdir, f"{spec['slug']}_reel.mp4")
        run([
            "ffmpeg", "-y", "-i", video_only, "-i", audio_path,
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", out_path,
        ])
        return out_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2] if len(sys.argv) > 2 else "out"
    slides_dir = os.path.join(outdir, spec["slug"])
    path = build_reel(spec, slides_dir, os.path.join(outdir, spec["slug"]))
    print(path)


if __name__ == "__main__":
    main()
