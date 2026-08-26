# Anchor Maintainer Release & Deployment Pipeline Guide

This guide details the step-by-step maintainer pipeline to package, build, and publish **Anchor** to PyPI, Docker Hub, and Vercel.

---

## Pre-Flight Checklist: Quality Gate Verification

Before building or publishing any release artifacts, execute the full quality gate suite locally:

```bash
# 1. Check code formatting & linting
uv run ruff check .
uv run ruff format --check .

# 2. Run strict type checking (0 errors across 124 source files)
uv run mypy --strict anchor/

# 3. Run full test suite (228+ passed tests)
uv run pytest -q
```

---

## Phase 1: Build & Publish PyPI Package (`anchor-runtime`)

Publish the Python SDK interface (`@anchor.tool`, `@anchor.agent`, `anchor.run`, `StepContext`, `ToolCall`, `Done`) to PyPI:

```bash
# 1. Clean previous build artifacts
rm -rf dist/ build/ *.egg-info

# 2. Build sdist and wheel packages
python -m build

# 3. Inspect wheel contents (Ensure demo-site/ and tests/ are EXCLUDED)
tar -tf dist/anchor_runtime-0.1.0.tar.gz

# 4. Upload build artifacts to PyPI (Free)
twine upload dist/*
```

---

## Phase 2: Build & Push Docker Hub Container Images

Build and publish the pre-packaged Docker containers (`anchor-api` and `anchor-worker`) to Docker Hub:

```bash
# 1. Log into your free Docker Hub account
docker login

# 2. Build API & Web Console container image
docker build -f ops/docker/Dockerfile.api -t adityaxnema/anchor-api:v0.1.0 -t adityaxnema/anchor-api:latest .

# 3. Build Worker container image
docker build -f ops/docker/Dockerfile.worker -t adityaxnema/anchor-worker:v0.1.0 -t adityaxnema/anchor-worker:latest .

# 4. Push images to Docker Hub (Free)
docker push adityaxnema/anchor-api:v0.1.0
docker push adityaxnema/anchor-api:latest
docker push adityaxnema/anchor-worker:v0.1.0
docker push adityaxnema/anchor-worker:latest
```

---

## Phase 3: Deploy Showcase Marketing Site (`demo-site`) to Vercel

Deploy your private showcase marketing site (`C:\Users\adity\OneDrive\Desktop\Apps\CS\Anchor\demo-site`) to Vercel:

```bash
# 1. Navigate to demo-site folder
cd demo-site

# 2. Deploy to production on Vercel (Free Hobby Tier)
vercel --prod
```

---

## Phase 4: Post-Release End-to-End Sanity Test

Test the complete end-user experience from a clean, empty directory:

```bash
# 1. Create a fresh temporary directory
mkdir ~/test-anchor-release && cd ~/test-anchor-release

# 2. Install published package from PyPI
pip install anchor-runtime

# 3. Generate docker-compose.yml and app.py template
anchor init

# 4. Start pre-built Docker containers from Docker Hub
docker compose up -d

# 5. Execute test agent workflow
python app.py

# 6. Verify Operator Console
# Open http://localhost:3000 in browser
```
