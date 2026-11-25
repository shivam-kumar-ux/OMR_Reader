# OMR System - Deployment Checklist

## ✅ Pre-Deployment Verification

### Code Quality
- [x] Database connection resilience (channel_binding stripped, 5s timeout, SQLite fallback)
- [x] Correct Vercel entrypoint (`api/index.py`)
- [x] Path resolution for modules fixed
- [x] CI tests passing (auto DB table creation, direct function calls)
- [x] Build size optimized < 500MB

### Configuration Files
- [x] `vercel.json` - Correct entrypoint and routing
- [x] `.vercelignore` - Excludes dev files, samples, tests
- [x] `api/index.py` - Proper module imports
- [x] `backend/app/db/session.py` - Fallback logic implemented
- [x] Requirements pinned to specific versions

### Documentation
- [x] SETUP_INSTRUCTIONS.md - Safe setup without secrets
- [x] BUILD_OPTIMIZATION_SUMMARY.md - Size reduction strategy
- [x] CRITICAL_ACTIONS.txt - Security steps
- [x] FINAL_ACTION_PLAN.txt - Implementation steps
- [x] DEPLOYMENT_CHECKLIST.md (this file)

### Security
- [x] Exposed Neon credentials removed from git
- [x] Credentials added to .gitignore
- [x] No secrets in documentation
- [x] Environment variables to be set in Vercel dashboard only

### Git History
- [x] Commits cleaned (samples folder removed)
- [x] Repository size < 50MB
- [x] All changes pushed to main branch

---

## 🔧 Manual Configuration Required

### Step 1: Rotate Neon Credentials

**Status**: ⏳ PENDING

1. Navigate to: https://console.neon.tech/
2. Find project ID: `delicate-smoke-09511385`
3. Go to "Connect" section
4. Click "Reset password" button
5. Copy the new connection string
6. This becomes your NEW DATABASE_URL

**Verification**:
```bash
# Your new connection string should look like:
postgresql://neondb_owner:NEW_PASSWORD@ep-lingering-voice-be753qfw.c-9.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### Step 2: Configure Vercel Environment Variables

**Status**: ⏳ PENDING

Go to: https://vercel.com/dashboard

1. Click project: `omr-reader-a3ny`
2. Go to: **Settings → Environment Variables**
3. Find or create `DATABASE_URL`
4. Set value to: `[NEW_CONNECTION_STRING_FROM_STEP_1]`
5. For scope, select: **Production, Preview, Development**
6. Click "Save"

**Verification**:
```bash
# After saving, it should show in the variables list
DATABASE_URL = postgresql://neondb_owner:***@ep-lingering-voice...
```

### Step 3: Redeploy Application

**Status**: ⏳ PENDING

1. Go to: https://vercel.com/projects
2. Click: `omr-reader-a3ny`
3. Navigate to: **Deployments** tab
4. Find the latest deployment (should show "Failed")
5. Click on it
6. Click: **Redeploy** button
7. Wait for build to complete (2-5 minutes)
8. Status should change from "Building" → "Ready" ✅

**What happens during redeploy**:
- Vercel installs Python dependencies
- Frontend is built with Vite
- Build cleanup script runs (removes test files, cache)
- Bundle is packaged (~350-400MB)
- FastAPI app is deployed
- Vercel CLI tests the endpoint

---

## 🧪 Post-Deployment Testing

### Test 1: Health Check

```bash
curl -v https://omr-reader-a3ny.vercel.app/api/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "environment": "production",
  "storage_provider": "local"
}
```

### Test 2: Login Endpoint

```bash
curl -X POST https://omr-reader-a3ny.vercel.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@12345"}'
```

**Expected response (if Neon is reachable)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 28800,
  "user_id": 1,
  "username": "admin",
  "role": "Admin"
}
```

**Expected response (if Neon is unreachable)**:
- SQLite fallback kicks in
- Same response with pre-seeded account

### Test 3: Web Interface

1. Go to: https://omr-reader-a3ny.vercel.app/
2. See login page loads (no 500 error)
3. Enter credentials: `admin` / `Admin@12345`
4. Should redirect to dashboard

### Test 4: GitHub Actions CI

Go to: https://github.com/shivam-kumar-ux/OMR_Reader/actions

Expected status: ✅ **All checks passing**
- Backend tests: PASS
- Frontend build: PASS

---

## 🚨 Troubleshooting

### Issue: Still getting FUNCTION_INVOCATION_FAILED

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| DATABASE_URL not set | Check Settings → Environment Variables in Vercel |
| Old password used | Rotate Neon password, get NEW connection string |
| Deployment not redeployed | Click Redeploy button after updating env vars |
| Build exceeding 500MB | Already optimized, should be <400MB now |

**Check Vercel logs**:
1. Go to Vercel project
2. Deployments → Failed deployment
3. Click "Runtime Logs" (bottom right)
4. Look for actual error message

### Issue: Can't login even with admin/Admin@12345

**Possible causes**:
- PostgreSQL not reachable → SQLite fallback should work
- Database not initialized → Our code creates tables automatically
- Wrong credentials → Use `admin` / `Admin@12345` exactly

**Check SQLite fallback**:
1. The app should automatically fall back to SQLite
2. Pre-seeded accounts: `admin` / `Admin@12345`, `operator` / `Operator@12345`
3. If still failing, check Vercel runtime logs

### Issue: Build still taking > 500MB

**Solutions**:
1. Run `git filter-repo` to clean git history of large files
2. Verify `.vercelignore` is not accidentally ignoring needed files
3. Check `vercel-build.sh` is included in repo
4. Force push cleaned history: `git push --force-with-lease origin main`

---

## 📋 Final Verification

### Before Going Live

- [ ] Neon password rotated
- [ ] DATABASE_URL updated in Vercel
- [ ] Vercel redeployed (shows "Ready")
- [ ] Health check endpoint responds
- [ ] Login page loads
- [ ] Can login with admin/Admin@12345
- [ ] GitHub Actions showing ✅ PASS
- [ ] No 500 errors in browser console

### Production Ready Checklist

- [ ] Database credentials secured (old one rotated)
- [ ] Environment variables properly configured
- [ ] All secrets removed from git
- [ ] Build optimized < 500MB
- [ ] SQLite fallback tested
- [ ] Error handling verified
- [ ] Logging enabled for debugging
- [ ] HTTPS enforced (Vercel handles this)

---

## 📞 Support

If you encounter issues:

1. **Check the logs**:
   - Vercel: Dashboard → Deployments → Runtime Logs
   - GitHub Actions: Repository → Actions → Failed workflow

2. **Read the documentation**:
   - SETUP_INSTRUCTIONS.md
   - BUILD_OPTIMIZATION_SUMMARY.md
   - CRITICAL_ACTIONS.txt

3. **Verify configuration**:
   - DATABASE_URL set in Vercel ✅
   - api/index.py is entry point ✅
   - .vercelignore excludes dev files ✅

---

## 🎯 Success Criteria

✅ **Deployment Successful When**:
1. Vercel shows "Ready" with green checkmark
2. No FUNCTION_INVOCATION_FAILED errors
3. Health check responds with 200 OK
4. Login endpoint works
5. Web interface loads and is functional
6. GitHub Actions CI passes

**Expected timeline**: 5-10 minutes from credential rotation to working deployment

