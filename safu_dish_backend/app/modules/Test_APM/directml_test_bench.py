# ============================================================
# DISH-CHAT v2.9 — StreamBoost (Phi 3.5 + DML + Autotune Compile)
# ============================================================
import os
import sys
import time

base = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(base, "local_deps", "torch_directml"))
    
try:
    import torch
    import torch_directml
    from transformers import AutoTokenizer, AutoModelForCausalLM
except ImportError:
    raise SystemExit("❌ torch-directml not installed: pip install torch-directml")

# === PRECISION BOOST ===
torch.set_float32_matmul_precision("medium")  # improves performance on DML for matmuls

# === CONFIG ===
MODEL_PATH     = r"F:\SAFU DISH\safu_dish_backend\dev\Phi-3.5-mini-instruct"
TARGET_DEVICE  = 1
MAX_NEW        = 128
WARM_PROMPT    = "Hello"
USE_COMPILE    = True

# === RoPE PATCH FOR DML ===
import transformers.models.phi3.modeling_phi3 as phi3_mod

def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)

def apply_rotary_pos_emb_dml_safe(q, k, cos, sin, position_ids=None, unsqueeze_dim=1):
    q, k = q.contiguous(), k.contiguous()
    cos, sin = cos.unsqueeze(unsqueeze_dim).contiguous(), sin.unsqueeze(unsqueeze_dim).contiguous()
    q32, k32, cos32, sin32 = q.float(), k.float(), cos.float(), sin.float()
    q_embed = (q32 * cos32) + (_rotate_half(q32) * sin32)
    k_embed = (k32 * cos32) + (_rotate_half(k32) * sin32)
    return q_embed.to(q.dtype), k_embed.to(k.dtype)

phi3_mod.apply_rotary_pos_emb = apply_rotary_pos_emb_dml_safe

# === LOAD MODEL ===
def load_phi3_dml_safe():
    dml_device = torch_directml.device(TARGET_DEVICE)
    print(f"🎯 Using DirectML device → {torch_directml.device_name(TARGET_DEVICE)}")

    print("📦 Loading Phi-3.5 Mini in float16 …")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        dtype=torch.float16,
        attn_implementation="eager",  # disables Flash-Attn
    )
    model.to(dml_device)
    model.eval()

    if USE_COMPILE:
        print("⚡ Applying Torch 2.0 compile optimization …")
        model = torch.compile(model, backend="inductor", mode="max-autotune", dynamic=True)

    # === Tokenizer fix for pad/eos confusion ===
    tok = AutoTokenizer.from_pretrained(MODEL_PATH)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    tok.truncation_side = "left"
    print(f"🧠 Tokenizer pad_token set to eos_token → id {tok.pad_token_id}")

    return model, tok, dml_device

# === STREAM GENERATION ===
@torch.no_grad()
def fast_stream_generate(model, tok, device, prompt: str):
    inputs = tok(prompt, return_tensors="pt", padding=True).to(device)
    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]
    input_len = input_ids.shape[1]

    start = time.perf_counter()

    output = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        pad_token_id=tok.pad_token_id,
        max_new_tokens=MAX_NEW,
        do_sample=True,
        use_cache=True,
        temperature=0.8,
        top_k=30,
        top_p=0.92,
    )

    total = time.perf_counter() - start
    tokens_generated = output.shape[1] - input_len

    reply = tok.batch_decode(output[:, input_len:], skip_special_tokens=True)[0]

    print(f"\n[REPLY] {reply.strip()}")
    print(f"[GEN] {tokens_generated} tokens in {total:.2f}s → {tokens_generated/max(total,1e-6):.2f} tok/s\n")

# === CHAT LOOP ===
def chat(model, tok, device):
    print("\n[CHAT] Type 'exit' to quit.\n")

    # Warm-up pass
    _ = tok(WARM_PROMPT, return_tensors="pt", padding=True).to(device)

    while True:
        prompt = input("You: ").strip()
        if prompt.lower() in {"exit", "quit"}:
            break
        fast_stream_generate(model, tok, device, prompt)

# === MAIN ===
if __name__ == "__main__":
    model, tok, device = load_phi3_dml_safe()
    chat(model, tok, device)
