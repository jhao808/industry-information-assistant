# Industry Information Assistant

**English** | [简体中文](README.zh-CN.md)

An AI-powered industry research assistant that combines multi-agent workflows, web search, knowledge graphs, data visualization, checkpoint recovery, and structured report generation.

## Highlights

- Multi-agent research workflow covering planning, retrieval, analysis, writing, and quality review
- Real-time research progress, reasoning summaries, and search results delivered through SSE
- PostgreSQL checkpoints for persistence and recovery of interrupted research tasks
- Search sources, knowledge graphs, analytical charts, chapter drafts, and final reports in one interface
- General chat with conversation history and contextual memory
- PostgreSQL, Redis, Milvus, and Elasticsearch infrastructure

## Research Workflow

```text
User query → Research planning → Information retrieval → Data analysis
                                                        ↓
Final report ← Quality review ← Report writing ←────────┘
                   ↓
          Supplementary research and revision
```

Each research phase is persisted as a checkpoint. When a task fails, users can resume from the unfinished phase while reusing the existing outline, facts, charts, and chapter drafts.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite, Ant Design, ECharts, Valtio |
| Backend | FastAPI, Python, SQLAlchemy, SSE |
| AI workflow | Multi-agent research graph, DeepSeek, Qwen |
| Search and retrieval | Bocha Search, Milvus, Elasticsearch |
| Persistence | PostgreSQL, Redis |
| Deployment | Docker Compose |

## Requirements

| Dependency | Recommended version | Purpose |
|---|---:|---|
| Docker | 20.0+ | PostgreSQL, Redis, Milvus, Elasticsearch, MinIO, and etcd |
| Python | 3.10+ | Backend service |
| Node.js | 18+ | Frontend development and build |

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/jhao808/industry-information-assistant.git
cd industry-information-assistant
```

### 2. Start infrastructure services

```bash
chmod +x start-services.sh
./start-services.sh start
```

Alternatively:

```bash
docker compose up -d
```

Check the service status:

```bash
./start-services.sh status
# or
docker compose ps
```

Default local services:

| Service | Address |
|---|---|
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| Milvus | `localhost:19530` |
| Elasticsearch | `localhost:1200` |
| MinIO Console | `localhost:9001` |

The credentials in Docker Compose are intended for local development only. Change them before deploying the project publicly.

### 3. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and provide at least:

```env
DASHSCOPE_API_KEY=your-dashscope-api-key
BOCHA_API_KEY=your-bocha-api-key
JWT_SECRET_KEY=generate-a-long-random-secret
```

The default model configuration is:

```env
LLM_MAIN_MODEL=deepseek-v4-pro-0813
LLM_FAST_MODEL=qwen3.8-flash
LLM_REVIEW_MODEL=deepseek-v4-pro-0813
```

Model availability and names depend on your Alibaba Cloud Bailian workspace. See [CONFIGURATION.md](CONFIGURATION.md) for configuration precedence and optional integrations.

Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `backend/.env` or any production credentials.

### 4. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/app_main.py
```

The backend runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

### 5. Start the frontend

In another terminal:

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Open `http://localhost:5183/login`.

## Project Structure

```text
industry-information-assistant/
├── backend/
│   ├── app/
│   │   ├── config/                 # Environment and model configuration
│   │   ├── core/                   # Database, Redis, and security
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── router/                 # FastAPI routes
│   │   ├── service/
│   │   │   └── deep_research_v2/   # Research graph and agents
│   │   └── app_main.py             # Backend entry point
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── store/
│   └── package.json
├── docker/
├── docker-compose.yml
└── start-services.sh
```

## Checkpoint Recovery

Research state is stored in PostgreSQL by session ID. The checkpoint contains the workflow phase, outline, extracted facts, charts, chapter drafts, final report, UI state, and quality-review result.

A failed or paused task displays a **Continue Research** action. Recovery skips completed phases and resumes from the first unfinished phase. Recovery currently operates at phase level; an interruption in the middle of a search phase may repeat some searches from that phase.

## Quality Review

The quality-review agent validates the generated report and returns a structured score and issue list. The workflow performs up to three review rounds, with at most two supplementary research or revision rounds between them. It stops early when the report passes review.

If the maximum review count is reached, the current report is preserved even when its score remains below the configured threshold. The UI should therefore be treated as a research aid rather than an automatic guarantee of factual accuracy.

## Tests and Build

Backend tests:

```bash
cd backend
PYTHONPATH=app .venv/bin/python -m unittest discover -s tests -v
```

Python compilation check:

```bash
cd backend
PYTHONPATH=app .venv/bin/python -m compileall -q app tests
```

Frontend production build:

```bash
cd frontend
npm run build
```

Docker Compose validation:

```bash
docker compose config
```

## Current Limitations

- Deep research is primarily a single-query workflow. Persistent, report-aware multi-turn research is planned.
- Recovery works at workflow-phase level; exact per-request search recovery is not implemented.
- The global search budget and per-section search limit are not fully connected to every recursive search path, so complex tasks may create many search calls.
- Reaching the maximum review count ends the workflow even when the final quality score remains below the threshold.
- LLM and search calls require valid third-party credentials, model access, and sufficient quota.

## Security Notes

- Real `.env` files, local databases, logs, dependency folders, generated reports, and build artifacts are excluded by `.gitignore`.
- Frontend `VITE_` variables are public at build time and must never contain private API keys.
- Replace all development passwords and generate a unique `JWT_SECRET_KEY` before deployment.
- Review generated reports and citations before using them for professional or high-stakes decisions.

## Documentation

- [中文说明](README.zh-CN.md)
- [Configuration guide](CONFIGURATION.md)
- [Backend notes](backend/README.md)
