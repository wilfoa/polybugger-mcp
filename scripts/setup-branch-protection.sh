#!/bin/bash
# Setup branch protection rules for the repository
# Requires: gh CLI authenticated with repo admin access
#
# Usage: ./scripts/setup-branch-protection.sh [owner/repo]

set -e

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

echo "Setting up branch protection for: $REPO"

# Enable branch protection on main
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO/branches/main/protection" \
  -f required_status_checks='{"strict":true,"contexts":["CI Success"]}' \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  -f restrictions=null \
  -f required_conversation_resolution=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false

echo "Branch protection enabled!"
echo ""
echo "Protected branch 'main' now requires:"
echo "  - 'CI Success' status check to pass"
echo "  - 1 approving review"
echo "  - Up-to-date branch before merging"
echo "  - Resolved conversations"
