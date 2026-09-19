# Remote Video Worker — Oracle Always Free

## Architecture
App → Render API (lightweight) → Oracle worker → FFmpeg / AI → worker media storage → Render API proxy → App.

The worker is intentionally limited to one video job at a time by default so several requests cannot exhaust RAM simultaneously.

## Free worker option
Oracle Cloud's Always Free Ampere A1 compute is the intended target. Oracle documents the A1 Always Free allocation as up to 3,000 OCPU-hours and 18,000 GB-hours per month, subject to account/region capacity. A1 is ARM64, and current PyTorch CPU wheels include Linux aarch64 builds, so the existing Python 3.11 + CPU stack can run on ARM64.

## 1. Create the VM

In Oracle Cloud Console:

1. Compute → Instances → Create instance.
2. Image: Oracle Linux 9 (or a current supported Linux ARM image).
3. Shape → Ampere → VM.Standard.A1.Flex → Always Free eligible.
4. Start with 1 OCPU and 6 GB RAM. If the account's Always Free allowance permits, increase RAM/OCPU later.
5. Assign a public IPv4 address.
6. Generate/download the SSH key pair and keep the private key private.
7. Create the instance.

## 2. Open port 8000

Add an inbound TCP rule for port 8000 from 0.0.0.0/0 in the VM's VCN security list or network security group. The application itself authenticates worker control requests with WORKER_TOKEN; port 8000 is only the transport layer.

## 3. Install Docker and start the worker

Clone this repository on the VM, copy worker.env.example to worker.env, fill the worker URL and AI credentials, then run:

docker compose -f docker-compose.worker.yml up -d --build

Check:

http://YOUR_WORKER_IP:8000/health

The response must show worker_mode: true and worker_max_concurrency: 1.

## 4. Render environment variables

On the Render API service, set:

- VIDEO_WORKER_URL=http://YOUR_WORKER_IP:8000
- VIDEO_WORKER_TOKEN=<the same secret as WORKER_TOKEN on the worker>
- PUBLIC_BASE_URL=<your Render API HTTPS URL>

Leave WORKER_MODE=0 on Render.

After saving, deploy the new commit. The Render API will only dispatch jobs; the heavy video pipeline will run on the worker.

## 5. Storage behavior

The first production-safe milestone uses the worker's persistent VM disk as the video store and the Render API as an HTTPS streaming proxy. The app therefore does not receive a mixed-content HTTP video URL. A later storage adapter can move completed MP4s to object storage without changing the mobile API contract.

## Security

Never commit worker.env. Never put AI keys in GitHub. The worker endpoint rejects requests without the shared worker token. The video endpoint is intended to be reached through the Render API rather than exposing worker URLs to the mobile UI.
