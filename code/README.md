# CMSVS

Configurable Multimodal Semantic Validation System for extracting and validating structured information from PDFs and images. The project includes:

- A FastAPI backend for extraction, validation, and config management
- A Streamlit frontend for interactive document upload and review
- A Python pipeline for local CLI and test usage

## Prerequisites

- Python 3.12 or lower
- `pip`
- An NVIDIA NIM API key

Note: the repository’s `.python-version` file is set to `3.12`, so use a Python version less than or equal to that.

## Project Structure

- `streamlit_app/app.py`: Streamlit frontend
- `api/main.py`: FastAPI application entry point
- `src/`: core extraction, OCR, retrieval, and validation pipeline
- `configs/`: sample YAML configurations
- `tests/`: test and end-to-end validation scripts

## Local Setup

1. Clone the repository and move into the project root.

```bash
cd code/
```

2. Create and activate a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies.

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

4. Set the NVIDIA API key in your shell before starting the backend.

```bash
export NVIDIA_API_KEY="nvapi...."
```

Notes:

- The backend reads `NVIDIA_API_KEY` from the environment at startup.
- If you open a fresh terminal, activate the virtual environment again and re-export the variable unless you have added it to your shell profile.

## Running the Application

Start the backend and frontend in separate terminals from the repository root.

### Terminal 1: Streamlit frontend

```bash
source .venv/bin/activate
python3 -m streamlit run streamlit_app/app.py
```

The frontend will usually be available at [http://localhost:8501](http://localhost:8501).

### Terminal 2: FastAPI backend

```bash
source .venv/bin/activate
export NVIDIA_API_KEY="nvapi...."
python3 -m api.main
```

The API will run on [http://localhost:8000](http://localhost:8000), with docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Verifying the Setup

Once the backend is running, confirm it is healthy:

```bash
curl http://localhost:8000/health
```

Expected behavior:

- `status` should return `ok`
- `nvidia_key_set` should be `true`
- `configs_available` should list bundled configs such as `funsd_ner_config` and `healthcare_sbc_config`

In the Streamlit sidebar, you should see the API status change to online.

## Configuration

The Streamlit app talks to the backend using `CMSVS_API_URL`. By default it uses:

```bash
http://localhost:8000
```

If your backend is running elsewhere, set it before launching Streamlit:

```bash
export CMSVS_API_URL="http://localhost:8000"
python3 -m streamlit run streamlit_app/app.py
```

## Using the App

1. Start both services.
2. Open the Streamlit UI in your browser.
3. Select one of the available configurations from the sidebar.
4. Upload a PDF or image document for extraction, or upload a document pair for validation.
5. Review extracted entities, validation results, and any items flagged for human review.

## Hugging Face Space Setup

Do not deploy the `main` branch directly to Hugging Face Spaces. In this repository, `main` includes the top-level `datasets/` folder and other large files, which caused deployment issues on Hugging Face.

Instead, use the separate deployment branch `deploy/hf`:

- `deploy/hf` is an orphan-style deployment branch used only for Hugging Face Spaces
- It moves the contents of `code/` to the repository root on that branch
- It adds a `Dockerfile` and `scripts/start_space.sh` for the Space runtime
- It avoids shipping the large dataset folders that exist on `main`

### Branch Layout

On `deploy/hf`, the Space expects the application files at the repository root, for example:

- `Dockerfile`
- `README.md` with Hugging Face Space metadata
- `streamlit_app/`
- `api/`
- `src/`
- `requirements.txt`

### Deployment Flow

From the repository root:

```bash
git fetch origin
git switch --track deploy/hf origin/deploy/hf
```

Make Hugging Face updates on `deploy/hf`, not on `main`. When application code changes under `code/` on `main`, mirror the relevant changes into the root of `deploy/hf` before pushing that branch to the Space.

### Hugging Face Space Configuration

The deployment branch is configured for a Docker Space:

- SDK: `docker`
- App port: `7860`
- Startup script: `scripts/start_space.sh`

At runtime, the container starts:

- the FastAPI backend on port `8000`
- the Streamlit frontend on port `7860`

### Required Secrets

Add this secret in your Hugging Face Space settings before launching the app:

```bash
NVIDIA_API_KEY=nvapi....
```

Without that secret, backend extraction requests will fail because the API server reads `NVIDIA_API_KEY` from the environment.

## Troubleshooting

- `NVIDIA_API_KEY is not configured on the server`
  Start the backend from a shell where `NVIDIA_API_KEY` has been exported.

- Streamlit shows API offline
  Make sure `python3 -m api.main` is running and reachable at `http://localhost:8000`.

- No configs appear in the sidebar
  Confirm the `configs/` directory contains YAML files and the backend started from the repository root.

- Dependency installation fails around OCR packages
  Recreate the virtual environment and reinstall. OCR dependencies can be platform-sensitive, so use Python 3.12 and install from `requirements.txt` first.

## Development Notes

- The repository includes bundled sample configs in `configs/`.
- The backend enables CORS for local frontend development.
- The API health endpoint is used by the Streamlit sidebar to report backend and key status.
