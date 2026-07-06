import transformers.models.phi3.modeling_phi3 as phi3_mod
import torch

def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)

def apply_directml_safe_rope_patch():
    def patched_rope(q, k, cos, sin, position_ids=None, unsqueeze_dim=1):
        q, k = q.contiguous(), k.contiguous()
        cos, sin = cos.unsqueeze(unsqueeze_dim).contiguous(), sin.unsqueeze(unsqueeze_dim).contiguous()
        q32, k32, cos32, sin32 = q.float(), k.float(), cos.float(), sin.float()
        q_embed = (q32 * cos32) + (_rotate_half(q32) * sin32)
        k_embed = (k32 * cos32) + (_rotate_half(k32) * sin32)
        return q_embed.to(q.dtype), k_embed.to(k.dtype)

    phi3_mod.apply_rotary_pos_emb = patched_rope