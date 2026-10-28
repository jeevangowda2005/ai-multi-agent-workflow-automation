# AI Multi-Agent Workflow Automation Platform

A production-style full-stack platform for building, orchestrating, and monitoring intelligent multi-agent workflows powered by **Google Gemini** and **LangGraph**.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Multi-Agent Platform                              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    React 18 + Vite 6 (SPA)                          │   │
│  │  Dashboard │ Workflows │ Agent Workspace │ Executions │ Reports      │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                             │ REST + WebSocket (/api, ws://)                │
│  ┌──────────────────────────▼───────────────────────────────────────────┐   │
│  │                    FastAPI (Python 3.11+)                            │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │              LangGraph Orchestration Layer                   │    │   │
│  │  │                                                             │    │   │
│  │  │  Task Analyzer  →  Agent Router  →  Specialized Agents      │    │   │
│  │  │                       │                                     │    │   │
│  │  │              ┌────────┼────────┐                            │    │   │
│  │  │           Research  Content  Data   Reporting               │    │   │
│  │  │           Agent     Agent    Agent  Agent                   │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  Execution Engine (async)  │  WebSocket Manager  │  Analytics       │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                             │                                               │
│  ┌──────────────────────────▼───────────────────────────────────────────┐   │
│  │              PostgreSQL 15 (via SQLAlchemy 2 + Alembic)              │   │
│  │  workflows │ tasks │ executions │ task_executions │ reports           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              Google Gemini API (gemini-2.0-flash)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer      | Technology                                               |
|------------|----------------------------------------------------------|
| Frontend   | React 18 · Vite 6 · TailwindCSS 3 · React Flow          |
| Backend    | Python 3.11+ · FastAPI · Uvicorn · LangGraph             |
| AI         | Google Gemini API (`google-genai`) · LangGraph           |
| Database   | PostgreSQL 15+ · SQLAlchemy 2 · Alembic                  |
| PDF        | ReportLab                                                |
| Docker     | Docker Compose (PostgreSQL + FastAPI + nginx)             |

---

## Project Structure

```
ai-multi-agent-workflow-automation/
├── docker-compose.yml              # Docker Compose (db + backend + frontend)
├── .gitignore
├── README.md
│
├── backend/
│   ├── Dockerfile                  # Python 3.12-slim, Alembic + Uvicorn
│   ├── .env.example                # Safe env template (no real secrets)
│   ├── requirements.txt
│   ├── main.py                     # Uvicorn entry point
│   ├── alembic.ini
│   ├── alembic/versions/           # Database migration history
│   ├── app/
│   │   ├── main.py                 # FastAPI factory, CORS, middleware
│   │   ├── core/
│   │   │   └── config.py           # Pydantic-settings (reads .env)
│   │   ├── api/
│   │   │   ├── router.py           # Registers all route modules
│   │   │   └── routes/
│   │   │       ├── health.py       # GET /api/health
│   │   │       ├── workflows.py    # Workflow & Task CRUD + Templates
│   │   │       ├── ai.py           # POST /api/ai/analyze
│   │   │       ├── agents.py       # POST /api/agents/execute
│   │   │       ├── executions.py   # Execution history + WebSocket
│   │   │       ├── analytics.py    # Analytics overview/trends/agents
│   │   │       └── reports.py      # AI report generation + PDF
│   │   ├── agents/
│   │   │   ├── langgraph_agent.py  # Task Analysis Agent (LangGraph)
│   │   │   └── specialized/
│   │   │       ├── research_agent.py
│   │   │       ├── content_agent.py
│   │   │       ├── data_agent.py
│   │   │       ├── reporting_agent.py
│   │   │       └── agent_router.py # Intelligent routing
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── execution_engine.py # Async workflow execution pipeline
│   │   │   ├── workflow_service.py # CRUD + templates + cycle detection
│   │   │   ├── analytics_service.py
│   │   │   ├── report_service.py
│   │   │   ├── pdf_service.py      # ReportLab PDF generation
│   │   │   └── gemini_service.py   # Google Gemini API wrapper
│   │   ├── core/
│   │   │   └── websockets.py       # WebSocket execution manager
│   │   └── db/
│   │       ├── base.py
│   │       └── session.py
│   └── tests/
│       ├── test_ai_agent.py
│       ├── test_agents.py
│       ├── test_execution_engine.py
│       ├── test_analytics_and_reports.py
│       ├── test_step7_workflow_builder.py
│       └── test_step8_security.py
│
└── frontend/
    ├── Dockerfile                  # Multi-stage: Node 20 build → nginx serve
    ├── nginx.conf                  # SPA fallback, API proxy, security headers
    ├── vite.config.js
    ├── tailwind.config.js
    ├── package.json
    └── src/
        ├── App.jsx                 # Route definitions
        ├── pages/
        │   ├── Dashboard.jsx       # Analytics dashboard + SVG charts
        │   ├── Workflows.jsx       # Workflow list + template gallery
        │   ├── WorkflowDetails.jsx # Visual builder + table view toggle
        │   ├── AiAnalyzer.jsx      # Task analysis UI
        │   ├── AgentWorkspace.jsx  # Multi-agent execution UI
        │   ├── ExecutionDashboard.jsx # Real-time WebSocket monitoring
        │   └── Reports.jsx         # AI report generation + PDF download
        ├── components/
        │   ├── layout/
        │   │   └── Sidebar.jsx
        │   ├── workflow/
        │   │   └── VisualWorkflowBuilder.jsx  # React Flow canvas
        │   └── ui/                 # StatCard, StatusBadge, Modal, etc.
        └── services/
            └── api.js              # Axios API client
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Google Gemini API key ([get one here](https://aistudio.google.com/))

### 1. Clone & configure

```bash
git clone <repo-url>
cd ai-multi-agent-workflow-automation

# Configure backend
cp backend/.env.example backend/.env
# Edit backend/.env and set GEMINI_API_KEY and DATABASE_URL
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API is available at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Frontend is available at: `http://localhost:5173`

---

## Docker Deployment

### Prerequisites
- Docker Desktop or Docker Engine + Docker Compose v2

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set at minimum:
#   GEMINI_API_KEY=<your key>
#   SECRET_KEY=<strong random string>
#   ALLOWED_ORIGINS=http://localhost  # or your production domain
```

### 2. Build and start all services

```bash
docker-compose up --build
```

This starts:
- **PostgreSQL 15** on port 5432
- **FastAPI backend** on port 8000 (auto-runs Alembic migrations)
- **React frontend** (nginx) on port 80

### 3. Verify

```bash
# Health check
curl http://localhost:8000/api/health
# → {"status": "healthy"}

# Frontend
open http://localhost
```

### 4. Stop services

```bash
docker-compose down           # stop containers
docker-compose down -v        # stop and remove database volume
```

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/ai/health` | AI configuration status |
| `POST` | `/api/ai/analyze` | Analyze a task with LangGraph + Gemini |
| `GET` | `/api/workflows` | List workflows |
| `POST` | `/api/workflows` | Create workflow |
| `GET` | `/api/workflows/{id}` | Get workflow with tasks |
| `PUT` | `/api/workflows/{id}` | Update workflow |
| `DELETE` | `/api/workflows/{id}` | Delete workflow |
| `POST` | `/api/workflows/{id}/tasks` | Add task to workflow |
| `PUT` | `/api/workflows/{wf_id}/tasks/{task_id}` | Update task |
| `DELETE` | `/api/workflows/{wf_id}/tasks/{task_id}` | Delete task |
| `GET` | `/api/workflows/templates` | List workflow templates |
| `POST` | `/api/workflows/templates/{id}/instantiate` | Create workflow from template |
| `POST` | `/api/workflows/{id}/execute` | Start async workflow execution |
| `GET` | `/api/executions/{id}` | Get execution status + task results |
| `POST` | `/api/executions/{id}/cancel` | Cancel running execution |
| `GET` | `/api/executions` | Searchable execution history |
| `WS` | `/api/ws/executions/{id}` | Real-time execution updates |
| `POST` | `/api/agents/execute` | Execute a specialized AI agent |
| `GET` | `/api/agents/executions` | List agent execution history |
| `GET` | `/api/analytics/overview` | Platform-wide analytics metrics |
| `GET` | `/api/analytics/trends` | Execution trends (last 7 days) |
| `GET` | `/api/analytics/agents` | Agent usage statistics |
| `POST` | `/api/reports/generate` | Generate AI report from execution |
| `GET` | `/api/reports` | List generated reports |
| `GET` | `/api/reports/{id}` | Get report by ID |
| `GET` | `/api/reports/{id}/download` | Download PDF report |

---

## AI Agents

### Task Analysis Agent (LangGraph)
Classifies tasks and recommends actions before execution.  
**Input:** Free-text task description  
**Output:** Category, priority, complexity, recommended action, explanation, suggested subtasks

### Research Agent
Analyzes research questions and generates structured research summaries.  
Clearly distinguishes supplied context from AI-generated suggestions.

### Content Generation Agent
Generates professional emails, articles, social media content, and business descriptions.  
Supports multiple writing tones and returns structured content.

### Data Analysis Agent
Analyzes user-provided JSON or CSV datasets.  
Identifies trends, patterns, and key insights. **Never invents numerical results.**

### Reporting Agent
Converts task results and structured information into professional Markdown or PDF reports.  
Includes executive summary, findings, and recommendations.

### Intelligent Router
Automatically routes tasks to the most suitable agent based on task description keywords and content.

---

## Workflow Templates

Three pre-built templates are available:

| Template | Tasks | Use Case |
|----------|-------|----------|
| **Customer Feedback Analysis** | Research → Data Analysis → Reporting | Analyze customer feedback and generate report |
| **AI Content Generation Pipeline** | Research → Content Generation → Reporting | Research topic and produce polished content |
| **Business Research & Reporting** | Research → Reporting | Deep-dive research with executive summary |

---

## Testing

```bash
cd backend
source venv/bin/activate

# Run full test suite
pytest tests/ -v --no-header -p no:warnings

# Run only security tests (no PostgreSQL required)
pytest tests/test_step8_security.py -v
```

**Expected results (with PostgreSQL running):**
```
57 items collected
42 passed, 2 skipped (Steps 1–7: no PostgreSQL needed for mock tests)
+ 18 passed (Step 8 security tests)
Total: 57 passed, 2 skipped
```

**Note:** Tests that depend on PostgreSQL require a running database configured in `backend/.env`.  
Tests that use mocked databases (SQLite) run without any database.

---

## Security

- **API keys** are loaded via environment variables — never hard-coded.
- **`.env` is excluded** from version control via `.gitignore`.
- **CORS** is configured via the `ALLOWED_ORIGINS` environment variable.  
  In production, set this to your specific domain(s) — never use `"*"`.
- **Request size limit:** 5 MB maximum body size enforced by middleware.
- **Error handling:** Unhandled exceptions return a generic 500 message — internal stack traces are never exposed to clients.
- **Authentication / Authorization:** Not implemented in this demo project.  
  ⚠️ **Add authentication before deploying to production with multiple users.**  
  Recommended: JWT tokens with FastAPI's `OAuth2PasswordBearer` or a service like Auth0.
- **Database credentials** are kept server-side and never returned in API responses.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | `development` or `production` |
| `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` | `8000` | Bind port |
| `DEBUG` | `true` | Set `false` in production |
| `DATABASE_URL` | `postgresql://postgres:changeme@localhost:5432/ai_workflow_db` | PostgreSQL connection URL |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `GEMINI_TIMEOUT_SECONDS` | `30` | Gemini API timeout |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated CORS origins |
| `SECRET_KEY` | _(placeholder)_ | Secret key (for future auth) |

---

## Resume Highlights

**Project Title:** AI Multi-Agent Workflow Automation Platform

**Technologies:** Python · FastAPI · LangGraph · Google Gemini API · React 18 · PostgreSQL · Docker · WebSockets · TailwindCSS

**Resume Bullets:**
- Built a full-stack AI workflow automation platform integrating **Google Gemini** and **LangGraph** to orchestrate four specialized AI agents (Research, Content, Data Analysis, Reporting) with intelligent task routing
- Designed an **async execution engine** with real-time WebSocket updates, sequential task output chaining, configurable retries, and cancellation support — reducing manual workflow coordination time
- Architected a **visual workflow builder** using React Flow with drag-and-drop node editing, circular dependency prevention, and real-time execution monitoring dashboards
- Implemented **production security** features including request size limiting, environment-variable-driven CORS, generic error handling, and Docker Compose deployment with PostgreSQL persistence and health checks

**60-Second Pitch:**
> I built an end-to-end AI workflow automation platform using FastAPI, LangGraph, and Google Gemini. It orchestrates four specialized AI agents — for research, content generation, data analysis, and reporting — through an intelligent routing layer that automatically selects the right agent for each task. Users build multi-step workflows visually using a React Flow canvas, execute them asynchronously, and watch real-time status updates via WebSockets. Results flow between tasks automatically, and completed workflows generate downloadable PDF reports. The platform tracks execution history and analytics in PostgreSQL and is containerized with Docker Compose for deployment.

**Interview Questions:**
1. **How does LangGraph improve on direct API calls for agent orchestration?**  
   LangGraph manages state transitions explicitly, making complex multi-step agent workflows composable and debuggable. Each node in the graph is a typed state transformation, which prevents the ad-hoc spaghetti that forms when chaining raw API calls with manual state management.

2. **How did you prevent race conditions in concurrent workflow executions?**  
   The execution engine tracks active execution IDs in an in-memory set guarded by an async lock. Before starting, it checks for an existing active execution on the same workflow and returns a 409 Conflict if one exists. Task status is also committed to PostgreSQL atomically, providing a durable record.

3. **How do WebSockets integrate with FastAPI's async model?**  
   FastAPI's WebSocket endpoints are native coroutines. The `ExecutionWebSocketManager` maintains a dict of active WebSocket connections per execution ID. The execution engine's background task broadcasts structured JSON messages via `asyncio.gather`, and the client-side uses a polling fallback if the WebSocket disconnects unexpectedly.

4. **Why did you choose PostgreSQL over a simpler store like SQLite for this project?**  
   PostgreSQL supports concurrent writes needed by the async execution engine, full-text query patterns used in execution history filtering, and proper foreign key enforcement for workflow/task/execution relationships. SQLite's file-locking would cause failures under concurrent async task updates.

5. **What security concerns would you address before a public production deployment?**  
   Add JWT-based authentication and route-level authorization guards. Harden CORS to specific domains. Add rate limiting to the AI endpoints to prevent abuse. Encrypt sensitive fields at rest. Add audit logging for all write operations. Set `DEBUG=false` and disable the OpenAPI docs endpoint in production.
