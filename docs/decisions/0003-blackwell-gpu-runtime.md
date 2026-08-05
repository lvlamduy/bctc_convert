# Decision 0003: isolate and replace the incompatible GPU runtime

Status: runtime accepted for logic development; model is not production approved

The RTX 5070 Ti reports compute capability 12.0 (`sm_120`). The preinstalled PyTorch 2.5.1+cu124 exposes architectures only through `sm_90`, and its own runtime warning says this GPU is incompatible.

NVIDIA documents that CUDA 12.8 first added compiler support for `SM_120`: <https://docs.nvidia.com/cuda/archive/12.8.0/cuda-features-archive/index.html>. PyTorch's official 2.12 release guidance recommends CUDA 13.0+ wheels for Blackwell and requires Linux driver 580.65.06 or later: <https://pytorch.org/blog/pytorch-2-12-release-blog/>. This host's 595.80 driver satisfies that stated driver floor.

The isolated runtime is Python 3.11 + PyTorch 2.12.0 CUDA 13.0 + TorchVision 0.27.0. `scripts/diagnostics/gpu_model_runtime_smoke.py` successfully imported the frozen document stack, allocated, multiplied, synchronized, and reported a native `sm_120` path on the target GPU. The base runtime is accepted for model experiments.

PaddleOCR-VL-1.6 plus PP-DocLayoutV3 completed E-0007 with 3,239 MiB peak total GPU memory. Its numeric cells were exact against the independent native reader on this one development page, but two labels disagreed and one wrapped row required structural fusion. Therefore neither the model nor any generated table is accepted as standalone truth.

Do not replace the host/base PyTorch installation. Keep `.gpu-venv` isolated, enforce disk preflight, pin model revisions/hashes, and require multi-institution frozen evaluation before production approval.
