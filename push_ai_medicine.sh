#!/bin/bash
# Commit and push AI-Medicine (and any other changes) to git.
# Run from repo root: ./push_ai_medicine.sh

set -e
cd "$(dirname "$0")"

echo "Adding changes..."
git add AI-Medicine/ .gitignore push_ai_medicine.sh
git add -u
git status --short

echo ""
read -p "Commit message [AI-Medicine: add project and docs]: " msg
msg="${msg:-AI-Medicine: add project and docs}"
git commit -m "$msg"

echo "Pushing to origin main..."
git push origin main
echo "Done."
