#!/usr/bin/env python3
"""
Free natural voice — edge-tts (Microsoft neural) pehle, Google TTS fallback.

Kyun: Google Translate TTS robot jaisi lagti hai. edge-tts ki neural awaaz
(Hindi: Swara / Madhur, Bangla: Tanishaa, Tamil: Pallavi ...) kaafi natural hai —
free, koi key nahi, sirf internet.

Chalao:
  pip install edge-tts
  python tools/voice.py tools/film_sample.json --out voices

Har line ka mp3 + voices/manifest.json banega. App wahi manifest padh sakti hai.
"""
import argparse
import asyncio
import json
import os
import time
import urllib.parse
import urllib.request

# bhasha ke hisaab se voices (edge-tts ke naam)
VOICES = {
    "hi": {"female": "hi-IN-SwaraNeural",   "male": "hi-IN-MadhurNeural"},
    "bn": {"female": "bn-IN-TanishaaNeural", "male": "bn-IN-BashkarNeural"},
    "ta": {"female": "ta-IN-PallaviNeural",  "male": "ta-IN-ValluvarNeural"},
    "te": {"female": "te-IN-ShrutiNeural",   "male": "te-IN-MohanNeural"},
    "mr": {"female": "mr-IN-AarohiNeural",   "male": "mr-IN-ManoharNeural"},
    "gu": {"female": "gu-IN-DhwaniNeural",   "male": "gu-IN-NiranjanNeural"},
    "kn": {"female": "kn-IN-SapnaNeural",    "male": "kn-IN-GaganNeural"},
    "ml": {"female": "ml-IN-SobhanaNeural",  "male": "ml-IN-MidhunNeural"},
    "pa": {"female": "pa-IN-GurleenNeural",  "male": "pa-IN-OjasNeural"},
    "or": {"female": "or-IN-SubhasiniNeural", "male": "or-IN-SukantNeural"},
    "ur": {"female": "ur-IN-GulNeural",      "male": "ur-IN-SalmanNeural"},
}

# character -> (gender, pitch, rate)
CHAR = {
    "boy":      ("male",   "+12Hz", "+6%"),
    "girl":     ("female", "+14Hz", "+4%"),
    "man":      ("male",   "-2Hz",  "+0%"),
    "woman":    ("female", "0Hz",   "+0%"),
    "narrator": ("female", "-4Hz",  "-6%"),
    "robot":    ("male",   "-10Hz", "-4%"),
}

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


def char_of(speaker: str):
    return CHAR.get(str(speaker or "").strip().lower(), CHAR["narrator"])


async def edge_line(text, lang, speaker, path, proxy=None):
    import edge_tts
    gender, pitch, rate = char_of(speaker)
    voice = VOICES.get(lang, VOICES["hi"])[gender]
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=proxy)
    await c.save(path)
    return {"voice": voice, "engine": "edge-tts"}


def google_line(text, lang, path):
    q = urllib.parse.quote(text)
    url = f"https://translate.google.com/translate_tts"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if len(data) < 1500:
        raise ValueError("chhota jawab")
    open(path, "wb").write(data)
    return {"voice": "google-" + lang, "engine": "google-tts"}


async def main_async(args):
    data = json.load(open(args.film, encoding="utf-8"))
    lines = data.get("shots") or data
    os.makedirs(args.out, exist_ok=True)
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    made, failed = [], 0
    for i, ln in enumerate(lines):
        text = (ln.get("say") or "").strip()
        if not text:
            continue
        lang = lang_of(text)
        path = os.path.join(args.out, f"line_{i:03d}.mp3")
        info = None
        try:
            info = await edge_line(text, lang, ln.get("speaker", ""), path, proxy)
        except Exception as e:
            print(f"[{i}] edge fail ({str(e)[:60]}) — google try")
            try:
                info = google_line(text, lang, path)
            except Exception as e2:
                print(f"[{i}] dono fail: {str(e2)[:60]}")
        if info and os.path.exists(path):
            made.append({"i": i, "file": path, "lang": lang, "speaker": ln.get("speaker", ""),
                         "text": text, **info})
            print(f"[{i}] {lang}/{info['voice']} -> {path} ({os.path.getsize(path)//1024} KB)")
        else:
            failed += 1
        time.sleep(0.4)

    manifest = os.path.join(args.out, "manifest.json")
    json.dump({"lines": made, "count": len(made), "failed": failed},
              open(manifest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{len(made)} lines bani, {failed} fail. manifest: {manifest}")
    return 0 if made else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--out", default="voices")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
