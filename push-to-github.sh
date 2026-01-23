#!/bin/bash
# Git push script for ConEd Scraper

cd /Users/zodyking/Documents/coned-scraper

# Initialize git if needed
if [ ! -d .git ]; then
    git init
fi

# Add remote
git remote add origin https://github.com/zodyking/coned-scraper.git 2>/dev/null || git remote set-url origin https://github.com/zodyking/coned-scraper.git

# Stage all files
git add .

# Commit
git commit -m "Initial commit: Home Assistant addon with MQTT sensor integration"

# Set main branch
git branch -M main

# Push
git push -u origin main

echo "Done! Repository pushed to GitHub."

