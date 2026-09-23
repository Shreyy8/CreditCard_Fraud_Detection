# Savanna Graph Setup

The graph path is now repository-owned and repeatable. Keep `.env` local and never commit credentials.

## 1. Configure the workspace

Set these values in the project-root `.env`:

```ini
TIGERGRAPH_HOST=https://<workspace-host>.i.tgcloud.io
TIGERGRAPH_GRAPH_NAME=FraudCaseGraph
TIGERGRAPH_USERNAME=tigergraph
TIGERGRAPH_PASSWORD=<password>
TIGERGRAPH_SECRET=<gsql-secret>
```

A pre-issued bearer token may be used with `TIGERGRAPH_TOKEN` instead of the secret.

## 2. Install schema and queries

From the repository root, with `.venv` active:

```powershell
.\.venv\Scripts\python.exe backend\install_schema.py
.\.venv\Scripts\python.exe backend\install_queries.py
```

The schema is in `backend/gsql/schema.gsql`; the investigation queries are in `backend/gsql/investigation_queries.gsql`.

## 3. Validate and load data

Always inspect the generated counts first:

```powershell
.\.venv\Scripts\python.exe backend\graph_loader.py --dry-run
```

When the schema exists and the counts look correct, upload the local supplied dataset:

```powershell
.\.venv\Scripts\python.exe backend\graph_loader.py --load
```

The loader uses `artifacts/transaction_cards.csv` for derived card IDs and does not download or recover outcomes from public IEEE-CIS/Kaggle files.

## 4. Run the app

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

In another terminal:

```powershell
Push-Location frontend
npm install
npm run dev
Pop-Location
```

The live graph integration tests require a running Savanna workspace with the schema, data, and queries installed. Local detector and loader fixture tests do not require Savanna.
