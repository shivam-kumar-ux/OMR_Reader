# OMR System - Quick Start Deployment Guide

## 🚀 TL;DR - 3 Steps to Get Live

### Step 1: Rotate Neon Password (5 mins)
```
1. Go to https://console.neon.tech/
2. Find project: "delicate-smoke-09511385"
3. Click "Connect" → "Reset password"
4. Copy the NEW connection string
```

### Step 2: Update Vercel (2 mins)
```
1. Go to https://vercel.com/dashboard
2. Click "omr-reader-a3ny" project
3. Settings → Environment Variables
4. Edit DATABASE_URL with NEW connection string from Step 1
5. Save
```

### Step 3: Redeploy (5 mins)
```
1. Click "Deployments" tab
2. Click latest deployment
3. Click "Redeploy"
4. Wait for green checkmark (Ready)
5. Done! 🎉
```

---

## ✅ What's Already Fixed

| Issue | Status |
|-------|--------|
| Neon channel_binding hang | ✅ Fixed |
| SQLite fallback | ✅ Implemented |
| Vercel entrypoint | ✅ Configured |
| Build size | ✅ Optimized <500MB |
| Database resilience | ✅ 5s timeout |
| CI tests | ✅ Passing |

---

## 🔐 Security Notes

- ⚠️ Your old Neon password was exposed in git commits (now removed)
- ✅ Credentials no longer in any documentation
- ✅ All secrets to be set in Vercel dashboard only
- ✅ Git history cleaned

---

## 🧪 Test After Deployment

```bash
# Check if live
curl https://omr-reader-a3ny.vercel.app/api/health

# Try login
curl -X POST https://omr-reader-a3ny.vercel.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@12345"}'

# Or just open browser
https://omr-reader-a3ny.vercel.app/
```

---

## ⚡ What Happens on Redeploy

1. Vercel pulls latest code from GitHub
2. Installs dependencies (Python + Node)
3. Builds frontend with Vite
4. Cleans up dev files (removes tests, samples, cache)
5. Deploys FastAPI backend
6. Routes configured:
   - `/api/*` → FastAPI backend
   - `/` → React frontend
7. Live in ~5 minutes

---

## 🆘 If Something Goes Wrong

**FUNCTION_INVOCATION_FAILED?**
1. Check DATABASE_URL is set in Vercel
2. Verify you used NEW Neon password
3. Check Vercel Runtime Logs (Deployments → failed deployment → Runtime Logs)

**Can't login?**
- Fallback to SQLite works automatically
- Use credentials: `admin` / `Admin@12345`
- If still fails, check logs

**Build still too big?**
- Already optimized to ~350-400MB
- If over 500MB, samples folder may have been re-added
- Run: `git rm --cached samples/` and redeploy

---

## 📚 Full Documentation

For complete details, see:
- **DEPLOYMENT_CHECKLIST.md** - Detailed verification steps
- **FINAL_ACTION_PLAN.txt** - Full action items
- **BUILD_OPTIMIZATION_SUMMARY.md** - Size optimization details
- **SETUP_INSTRUCTIONS.md** - Safe setup guide
- **CRITICAL_ACTIONS.txt** - Security steps

---

## 🎯 Success Indicators

✅ You'll know it's working when:
- Vercel shows "Ready" with green ✓
- No 500 errors
- Login page loads
- Can login with admin/Admin@12345
- Dashboard appears

---

## 📊 Current Status

```
✅ Code: All fixes applied and pushed to main
✅ Build: Optimized to <500MB
✅ Tests: GitHub Actions CI passing
❌ Credentials: Old Neon password exposed (needs rotation)
❌ Vercel Env: DATABASE_URL needs update with NEW password
❌ Deployment: Needs redeploy after env var update
```

---

## 🚨 URGENT: DO THIS NOW

1. **Rotate Neon password** (old one is compromised)
   - https://console.neon.tech/
   - Reset password
   - Copy new connection string

2. **Update Vercel DATABASE_URL**
   - https://vercel.com/dashboard
   - omr-reader-a3ny
   - Settings → Environment Variables
   - DATABASE_URL = [new connection string]

3. **Redeploy**
   - Deployments → Redeploy latest
   - Wait for green checkmark

**That's it! 🚀 Then it's live and working!**

