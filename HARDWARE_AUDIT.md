# Hardware audit

Captured: 2026-08-05T18:33:51.243118+00:00

- Host: `O-2004251`
- OS: Ubuntu 22.04.5 LTS; kernel `6.6.0-hiveos`
- CPU: AMD Ryzen 9 5950X 16-Core Processor (32 logical CPUs)
- RAM: 125.71 GiB; swap: 0.00 GiB
- Workspace disk: 39.38 GiB total, 12.27 GiB free
- GPU: NVIDIA GeForce RTX 5070 Ti (16303 MiB, compute 12.0)
- NVIDIA driver: 595.80
- Driver-reported CUDA: 13.2
- CUDA toolkit (`nvcc`): not installed
- Python: Python 3.11.10
- PyTorch: 2.5.1+cu124 (build CUDA 12.4)

## Blocking compatibility finding

The installed PyTorch architecture list is `['sm_50', 'sm_60', 'sm_70', 'sm_75', 'sm_80', 'sm_86', 'sm_90']` while the GPU reports compute capability `12.0`. The current build does not contain `sm_120` kernels. No GPU model runtime is approved until an isolated image passes a real inference smoke test and VRAM benchmark.
