#!/bin/bash
# Vercel build script to minimize bundle size

echo "🔨 Building OMR Application for Vercel..."

# Build frontend
echo "📦 Building frontend..."
cd frontend
npm ci || npm install
npm run build
cd ..

# Clean up development files
echo "🧹 Cleaning up development files..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .venv -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove unnecessary directories
rm -rf samples/ 2>/dev/null || true
rm -rf .github/ 2>/dev/null || true
rm -rf tests/ 2>/dev/null || true
rm -rf docs/ 2>/dev/null || true
rm -rf .vscode/ 2>/dev/null || true

echo "✅ Build complete! Bundle ready for deployment"
