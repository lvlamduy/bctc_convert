# Hardware audit

Captured: 2026-08-05T19:56:53.587820+00:00

- Host: `O-2004251`
- OS: Ubuntu 22.04.5 LTS; kernel `6.6.0-hiveos`
- CPU: AMD Ryzen 9 5950X 16-Core Processor (32 logical CPUs)
- RAM: 125.71 GiB; swap: 0.00 GiB
- Workspace disk: 39.38 GiB total, 6.70 GiB free
- GPU: NVIDIA GeForce RTX 5070 Ti (16303 MiB, compute 12.0)
- NVIDIA driver: 595.80
- Driver-reported CUDA: 13.2
- CUDA toolkit (`nvcc`): not installed
- Python: Python 3.11.10
- PyTorch: not installed in the control-plane interpreter
- Isolated GPU runtime: PASS — PyTorch 2.12.0+cu130, CUDA 13.0, native sm_120, 122-package exact freeze
- Recorded document-model status: `LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED`

## Compatibility and approval finding

The control-plane environment intentionally has no PyTorch; model dependencies remain isolated from orchestration and validation code. The isolated runtime was revalidated on this host: imports and dependency compatibility passed, the installed freeze exactly matched the tracked freeze, and a real CUDA matrix kernel ran on the detected GPU. This accepts the runtime for logic development; production model approval remains blocked until frozen multi-institution, scan/distortion, cross-page, and holdout accuracy gates pass.
