# Email Workload Assistant

Python/FastAPI + React/TypeScript/Vite mailbox workload assistant using Ollama for AI decision support and natural-language Q&A.

## Requirements

- Python 3.11+
- Node.js 20+
- Ollama
- The configured Ollama model, `qwen2.5:3b` by default

No external API key is required. The application uses a locally running Ollama instance.

## LLM setup

In a Powershell Terminal, run the following command to download the Ollama model:

```
ollama pull qwen2.5:3b
```

In a Powershell Terminal, run the Ollama model with:

```
ollama run qwen2.5:3b
```

## Backend setup

Run the following commands inside of a Bash terminal

Install the Python dependencies:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate # windows
source .venv/bin/activate # Linux or MacOS
python -m pip install -r requirements.txt
```

To then run the backend:

```bash
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Frontend setup

Run the following in another powershell terminal:

```
cd frontend
npm install
npm run dev
```

## Testing

The backend uses `pytest` and `pytest-cov`.

Run the full test suite:

```bash
cd backend
PYTHONPATH=. pytest -q
```

```bash
cd backend
PYTHONPATH=. pytest --cov=app --cov-report=term-missing --cov-report=html
```
