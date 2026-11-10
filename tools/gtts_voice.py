#!/usr/bin/env python3
"""
Free Hindi/Indic voice — Google TTS endpoint se (koi key nahi, koi GPU nahi).

Kaam:
  film.json -> har line ka mp3 -> voices/manifest.json

Chalao:
  python tools/gtts_voice.py tools/film_sample.json --out voices

Dhyan:
- Yeh endpoint Google Translate ka public TTS hai: free, par bhasha ke hisaab se
  sirf ek hi awaaz deta hai. Character ke hisaab se pitch/rate app me lagta hai.
- Bhasha script se pehchani jaati hai (Devanagari -> hi, Bangla -> bn, ...).
- Badi film ke liye lines ko 200 characters se chhota rakho (endpoint limit).
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

RANGES = [
    (0x0980, 0x09FF, "bn"), (0x0A00, 0x0A7F, "pa"), (0x0A80, 0x0AFF, "gu"),
    (0x0B00, 0x0B7F, "or"), (0x0B80, 0x0BFF, "ta"), (0x0C00, 0x0C7F, "te"),
    (0x0C80, 0x0CFF, "kn"), (0x0D00, 0x0D7F, "ml"), (0x0600, 0x06FF, "ur"),
]


def lang_of(text: str) -> str:
    for ch in text:
        cp = ord(ch)
        for lo, hi, code in RANGES:
            if lo <= cp <= hi:
                return code
    return "hi"


def tts_url(text: str, lang: str) -> str:
    q = urllib.parse.quote(text)
    return f"https://translate.google.com/translate_tts"


def fetch_mp3(text: str, lang: str, path: str, tries: int = 3) -> bool:
    url = tts_url(text, lang)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 1500:
                raise ValueError(f"chhota jawab ({len(data)} bytes)")
            with open(path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"   try {attempt+1} fail: {e}")
            time.sleep(2 + attempt * 2)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--out", default="voices")
    args = ap.parse_args()

    data = json.load(open(args.film, encoding="utf-8"))
    lines = data.get("shots") or data
    os.makedirs(args.out, exist_ok=True)

    made, failed = [], 0
    for i, ln in enumerate(lines):
        text = (ln.get("say") or "").strip()
        if not text:
            continue
        if len(text) > 200:
            print(f"[{i}] line lambi hai ({len(text)} chars) — chhoti karo, skip")
            failed += 1
            continue
        lang = lang_of(text)
        path = os.path.join(args.out, f"line_{i:03d}.mp3")
        if fetch_mp3(text, lang, path):
            made.append({"i": i, "file": path, "lang": lang,
                         "speaker": ln.get("speaker", ""), "text": text,
                         "engine": "google-tts"})
            print(f"[{i}] {lang} -> {path} ({os.path.getsize(path)//1024} KB)")
        else:
            failed += 1
            print(f"[{i}] FAIL — {text[:40]}")
        time.sleep(0.8)   # endpoint ko saans lene do

    manifest = os.path.join(args.out, "manifest.json")
    json.dump({"lines": made, "count": len(made), "failed": failed},
              open(manifest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{len(made)} lines bani, {failed} fail. manifest: {manifest}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
