from __future__ import annotations
import os
import time
import requests
import subprocess
import shutil
from pathlib import Path


class VideoProcessor:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("ASSEMBLYAI_API_KEY")

    def _transcribe(self, video_path: Path) -> list[dict]:
        if not self._api_key:
            return []
        with open(video_path, "rb") as f:
            r = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": self._api_key},
                data=f, timeout=120,
            )
        r.raise_for_status()
        upload_url = r.json()["upload_url"]
        r = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": self._api_key, "content-type": "application/json"},
            json={"audio_url": upload_url, "language_code": "ru"},
            timeout=30,
        )
        r.raise_for_status()
        transcript_id = r.json()["id"]
        for _ in range(60):
            time.sleep(5)
            r = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"authorization": self._api_key}, timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data["status"] == "completed":
                return data.get("words", [])
            if data["status"] == "error":
                print(f"[VideoProcessor] error: {data.get('error')}")
                return []
        return []

    def _ms_to_srt(self, ms: int) -> str:
        h = ms // 3600000
        m = (ms % 3600000) // 60000
        s = (ms % 60000) // 1000
        ms = ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _make_srt(self, words: list[dict], max_chars: int = 40) -> str:
        if not words:
            return ""
        srt = []
        idx = 1
        chunk: list[str] = []
        start_ms = words[0]["start"]
        for i, w in enumerate(words):
            chunk.append(w["text"])
            if len(" ".join(chunk)) >= max_chars or i == len(words) - 1:
                end_ms = w["end"]
                srt.append(f"{idx}\n{self._ms_to_srt(start_ms)} --> {self._ms_to_srt(end_ms)}\n{' '.join(chunk)}\n")
                idx += 1
                chunk = []
                if i + 1 < len(words):
                    start_ms = words[i + 1]["start"]
        return "\n".join(srt)

    def add_subtitles(self, video_path: Path, output_path: Path) -> Path:
        print(f"[VideoProcessor] transcribing {video_path.name}...")
        words = self._transcribe(video_path)
        if not words:
            print("[VideoProcessor] no words, copying original")
            shutil.copy(video_path, output_path)
            return output_path
        srt_content = self._make_srt(words)
        srt_path = video_path.with_suffix(".srt")
        srt_path.write_text(srt_content, encoding="utf-8")
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"subtitles={srt_path}:force_style='FontSize=18,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Bold=1'",
            "-c:a", "copy", str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[VideoProcessor] FFmpeg error: {result.stderr[-300:]}")
            shutil.copy(video_path, output_path)
        srt_path.unlink(missing_ok=True)
        return output_path
