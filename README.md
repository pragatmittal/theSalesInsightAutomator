## The Sales Insight Automator – Engineer's Log

This prototype delivers an end-to-end **Quick-Response Tool** for the Rabbitt AI sales team:

- **Upload** a quarterly sales `.csv`/`.xlsx`
- **AI (Gemini)** generates an executive-ready summary
- **Email** sends the narrative directly to the requested inbox

The stack is production-minded: containerized services, CI on pull requests, and a deployable split between a Vercel-ready frontend and a Render-ready backend.

---

### System Overview

- **Frontend**: Next.js (SPA-style single page)
  - Upload `.csv`/`.xlsx`
  - Enter recipient email
  - Real-time feedback (loading / success / error)
  - Talks to backend via `NEXT_PUBLIC_API_URL`
- **Backend**: FastAPI
  - `POST /api/process-sales`
    - Accepts file + recipient email + API key
    - Parses CSV
    - Aggregates sales metrics
    - Calls **Google Gemini** for a narrative
    - Sends email via **Gmail SMTP** using `fastapi-mail`
  - `GET /docs` – live Swagger UI
  - `GET /health` – liveness check
- **AI Engine**: Google Gemini (2.5 Flash)
- **Mail Service**: Gmail SMTP (`fastapi-mail`)

---

### Running Locally with Docker Compose

#### 1. Prerequisites

- Docker + docker-compose
- Google Gemini API key
- Gmail account with an **App Password** for SMTP

#### 2. Configure environment

From the repo root:

```bash
cp .env.example .env
```

Edit `.env` and provide real values:

- `BACKEND_API_KEY`
- `GEMINI_API_KEY`
- `SMTP_USERNAME`
- `SMTP_PASSWORD` (Gmail App Password)
- `SMTP_SERVER`
- `SMTP_PORT`
- `EMAIL_FROM`

#### 3. Start the stack

```bash
docker-compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend API + Swagger: `http://localhost:8000/docs`

#### 4. Use the tool

1. Open `http://localhost:3000`
2. Select a `.csv`/`.xlsx` file (e.g. the provided Q1 sample)
3. Enter the recipient email
4. Submit – you should see loading → success and receive an email with the Gemini summary

---

### Security – How Endpoints Are Secured

- **API Key Guard**
  - `POST /api/process-sales` requires a form field `x_api_key`
  - Compared against `BACKEND_API_KEY` from environment
  - Frontend injects `NEXT_PUBLIC_BACKEND_API_KEY` at build-time and sends it with every request
- **Input Validation**
  - Email validated with `EmailStr` (Pydantic)
  - File type checked (`.csv` / Excel mimetypes)
  - Non-empty payload and non-empty data rows enforced
- **Abuse Mitigation (Design Hooks)**
  - File parsing is limited to CSV for now; extension points exist for:
    - size limits
    - row-count caps
    - rate limiting (middleware)
- **Secrets Handling**
  - All sensitive configuration is environment-driven:
    - `GEMINI_API_KEY`
    - `SMTP_USERNAME` / `SMTP_PASSWORD` (Gmail)
    - `BACKEND_API_KEY`
    - `EMAIL_FROM`
  - Example values live only in `.env.example` (no real secrets in the repo)
- **Transport Security**
  - Production hosting (Vercel + Render) provides HTTPS termination

---

### Environment Configuration – `.env.example`

The `.env.example` file in the repo root documents all required configuration:

- `BACKEND_API_KEY` – shared secret between frontend and backend
- `GEMINI_API_KEY` – Google Gemini API key
- `SMTP_USERNAME` / `SMTP_PASSWORD` – Gmail SMTP credentials (App Password)
- `SMTP_SERVER` / `SMTP_PORT` – SMTP host and port (default: `smtp.gmail.com:587`)
- `EMAIL_FROM` – From-address used when sending summaries
- `NEXT_PUBLIC_API_URL` – Frontend → backend API endpoint
- `NEXT_PUBLIC_BACKEND_API_KEY` – Exposed version of the API key (same value as `BACKEND_API_KEY`)

Copy this into a real `.env` and fill in your credentials before running locally or deploying.

---

### CI/CD – GitHub Actions

On **pull requests to `main`**, `.github/workflows/ci.yml` runs:

- **Backend job**
  - Installs Python 3.12 + `backend/requirements.txt`
  - Compiles the FastAPI app (`python -m compileall app`) as a basic lint/build sanity check
- **Frontend job**
  - Installs Node 22 + `npm install`
  - Runs `npm run lint`
  - Runs `npm run build`

If any step fails, the PR check fails, blocking merges until the build is healthy.

---

### Deployment Notes

#### Backend – Render

1. Create a new **Web Service** pointing at the `backend` directory:
   - If using Docker:
     - Build with the provided `backend/Dockerfile`
   - Expose port `8000`
2. Configure environment variables on Render:
   - `BACKEND_API_KEY`
   - `GEMINI_API_KEY`
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_SERVER`
   - `SMTP_PORT`
   - `EMAIL_FROM`
3. Note the public base URL, e.g.:
   - `https://sales-insight-backend.onrender.com`
4. Swagger docs will be available at:
   - `https://sales-insight-backend.onrender.com/docs`

#### Frontend – Vercel

1. Connect the GitHub repository to Vercel
2. Set project environment variables:
   - `NEXT_PUBLIC_API_URL=https://sales-insight-backend.onrender.com/api/process-sales`
   - `NEXT_PUBLIC_BACKEND_API_KEY=<same BACKEND_API_KEY used on backend>`
3. Build command: `npm run build`
4. Output directory: `.next` (default for Next.js)

Once deployed:

- **Frontend URL** (example): `https://sales-insight-frontend.vercel.app`
- **Swagger URL**: `https://sales-insight-backend.onrender.com/docs`

Include both in your submission.

---

### Future Hardening Ideas

- Add proper **rate limiting** and strict **file size caps**
- Extend parser to support `.xlsx` robustly (e.g., `pandas.read_excel`)
- Persist request logs / summaries for auditability
- Add authentication (e.g., SSO / JWT) around the frontend and backend

