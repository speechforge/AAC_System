#!/usr/bin/env python3
"""Verify the actual CUDA runtime with a tensor operation, not nvidia-smi alone."""
import argparse
import importlib.metadata
import json
import platform


def check(require_cuda: bool = True) -> dict:
    import torch
    info = {"python": platform.python_version(), "torch": torch.__version__,
            "torch_cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available(),
            "packages": {name: importlib.metadata.version(name)
                         for name in ("transformers", "datasets", "sentencepiece", "safetensors")}}
    if require_cuda and not info["cuda_available"]:
        raise RuntimeError("CUDA is unavailable. Install a PyTorch build compatible with this GPU/driver.")
    if info["cuda_available"]:
        info.update(gpu=torch.cuda.get_device_name(0), capability=torch.cuda.get_device_capability(0),
                    vram_gib=round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2),
                    compiled_architectures=torch.cuda.get_arch_list())
        x = torch.randn(64, 64, device="cuda")
        assert torch.isfinite(x @ x.T).all().item()
        torch.cuda.synchronize()
        info["cuda_matmul"] = "passed"
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()
    print(json.dumps(check(not args.allow_cpu), indent=2))
