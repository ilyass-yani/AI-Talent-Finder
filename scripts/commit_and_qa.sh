#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/commit_and_qa.sh "short message"
MSG=${1:-"feat: improve homepage + faq + contact"}
BRANCH=feature/homepage-improvements

git checkout -b "$BRANCH"
git add frontend/src/app/page.tsx frontend/src/app/api/contact/route.ts frontend/e2e/home.spec.ts
git commit -m "$MSG"
echo "Pushed changes to branch $BRANCH locally. Run:\n  git push -u origin $BRANCH"

cat <<'QA'
QA Checklist:
- [ ] Run frontend dev and verify visually (http://localhost:3000)
- [ ] Verify FAQ accordion opens and closes
- [ ] Submit contact form and check frontend/data/contacts.jsonl has entry
- [ ] Run Playwright tests: cd frontend && npx playwright test frontend/e2e/home.spec.ts
- [ ] Run lint and formatting
QA
