# Vercel Deployment Setup Guide

## Step 1: Add Environment Variables in Vercel Dashboard

Go to your Vercel project: https://vercel.com/dashboard

1. Click on your project: **omr-reader-a3ny**
2. Go to **Settings** → **Environment Variables**
3. Add the following variables:

### Required Environment Variables:

| Variable Name | Value | Scope |
|---|---|---|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_lcmzqebWAS17@ep-lingering-voice-be753qfw.c-9.us-east-2.aws.neon.tech/neondb?sslmode=require` | Production, Preview |
| `APP_SECRET_KEY` | `supersecret-omr-app-key-change-in-production-2026-secure!` | Production, Preview |
| `ENVIRONMENT` | `production` | Production |
| `DEBUG` | `False` | Production |
| `STORAGE_PROVIDER` | `local` | Production, Preview |
| `CONFIDENCE_THRESHOLD_AUTO_ACCEPT` | `0.88` | Production, Preview |
| `BUBBLE_FILL_THRESHOLD` | `0.35` | Production, Preview |
| `BUBBLE_UNCERTAIN_LOW` | `0.20` | Production, Preview |
| `BUBBLE_UNCERTAIN_HIGH` | `0.35` | Production, Preview |
| `OCR_NAME_SIMILARITY_THRESHOLD` | `0.75` | Production, Preview |
| `IS_SERVERLESS` | `true` | Production, Preview |

## Step 2: Verify Build & Deployment Settings

1. Go to **Settings** → **Build & Development Settings**
2. Verify:
   - **Framework Preset**: `Other`
   - **Build Command**: `npm run build --prefix frontend` (or leave blank if using vercel.json)
   - **Output Directory**: `frontend/dist`
   - **Install Command**: `npm install`

## Step 3: Redeploy

After adding environment variables:

1. Go to **Deployments** tab
2. Click on the latest deployment
3. Click **Redeploy** button

Or push a new commit to trigger auto-deployment:

```bash
git commit --allow-empty -m "trigger: redeploy with env vars"
git push origin main
```

## Step 4: Test the Deployment

Once deployed, test with:

```bash
# Health check
curl https://omr-reader-a3ny.vercel.app/api/health

# Test endpoint
curl https://omr-reader-a3ny.vercel.app/api/test

# Login endpoint (should fail gracefully if DB is down)
curl -X POST https://omr-reader-a3ny.vercel.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@12345"}'
```

## Troubleshooting

If you still get `FUNCTION_INVOCATION_FAILED`:

1. **Check Vercel Logs**:
   - Go to your Vercel project → **Deployments**
   - Click the failed deployment
   - Click **Runtime Logs** to see actual error

2. **Common Issues**:
   - DATABASE_URL not set → Falls back to SQLite in `/tmp/omr_local.db`
   - Import errors → Check Python path in `api/index.py`
   - Timeout → Neon connection taking too long, our fix should handle this
   - Missing dependencies → Check `.vercelignore` isn't excluding needed files

3. **If database connection fails**:
   - The app will auto-fallback to SQLite
   - Login with `admin` / `Admin@12345`
   - Check `/tmp/omr_local.db` exists on Vercel

## GitHub Actions CI

The CI workflow should now pass with our fixes:
- Tests use SQLite (`DATABASE_URL: sqlite:///./test_ci.db`)
- Database tables auto-created by `ensure_db` fixture
- No TestClient deadlocks in test_reports.py
- Backend tests: ✅ PASS
- Frontend build: ✅ PASS

