#!/bin/bash
# Push everything to GitHub repository

cd /Users/zodyking/Documents/coned-scraper

echo "=== Initializing Git Repository ==="
git init

echo "=== Setting up remote ==="
git remote add origin https://github.com/zodyking/coned-scraper.git 2>/dev/null || git remote set-url origin https://github.com/zodyking/coned-scraper.git

echo "=== Staging all files ==="
git add -A

echo "=== Files staged: ==="
git status --short | head -30

echo ""
echo "=== Committing changes ==="
git commit -m "Initial commit: Home Assistant addon repository with MQTT sensor integration"

echo "=== Setting main branch ==="
git branch -M main

echo "=== Pushing to GitHub ==="
echo "Note: You may need to authenticate with GitHub"
git push -u origin main

echo ""
echo "=== Done! ==="
echo "Repository URL: https://github.com/zodyking/coned-scraper"

