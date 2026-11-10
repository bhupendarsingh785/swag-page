#!/usr/bin/env python3
"""
CPU par chhota LLM — bina GPU, bina API key (llama.cpp ke raste).

GitHub Actions ke free runner par chalta hai, ya apne laptop par:
    pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
    python tools/cpu_llm.py "ek chhoti kahani likho jungle ke baare me"

Model pehli baar download hota hai (~400MB), phir cache me rehta hai.
Sach: 1.5B model chhota hai — chhoti lines theek, lambi kahani kamzor. 0.5B se behtar.
"""
import os
import sys

MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_DIR = os.environ.get("MODEL_DIR", "models")


def get_model_path() -> str:
    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, MODEL_FILE)
    if os.path.exists(path):
        return path
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE, local_dir=MODEL_DIR)


def main():
    prompt = " ".join(sys.argv[1:]).strip() or "Namaste! Ek line me batao tum kaun ho."
    try:
        from llama_cpp import Llama
    except ImportError:
        print("llama-cpp-python nahi hai. Install:\n"
              "  pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu")
        return 2

    path = get_model_path()
    print(f"model: {path}")
    llm = Llama(model_path=path, n_ctx=1024, n_threads=os.cpu_count() or 2, verbose=False)
    out = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": "Tum ek chhote madadgar ho. Hinglish me chhota jawab do."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=180,
        temperature=0.7,
    )
    text = out["choices"][0]["message"]["content"].strip()
    print("\n--- jawab ---")
    print(text)
    usage = out.get("usage", {})
    print(f"\n(tokens: {usage.get('total_tokens', '?')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
