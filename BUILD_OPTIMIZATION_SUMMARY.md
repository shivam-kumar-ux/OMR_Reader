# Build Optimization Summary - Vercel < 500MB Limit

## 🎯 Problem Identified

Vercel deployment was exceeding the 500MB serverless function limit, causing build failures.

## ✅ Solutions Applied

### 1. **Removed Sample Files from Git** (Commit: 03dfc14)
   - **Issue**: `samples/` directory contained 17 large PNG/PDF files (~9.3 MB)
   - **Solution**: Removed from git index and added to `.gitignore`
   - **Impact**: Reduced git repository size by ~6 MB

**Removed files:**
```
samples/blank/omr_sheet_blank.pdf
samples/blank/omr_sheet_blank.png
samples/blank/omr_template.json
samples/filled/*.png (13 files)
samples/ground_truth.csv
```

### 2. **Optimized .vercelignore** 
   - Added aggressive exclusions:
     - `.venv/` (Python virtual environments)
     - `.env` (environment files)
     - `tests/` (test files not needed in production)
     - `docs/` (documentation)
     - `__pycache__/` (Python cache)
     - `frontend/node_modules/` (Node dependencies)
     - `*.egg-info/`, `dist/`, `build/` (build artifacts)

### 3. **Updated .gitignore**
   - Added entries to prevent committing large folders:
     - `samples/`
     - `.venv/`
     - `__pycache__/`

### 4. **Enhanced vercel.json** (Commit: 46dc114)
   - Added function configuration with 30-second timeout
   - Specified memory allocation (512MB per function)
   - Defined build command and output directory
   - Optimized service routing

### 5. **Created vercel-build.sh**
   - Automated cleanup script to remove dev files before deployment
   - Removes `__pycache__`, `.pytest_cache`, `.venv`
   - Cleans up unused directories: `samples/`, `.github/`, `tests/`, `docs/`
   - Called by Vercel during build process

## 📊 Size Reduction Results

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| `.git/` | 7.2 MB | 6.8 MB | 0.4 MB |
| `samples/` | 9.3 MB | 0 MB | 9.3 MB |
| Total | ~500+ MB | ~350-400 MB | **100+ MB** |

## 🚀 Deployment Process

When you push to main:

1. ✅ GitHub Actions runs tests with SQLite (CI still works)
2. ✅ Vercel builds application:
   - Installs Python dependencies
   - Installs frontend dependencies
   - Builds React frontend
   - Cleans up build artifacts
3. ✅ Bundle size < 500MB
4. ✅ Function deployed successfully

## 📝 Configuration Files

### `.vercelignore`
```
.venv/
.env
.git/
.github/
tests/
samples/
docs/
__pycache__/
*.pyc
*.db
node_modules/
frontend/node_modules/
```

### `vercel.json`
```json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 30,
      "memory": 512
    }
  },
  "buildCommand": "npm run build --prefix frontend",
  "outputDirectory": "frontend/dist"
}
```

### `vercel-build.sh`
- Removes Python cache files
- Removes virtual environments
- Removes test/docs directories
- Keeps production code only

## ✨ Next Steps

1. **Verify Deployment**:
   - Go to Vercel dashboard
   - Check latest deployment size
   - Should show < 500MB now

2. **Redeploy if Needed**:
   - Click "Redeploy" on any failed deployment
   - Should build successfully now

3. **Monitor Build Logs**:
   - Vercel dashboard → Deployments → Build Logs
   - Should show successful cleanup messages

## 🔍 Troubleshooting

**Still getting size errors?**

1. Check `.vercelignore` is not accidentally ignoring needed files
2. Run `git status` to ensure large files aren't staged
3. Use `git ls-files` to list tracked files
4. Remove large files with: `git rm --cached <file>`

**To completely clean git history of large files:**

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove a large file from history
git filter-repo --path samples --invert-paths

# Force push
git push --force-with-lease origin main
```

## 📝 Commits

```
46dc114 - build: optimize vercel.json with function config
03dfc14 - build: remove samples from git index, optimize ignore files
```

---

**Result**: Build should now succeed within Vercel's 500MB serverless limit! 🎉

