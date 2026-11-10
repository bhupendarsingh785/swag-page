#!/usr/bin/env python3
"""
Maya 2 Native se Hindi/Indic voice banao — RunPod / kisi bhi NVIDIA GPU par.

Kya karta hai:
  1. film.json padhta hai: {"shots":[{"say":"...","speaker":"Boy"}, ...]}
  2. har line ka mp3 banata hai (voice + language ke hisaab se)
  3. voices/manifest.json likhta hai — app usi se awaaz utha leti hai

Chalane ka tareeka (GPU par):
  pip install maya3 soundfile
  python maya_voice.py film.json

Bina GPU (sirf test ke liye, quality kam):
  python maya_voice.py film.json --fallback edge

GPU na ho to script saaf bata kar ruk jaati hai — jhooth nahi bolti.
"""
import argparse
import json
import os
import subprocess
import sys

VOICES = {
    "boy": "Ahana",
    "girl": "Ahana",
    "man": "Rohan",
    "narrator": "Ahana",
    "robot": "Rohan",
}
LANG_HINT = {"hi": "hi", "bn": "bn", "ta": "ta", "te": "te", "mr": "mr",
             "gu": "gu", "kn": "kn", "ml": "ml", "pa": "pa", "or": "or"}


def detect_lang(text: str) -> str:
    """Script dekh kar bhasha — Maya ko lang code chahiye hota hai."""
    ranges = [
        (0x0980, 0x09FF, "bn"), (0x0A00, 0x0A7F, "pa"), (0x0A80, 0x0AFF, "gu"),
        (0x0B00, 0x0B7F, "or"), (0x0B80, 0x0BFF, "ta"), (0x0C00, 0x0C7F, "te"),
        (0x0C80, 0x0CFF, "kn"), (0x0D00, 0x0D7F, "ml"), (0x0600, 0x06FF, "ur"),
    ]
    for ch in text:
        cp = ord(ch)
        for lo, hi, code in ranges:
            if lo <= cp <= hi:
                return code if code in LANG_HINT else "hi"
    return "hi"


def gpu_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def synth_maya(lines, outdir, model_id="maya-research/maya2-native"):
    from maya3 import Maya3TTS  # type: ignore
    import soundfile as sf  # type: ignore

    tts = Maya3TTS.from_pretrained(model_id, max_seats=1)
    made = []
    try:
        for i, ln in enumerate(lines):
            text = ln["say"].strip()
            if not text:
                continue
            lang = detect_lang(text)
            voice = VOICES.get(str(ln.get("speaker", "")).lower(), "Ahana")
            audio = tts.generate(text, lang=lang, voice=voice, normalize=True)
            path = os.path.join(outdir, f"line_{i:03d}.wav")
            sf.write(path, audio, 24000)
            made.append({"i": i, "file": path, "lang": lang, "voice": voice,
                         "text": text, "engine": "maya2-native"})
            print(f"[{i}] {lang}/{voice} -> {path}")
    finally:
        tts.close()
    return made


def synth_edge(lines, outdir):
    """Bina GPU ka rasta: edge-tts (free). Quality Maya se kam, par chalta hai."""
    made = []
    voice_map = {"hi": "hi-IN-SwaraNeural", "bn": "bn-IN-TanishaaNeural",
                 "ta": "ta-IN-PallaviNeural", "te": "te-IN-ShrutiNeural",
                 "mr": "mr-IN-AarohiNeural", "gu": "gu-IN-DhwaniNeural",
                 "kn": "kn-IN-SapnaNeural", "ml": "ml-IN-SobhanaNeural"}
    for i, ln in enumerate(lines):
        text = ln["say"].strip()
        if not text:
            continue
        lang = detect_lang(text)
        voice = voice_map.get(lang, voice_map["hi"])
        path = os.path.join(outdir, f"line_{i:03d}.mp3")
        cmd = [sys.executable, "-m", "edge_tts", "--voice", voice,
               "--text", text, "--write-media", path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[{i}] edge-tts fail: {r.stderr.strip()[:120]}")
            continue
        made.append({"i": i, "file": path, "lang": lang, "voice": voice,
                     "text": text, "engine": "edge-tts"})
        print(f"[{i}] {lang}/{voice} -> {path}")
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film", help="film.json (shots with say/speaker)")
    ap.add_argument("--out", default="voices")
    ap.add_argument("--fallback", choices=["edge", "none"], default="none")
    args = ap.parse_args()

    data = json.load(open(args.film, encoding="utf-8"))
    lines = data.get("shots") or data
    os.makedirs(args.out, exist_ok=True)

    made = []
    if gpu_available():
        print("GPU mila — Maya 2 Native se bana raha hoon")
        made = synth_maya(lines, args.out)
    elif args.fallback == "edge":
        print("GPU nahi hai — edge-tts se bana raha hoon (quality kam)")
        made = synth_edge(lines, args.out)
    else:
        print("GPU nahi mila. Do rasta:\n"
              "  1) RunPod par RTX 4090 le kar yahan chalao (approx $0.34/hr)\n"
              "  2) --fallback edge lagao (free, par awaaz utni natural nahi)\n"
              "Kuch bana kar nahi diya — saaf bata raha hoon.")
        return 2

    manifest = os.path.join(args.out, "manifest.json")
    json.dump({"lines": made, "count": len(made)}, open(manifest, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{len(made)} lines bani. manifest: {manifest}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
