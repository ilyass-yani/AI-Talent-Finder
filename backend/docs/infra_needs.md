# Infrastructure & Security Checklist

Essentials to run production finetuning, FAISS and scraping safely:

- GPU nodes (NVIDIA) with CUDA; recommended: A10 / A100 / H100 depending on scale.
- Disk: >= 200GB for datasets and model artifacts.
- Secrets manager for HF tokens and scraper credentials.
- Proxies & IP rotation for scraping; logging and rate-limits.
- CI: do not run GPU finetuning in shared CI; use dedicated GPU runners.
- Legal review before scraping LinkedIn (ToS compliance).

Recommended services:

- Use cloud-managed GPUs (GCP, AWS, Azure) or dedicated on-prem machines.
- Use S3-compatible storage for artifacts and FAISS index backups.
