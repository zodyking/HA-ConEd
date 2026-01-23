#!/bin/bash
set -e

cd /Users/zodyking/Documents/coned-scraper

echo "=== Step 1: Initializing Git ==="
if [ ! -d .git ]; then
    git init
    echo "Git repository initialized"
else
    echo "Git repository already exists"
fi

echo ""
echo "=== Step 2: Setting up remote ==="
if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin https://github.com/zodyking/coned-scraper.git
    echo "Remote URL updated"
else
    git remote add origin https://github.com/zodyking/coned-scraper.git
    echo "Remote added"
fi

echo ""
echo "=== Step 3: Staging all files ==="
git add -A
echo "Files staged"

echo ""
echo "=== Step 4: Checking status ==="
git status --short | head -20

echo ""
echo "=== Step 5: Committing ==="
git commit -m "Initial commit: Home Assistant addon repository with MQTT sensor integration" || echo "Nothing to commit or commit failed"

echo ""
echo "=== Step 6: Setting main branch ==="
git branch -M main

echo ""
echo "=== Step 7: Pushing to GitHub ==="
echo "Pushing to https://github.com/zodyking/coned-scraper.git"
git push -u origin main

echo ""
echo "=== Done! ==="
echo "Repository pushed to: https://github.com/zodyking/coned-scraper"
