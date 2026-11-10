"""
Modal par free GPU se Hindi/Indic awaaz — VoxCPM2 (Apache-2.0).

Modal Starter plan har mahine $30 compute free deta hai (card chahiye).
L4 GPU (24GB) par yeh lagbhag 37 ghante banta hai — matlab mahine me kai filmein.

Setup (ek baar):
    pip install modal
    modal token new
    modal deploy tools/modal_tts.py

Test:
    curl -X POST https://<tumhara-url>.modal.run \
         -H "Content-Type: application/json" \
         -d '{"text":"नमस्ते, मैं जंगल से डरता हूँ","lang":"hi"}' --output line.wav

Dhyan:
- Pehli call par model download hota hai (~8GB) — 2-3 minute, woh bhi credit me ginta hai.
- `scaledown_window` chhota rakha hai, warna idle time bhi paisa khata hai.
- Yeh script GPU par chal kar TEST NAHI hui hai (mere paas GPU nahi). Syntax check hua hai.
  Pehli call par error aaye to poora message bhejna — main theek kar dungi.
"""
import io
import json

import modal

app = modal.App("seetal-tts")

# model + code ek hi image me — har cold start par pip nahi
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install("torch==2.6.0", "soundfile", "numpy", "fastapi[standard]")
    .pip_install("voxcpm")
)

MODEL_ID = "openbmb/VoxCPM2"


@app.cls(
    image=image,
    gpu="L4",              # 24GB — VoxCPM2 (~8GB) aur Maya (~12GB) dono ke liye kaafi
    scaledown_window=120,  # 2 min idle ke baad band — credit bachta hai
    timeout=600,
)
class TTS:
    @modal.enter()
    def load(self):
        from voxcpm import VoxCPM
        self.model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False)

    @modal.method()
    def say(self, text: str, lang: str = "hi", seed: int = 42) -> bytes:
        import soundfile as sf
        wav = self.model.generate(text=text, cfg_value=2.0, inference_timesteps=10, seed=seed)
        buf = io.BytesIO()
        sf.write(buf, wav, self.model.tts_model.sample_rate, format="WAV")
        return buf.getvalue()


@app.function(image=image, gpu="L4", scaledown_window=120, timeout=600)
def say_batch(lines: list[dict]) -> list[dict]:
    """Ek call me poori film ki lines — har line ka WAV base64 me."""
    import base64
    from voxcpm import VoxCPM
    import soundfile as sf

    model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False)
    out = []
    for i, ln in enumerate(lines):
        text = (ln.get("say") or "").strip()
        if not text:
            continue
        wav = model.generate(text=text, cfg_value=2.0, inference_timesteps=10, seed=42 + i)
        buf = io.BytesIO()
        sf.write(buf, wav, model.tts_model.sample_rate, format="WAV")
        out.append({"i": i, "wav_b64": base64.b64encode(buf.getvalue()).decode(),
                    "text": text, "speaker": ln.get("speaker", "")})
    return out


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def speak(item: dict):
    """HTTP endpoint — text bhejo, WAV wapas."""
    from fastapi import Response
    text = (item.get("text") or "").strip()
    if not text:
        return Response(content=json.dumps({"error": "text khaali hai"}),
                        media_type="application/json", status_code=400)
    wav = TTS().say.remote(text, item.get("lang", "hi"))
    return Response(content=wav, media_type="audio/wav")


# local test (modal run tools/modal_tts.py)
@app.local_entrypoint()
def main():
    data = say_batch.remote([{"say": "नमस्ते, मैं जंगल से डरता हूँ", "speaker": "Boy"}])
    print("lines:", len(data), "| pehli line bytes:", len(data[0]["wav_b64"]) if data else 0)
