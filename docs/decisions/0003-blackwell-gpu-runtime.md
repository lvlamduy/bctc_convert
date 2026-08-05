# Decision 0003: isolate and replace the incompatible GPU runtime

Status: accepted; target environment not installed while source upload consumes workspace disk

The RTX 5070 Ti reports compute capability 12.0 (`sm_120`). The preinstalled PyTorch 2.5.1+cu124 exposes architectures only through `sm_90`, and its own runtime warning says this GPU is incompatible.

NVIDIA documents that CUDA 12.8 first added compiler support for `SM_120`: <https://docs.nvidia.com/cuda/archive/12.8.0/cuda-features-archive/index.html>. PyTorch's official 2.12 release guidance recommends CUDA 13.0+ wheels for Blackwell and requires Linux driver 580.65.06 or later: <https://pytorch.org/blog/pytorch-2-12-release-blog/>. This host's 595.80 driver satisfies that stated driver floor.

The candidate isolated runtime is therefore Python 3.11 + PyTorch 2.12.0 CUDA 13.0. It is not approved merely by installation: `scripts/diagnostics/gpu_smoke.py` must successfully allocate, multiply, synchronize, and report an architecture path for capability 12.0. Each OCR/model service must then pass its own inference and VRAM benchmark.

Do not replace the host/base PyTorch installation. Create `.gpu-venv` only after the PDF upload finishes and disk capacity is re-audited.
