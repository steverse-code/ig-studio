#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reel.py — 카드뉴스 슬라이드를 이어붙여 Instagram 릴스(세로 영상)를 만든다.

각 슬라이드 이미지에 이미 헤드라인/자막/본문이 디자인되어 있으므로,
슬라이드를 Ken Burns(천천히 줌) 효과로 순서대로 보여주고
저작권 걱정 없는 자체 생성 앰비언트 배경음을 깔아 mp4로 내보낸다.

사용:
    python3 scripts/reel.py content/2026-08-17-vo2max.json out/
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

W, H, FPS = 1080, 1350, 30

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


def build_ambient_bed(duration: float, out_path: str):
    """저작권 없는 자체 생성 배경음 — 저음 단조 드론 + 느린 스웰로 무게감 있는 톤."""
    d = duration + 1.0
    # E2 단조 드론(근음·단3도·5도) + 한 옥타브 아래 서브베이스, 살짝 디튠해서 두께감
    tones = [
        (41.20, 0.075),   # E1 서브베이스
        (82.41, 0.060),   # E2 근음
        (82.90, 0.045),   # E2 살짝 디튠 (합창감)
        (98.00, 0.045),   # G2 단3도
        (123.47, 0.040),  # B2 5도
    ]
    inputs = []
    for freq, vol in tones:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={d},volume={vol}"]
    n = len(tones)
    mix = "".join(f"[{i}]" for i in range(n))
    filt = (
        f"{mix}amix=inputs={n}:duration=longest,"
        f"tremolo=f=0.12:d=0.25,"
        f"aecho=0.85:0.9:1400:0.45,"
        f"alimiter=limit=0.7,"
        f"afade=t=in:d=1.4,afade=t=out:st={duration - 1.4:.3f}:d=1.4"
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
        build_ambient_bed(total, audio_path)

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
