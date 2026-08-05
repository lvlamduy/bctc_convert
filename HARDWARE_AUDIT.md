# Hardware audit

Captured: 2026-08-05T19:07:09.709965+00:00

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
- PyTorch: not installed in the control-plane interpreter

## Blocking compatibility finding

The control-plane environment intentionally has no PyTorch. The separately observed incompatible host build and the required isolated GPU benchmark are recorded in `docs/environment/SOFTWARE_INVENTORY.md`. No GPU model runtime is approved until an isolated image passes a real inference smoke test and VRAM benchmark.
