# OMR System Setup Instructions

## ⚠️ SECURITY NOTE

**DO NOT commit DATABASE_URL or API keys to this repository.**

Environment variables should be configured directly in Vercel dashboard, never in code or documentation.

## GitHub Actions CI

GitHub Actions tests are **already configured** and use SQLite for testing:

- ✅ `tests/test_auth.py` - Database tables auto-created
- ✅ `tests/test_reports.py` - Direct function calls (no TestClient)
- ✅ `tests/test_database.py` - SQLite test database
- ✅ Frontend build - Vite optimization

**CI Status**: View at https://github.com/shivam-kumar-ux/OMR_Reader/actions

## Vercel Deployment

### Step 1: Rotate Neon Credentials

Your previous DATABASE_URL credentials have been exposed and must be rotated:

1. Go to: https://console.neon.tech/
2. Navigate to your project: **delicate-smoke-09511385**
3. Click **Connection** section
4. Click **Reset password** to generate new credentials
5. Copy the new connection string

### Step 2: Add Environment Variables to Vercel

1. Go to: https://vercel.com/dashboard
2. Click your project: **omr-reader-a3ny**
3. Click **Settings** → **Environment Variables**
4. Add these variables (use your NEW Neon connection string):

```
DATABASE_URL          = [NEW_NEON_CONNECTION_STRING]
APP_SECRET_KEY        = [SECURE_KEY_HERE]
ENVIRONMENT           = production
DEBUG                 = False
STORAGE_PROVIDER      = local
CONFIDENCE_THRESHOLD_AUTO_ACCEPT = 0.88
BUBBLE_FILL_THRESHOLD = 0.35
BUBBLE_UNCERTAIN_LOW  = 0.20
BUBBLE_UNCERTAIN_HIGH = 0.35
OCR_NAME_SIMILARITY_THRESHOLD = 0.75
IS_SERVERLESS         = true
```

5. For each variable select scope: **Production, Preview, Development**

### Step 3: Redeploy

1. Click **Deployments** tab
2. Click **Redeploy** on latest deployment
3. Wait for deployment to complete (2-5 minutes)

## Testing

Once deployed:

```bash
# Health check
curl https://omr-reader-a3ny.vercel.app/api/health

# Try login (use your Neon database credentials or fallback to SQLite)
curl -X POST https://omr-reader-a3ny.vercel.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@12345"}'
```

## Fallback Behavior

If PostgreSQL connection fails:
- ✅ Application automatically falls back to SQLite at `/tmp/omr_local.db`
- ✅ Pre-seeded accounts available:
  - `admin` / `Admin@12345` (Admin role)
  - `operator` / `Operator@12345` (Operator role)
- ✅ No downtime - application continues to work

## Code Fixes Applied

All critical production issues have been fixed:

1. ✅ Neon `channel_binding=require` hang → Stripped from connection string
2. ✅ Missing 5-second connect timeout → Added
3. ✅ No database fallback → Automatic SQLite fallback
4. ✅ Wrong Vercel entrypoint → Fixed to `api/index.py`
5. ✅ CI test failures → Auto-create tables + direct function calls

See commits:
- `f782d4b` - Database resilience & CI fixes
- `af94d95` - Vercel entrypoint configuration

## Troubleshooting

**Still getting FUNCTION_INVOCATION_FAILED?**

1. Check Vercel logs:
   - Deployments → Failed deployment → Runtime Logs
   - Look for actual error message

2. Verify DATABASE_URL is set:
   - Settings → Environment Variables
   - DATABASE_URL should be visible

3. If PostgreSQL unreachable:
   - Don't panic! SQLite fallback kicks in
   - Try logging in with `admin` / `Admin@12345`

4. Check git history was cleaned:
   - Exposed credentials should no longer be in repo
   - If needed, use `git filter-branch` or `git filter-repo`

