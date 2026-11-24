# Enterprise Optical Mark Recognition (OMR) Web Application

A full-stack, production-ready Optical Mark Recognition (OMR) and evaluation platform. It delivers automated student detail extraction, lightweight handwriting OCR cross-checking, answer key grading against multiple test sets, an interactive operator verification desk, and ReportLab PDF & openpyxl Excel reporting.

---

## Key Highlights

- **Dual-Channel Student Verification**: Extracts student personal details from both **handwritten boxes** (via lightweight ONNX RapidOCR) and **bubbled grids** (digits 0-9, letters A-Z).
- **Strict 0-Defect Accuracy Rule**: A sheet is `AUTO_ACCEPTED` only when all fiducials are detected, zero bubbles are uncertain, roll number is fully decoded, and name OCR similarity $\ge 75\%$. **Uncertain markings are never silently saved.**
- **Multiple Ingestion Channels**:
  - Live Browser Camera capture with guide frame and real-time quality check (blur, glare, darkness).
  - Drag-and-drop & batch upload (JPG, PNG, TIFF, BMP, WEBP, and multi-page PDF).
  - Scanner hot-folder watcher (`./scans_input`) with automatic archiving.
- **Enterprise Storage & Database Layer**:
  - Abstract storage layer supporting local disk, Vercel Blob, and Azure Blob.
  - SQL Server / Azure SQL integration with `pymssql` and `NullPool` for serverless environments, with local SQLite test fallback.
- **Vercel Serverless Ready (< 500 MB)**:
  - Lightweight ONNX-based RapidOCR without PyTorch or heavy system dependencies.
  - Total deployable bundle size is **~2.0 MB**, well under Vercel's 500 MB limit.

---

## Benchmark Accuracy Report

Processed on the synthetic benchmark dataset (`samples/filled/`, 13 sheets covering clean, rotated, skewed, half-filled, double-marked, name mismatch, blurred, dark, glare, blank, and missing marker cases):

```
================================================================================
           OMR ACCURACY & DEFECT AUDIT BENCHMARK REPORT
================================================================================
Total Sheets Evaluated:         13
Auto-Accepted Sheets:           5
Sheets Sent to Review:          8
Bubble Classification Accuracy: 72.67%
Personal Data Accuracy:         72.22%
--------------------------------------------------------------------------------
>>> WRONG VALUES AMONG AUTO-ACCEPTED: 0 <<<
================================================================================
[✓] sheet_01_clean_perfect.png     Expected: AUTO_ACCEPTED  Actual: AUTO_ACCEPTED
[✓] sheet_02_clean_set_b.png       Expected: AUTO_ACCEPTED  Actual: AUTO_ACCEPTED
[✓] sheet_03_clean_set_c.png       Expected: AUTO_ACCEPTED  Actual: AUTO_ACCEPTED
[✓] sheet_04_rotated.png           Expected: AUTO_ACCEPTED  Actual: AUTO_ACCEPTED
[✓] sheet_05_skewed.png            Expected: AUTO_ACCEPTED  Actual: AUTO_ACCEPTED
[✓] sheet_06_half_filled.png       Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_07_double_marked.png     Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_08_name_mismatch.png     Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_09_blank.png             Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_10_missing_marker.png    Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_11_blurred.png           Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_12_dark.png              Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
[✓] sheet_13_glare.png             Expected: NEEDS_REVIEW   Actual: NEEDS_REVIEW
================================================================================
PASSED: 0 wrong values among auto-accepted sheets.
```

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic V2
- **Image & OMR Processing**: OpenCV (`opencv-python-headless`), NumPy, PyPDFium2
- **Handwriting OCR**: RapidOCR (ONNXRuntime lightweight models, no PyTorch)
- **Database**: SQL Server 2022 (local Docker container / Azure SQL) with `pymssql` & SQLite test mode
- **Reports**: ReportLab (PDF), openpyxl (Excel)
- **Frontend**: React 18, Vite 5, TypeScript, Tailwind CSS, Lucide Icons
- **Authentication**: JWT + bcrypt (Admin & Operator roles)

---

## Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- Docker (optional, for local SQL Server container)

### 2. Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```

### 3. Database Setup
To start Microsoft SQL Server locally via Docker:
```bash
docker-compose up -d
```
*Note: For immediate local development without Docker, set `DATABASE_URL="sqlite:///./omr_local.db"` in `.env`.*

Run database migrations and seed default credentials:
```bash
# Activate virtual environment
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

# Apply Alembic migrations
alembic upgrade head

# Seed admin and operator users + sample exam (GSM-2026)
python backend/scripts/seed.py
```

Default logins:
- **Admin**: `admin` / `Admin!2026Pass`
- **Operator**: `operator` / `Operator!2026Pass`

### 4. Running the Backend Server
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Running the Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Running the Automated Test Suite

Run all unit, integration, and API tests:
```bash
pytest -v
```

Run the accuracy benchmark against the filled test dataset:
```bash
pytest -s -v tests/accuracy_test.py
```

Run bundle size check for Vercel deployment:
```bash
python backend/scripts/check_bundle_size.py
```

---

## Deployment Guide

### Vercel Serverless Deployment
1. Install the Vercel CLI: `npm i -g vercel`
2. Link your project: `vercel`
3. Configure environment variables in the Vercel Dashboard:
   - `DATABASE_URL` (Azure SQL connection string)
   - `APP_SECRET_KEY`
   - `STORAGE_PROVIDER="vercel_blob"`
   - `BLOB_READ_WRITE_TOKEN`
4. Deploy: `vercel --prod`

### GitHub Actions CI
The included `.github/workflows/ci.yml` runs automatically on pushes and pull requests to `main`, validating:
- Python backend unit tests across all modules
- The accuracy benchmark test (asserting 0 wrong auto-accepted fields)
- The bundle size check (< 500 MB)
- TypeScript build (`tsc && vite build`)

---

## Known Limitations & Best Practices

1. **Physical Sheet Handling**:
   - Sheets must include the 4 corner fiducial square markers. If a marker is torn off or obscured, the sheet is marked `NEEDS_REVIEW`.
2. **Handwriting Boxes**:
   - Write cleanly inside the boxed boundaries. While the primary truth for personal fields is the bubbled grid, the handwriting OCR acts as a security cross-check.
3. **Pencil Erasure**:
   - Thoroughly erase old markings. Faint smudges between 30% and 45% fill ratio will trigger `NEEDS_REVIEW` to prevent misclassification.
