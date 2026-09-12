# Next.js demo UI

The public-facing UI lives in `frontend/`. It is a Next.js landing page with a
floating AI Assistant widget, inspired by a customer-support widget rather than
a full-page admin dashboard. Django remains the only source of agent, academic,
RAG, session, and nDRIMS data.

## Local run

Start Django first from the repository root:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000`. The development rewrite forwards `/api/*` to
Django at `127.0.0.1:8000`; no duplicate Node agent API exists.

The widget first requests `/api/csrf/`, then uses the returned token for the
SSE POST request. For a local authenticated test, sign in to Django Admin at
`http://127.0.0.1:8000/admin/` before opening the Next.js page. The browser
session cookie is host-based rather than port-based, so it is sent through the
development proxy.

For a deployed version, put Next.js and Django behind one HTTPS origin and
route `/api/` to Django. Do not expose Gemini or database credentials to the
Next.js browser bundle.
