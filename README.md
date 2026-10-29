# 🎓 AI-Powered Smart Classroom AV Troubleshooting Assistant

A production-ready full-stack web application for campus-wide classroom audiovisual (AV) complaint management, automated technician dispatch, and AI-powered troubleshooting assistance. Engineered for a single college campus across multiple blocks, classrooms, faculty members, and assigned technicians.

---

## 🚀 Key Architectural Highlights

- **Frontend:** Modern **React 18** Single-Page Application (SPA) built with **Vite** and **Tailwind CSS**, strictly matching the finalized Figma design prototype ([revel-next-20376655.figma.site](https://revel-next-20376655.figma.site)).
  - Manrope typography, `#090d16` navy sidebar, `#4f46e5` royal indigo accents, `#f8fafc` canvas, and interactive role switcher.
  - Zero hardcoded statistics: all metrics, charts, tables, and streams query live backend APIs.
- **Backend:** **Python FastAPI** REST API server providing parameterized SQLite operations, ChromaDB vector retrieval, and OpenAI-compatible Qwen3-8B inference endpoints.
- **Relational Database:** SQLite with Foreign Keys enforced, WAL mode, salted SHA-256 password hashing, and role-based access control (Admin, Teacher, Technician).
- **Vector Database (RAG):** **ChromaDB** persistent vector storage (`data/chroma_db`) with automated text chunking (400 tokens / 60 overlap), metadata extraction, and semantic search.
- **AI Model Engine:** **Qwen3-8B** hardware-adaptive inference with auto-probing of OpenAI-compatible local/remote endpoints (`http://127.0.0.1:11434/v1`, `http://127.0.0.1:8000/v1`, `http://127.0.0.1:1234/v1`) and grounded fallback synthesis strictly constrained to ChromaDB evidence.
- **Emergency Safety Protocol:** Built-in NLP safety hazard detector stopping troubleshooting on smoke, sparks, burning smells, or exposed wiring to trigger emergency dispatch.
- **Lectern QR Workflow:** Opaque token resolution for every classroom, automated duplicate ticket detection, and printable QR plaques.
- **Audit Logs:** Immutable chronological event stream (`complaint_events`) recording all steps, feedback, status transitions, and technician notes.

---

## 📂 Project Structure

```text
classroom-av-assistant/
├── frontend/                     # React + Vite + Tailwind CSS Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx        # Campus clock, live badges, and role switcher dropdown
│   │   │   └── Sidebar.jsx       # Brand badge, 9 navigation items, & Qwen3-8B status card
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx           # 4 Telemetry cards, trend chart, device breakdown, table, & quick-view panel
│   │   │   ├── TroubleshootingChatPage.jsx # Multi-turn AI copilot, safety hazard banner, source citations, & step feedback
│   │   │   ├── ClassroomQRPage.jsx         # Lectern QR scanner, opaque token resolution, & duplicate checker
│   │   │   ├── RaiseRequestPage.jsx        # Technician dispatch form with auto-routing preview
│   │   │   ├── MyComplaintsPage.jsx        # Role-governed complaints filter and session launcher
│   │   │   ├── TechnicianWorkspacePage.jsx # Assigned queue cards, Acknowledge, Add Note, & Resolve modal
│   │   │   ├── ComplaintLogsPage.jsx       # Complaint table with expandable chronological audit timeline
│   │   │   ├── KnowledgeBasePage.jsx       # Approved SOP manuals and PDF/TXT manual ingestion to ChromaDB
│   │   │   ├── AdminSettingsPage.jsx       # Blocks, classrooms, printable QR plaques, & public datasets
│   │   │   └── SignInPage.jsx              # Figma split-hero sign-in with salted authentication
│   │   ├── services/
│   │   │   └── api.js            # Centralized API service connecting React to FastAPI
│   │   ├── App.jsx               # Application routing and state management
│   │   ├── index.css             # Tailwind directives & design system variables
│   │   └── main.jsx              # React DOM entry point
│   ├── index.html                # HTML template with Google Fonts (Manrope)
│   ├── package.json              # Frontend npm dependencies & scripts
│   ├── postcss.config.js         # PostCSS config for Tailwind
│   ├── tailwind.config.js        # Figma color tokens & fonts configuration
│   └── vite.config.js            # Vite build configuration with /api proxy to port 8000
│
├── backend/                      # Python FastAPI Backend
│   ├── main.py                   # FastAPI server entry point
│   ├── api.py                    # REST API routes (Dashboard, Auth, QR, Chat, Complaints, Tickets)
│   ├── config.py                 # Configuration settings and environment variables
│   ├── repository.py             # Resilient local JSON / MongoDB fallback storage layer
│   ├── ai_assistant.py           # Diagnostic planning and guided troubleshooting assistant
│   ├── knowledge_base.py         # Knowledge retriever interface
│   ├── dataset_loader.py         # CSV dataset analytics (5,000 incident dataset)
│   ├── requirements.txt          # Python dependencies
│   ├── database/
│   │   ├── connection.py         # SQLite connection manager & WAL configuration
│   │   ├── schema.sql            # 11 normalized tables with indexes & constraints
│   │   └── crud.py               # Parameterized SQL queries, salted password auth, & live metrics
│   ├── model/
│   │   └── llm_inference.py      # Qwen3-8B pipeline loader, endpoint discovery, & grounded synthesis
│   ├── nlp/
│   │   └── extractor.py          # NLP entity parser, hazard detector, & urgency classifier
│   ├── rag/
│   │   ├── document_processor.py # PDF/TXT manual parser & sliding-window chunker
│   │   └── vector_store.py       # ChromaDB vector store wrapper
│   └── services/
│       ├── complaint_service.py  # Complaint lifecycle, auto-routing, & feedback processor
│       ├── dataset_service.py    # Public datasets (IT_Support_V2 & FloDial)
│       ├── notification_service.py # In-app notification dispatcher & Twilio voice integration
│       └── qr_service.py         # QR code plaque generator
│
├── data/
│   ├── campus_manuals/           # Verified campus SOP manuals (Projector, Smart Board, Mic, etc.)
│   ├── chroma_db/                # Persistent ChromaDB vector database files
│   ├── classroom_av.db           # Persistent SQLite database
│   └── ai_classroom_av_troubleshooting_5000.csv
│
├── scripts/
│   └── seed_data.py              # Campus infrastructure, demo users, & SOP chunk seeder
│
├── tests/
│   ├── run_tests.py              # Master test runner (Runs all 3 test suites)
│   ├── test_acceptance.py        # 13 Acceptance criteria tests
│   ├── test_rag_grounding.py     # 7 RAG retrieval & evidence grounding tests
│   └── test_workflow.py          # 9 End-to-end full lifecycle workflow tests
│
├── main.py                       # Root launcher for backend (python -m uvicorn main:app --reload)
├── package.json                  # Root npm runner ("npm run dev" starts frontend)
├── requirements.txt              # Root Python requirements
└── README.md                     # Comprehensive project documentation
```

---

## ⚡ Quick Start Instructions

### 1. Environment Setup & Python Dependencies

Make sure Python 3.10+ and Node.js 18+ are installed.

Install Python dependencies:
```powershell
pip install -r requirements.txt
```

Initialize and seed the SQLite database and ChromaDB vector store:
```powershell
python scripts/seed_data.py
```

### 2. Frontend Dependencies

Install npm dependencies:
```powershell
cd frontend
npm install
cd ..
```

---

## 🖥️ Running the Application

### Start the Backend Server (FastAPI)
Run from the project root:
```powershell
python -m uvicorn main:app --reload
```
- API Server: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

### Start the Frontend Server (React + Vite)
In a separate terminal, run from the project root:
```powershell
npm run dev
```
*(Or navigate to `frontend` and run `npm run dev`)*
- Web Application: `http://localhost:5173`

---

## 🔑 Demo Login Credentials

The database comes pre-seeded with verified demo credentials. You can also switch roles at any time using the quick role switcher in the top header.

| Role | Name | Email / Username | Password | Access Scope |
|---|---|---|---|---|
| **Administrator** | Dr. Priya Sharma | `priya@campus.edu` / `admin` | `Admin@123` | Full access across all 9 pages, infrastructure, manuals, and settings |
| **Teacher** | Prof. Elena Rostova | `elena@campus.edu` / `teacher1` | `Teacher@123` | Dashboard, AI Troubleshooting Chat, QR Scanner, Requests, My Complaints, Logs |
| **Technician** | Alex Martinez | `alex.tech@campus.edu` / `tech1` | `Tech@123` | Dashboard, Technician Workspace (Acknowledge, Notes, Resolve), QR, Requests, Logs |

---

## 🧪 Running Automated Tests

Run the complete test suite (all 3 suites, 29 total integration and acceptance checks):
```powershell
python tests/run_tests.py
```

- **Suite 1 (`test_acceptance.py`):** 13 Acceptance tests verifying SQLite persistence, dashboard counts, chat history, technician acknowledge/resolve, duplicate detection, and safety hazard detection.
- **Suite 2 (`test_rag_grounding.py`):** 7 RAG tests verifying 2,292 empirical incident chunks, TF-IDF and ChromaDB semantic retrieval, evidence citations, and out-of-domain query fallbacks.
- **Suite 3 (`test_workflow.py`):** 9 End-to-end lifecycle tests validating diagnosis planning, complaint creation, step feedback, ticket escalation, and technician status patches.

---

## 🛡️ API Endpoints Reference

### Dashboard & Analytics
- `GET /api/dashboard/metrics`: Live SQLite complaint counts, weekly trend bars, device distribution, and latest complaints.
- `GET /api/health`: Health status, storage mode, vector store chunk count, and retriever status.
- `GET /api/analytics`: Dataset analytics from 5,000 incident historical records.
- `GET /api/metadata`: Device types, models, and symptoms.

### Authentication
- `POST /api/auth/login`: Authenticate with username or email and salted SHA-256 password hash.
- `GET /api/auth/users`: List registered campus users with role filter.

### Infrastructure & QR
- `GET /api/blocks`: List campus academic blocks.
- `POST /api/blocks`: Create a new campus block.
- `GET /api/classrooms`: List classrooms with opaque QR tokens.
- `POST /api/classrooms`: Create a classroom and generate a stable QR token.
- `GET /api/classrooms/token/{qr_token}`: Zero-auth classroom resolution by scanned token.
- `GET /api/classrooms/{id}/qr-plaque`: Base64 printable QR code plaque for lectern mounting.
- `GET /api/duplicate-check`: Prevent duplicate unresolved complaints for a room/device.

### Troubleshooting & Complaints
- `POST /api/chat/troubleshoot`: Grounded AI troubleshooting step with ChromaDB evidence retrieval and safety hazard checks.
- `GET /api/chat/{complaint_id}`: Retrieve persistent conversation history.
- `POST /api/chat/{complaint_id}/feedback`: Process user feedback on troubleshooting step (*worked*, *failed*).
- `POST /api/complaints`: Register a complaint.
- `GET /api/complaints`: List and filter complaints by status, room, device, or technician.
- `POST /api/complaints/{id}/status`: Update complaint status (*acknowledged*, *diagnostic note*, *resolved*).
- `POST /api/complaints/{id}/escalate`: Escalate complaint to assigned technician.
- `GET /api/complaints/{id}/events`: Retrieve chronological audit timeline.

### Knowledge Base & Datasets
- `GET /api/knowledge-base/documents`: List approved SOP manuals.
- `POST /api/knowledge-base/upload`: Ingest PDF/TXT/MD manual, chunk, and embed into ChromaDB.
- `GET /api/datasets/status`: Status of `benjaminmacklin/IT_Support_V2` and `FloDial`.
- `POST /api/datasets/verify`: Reload and verify public IT support datasets.
