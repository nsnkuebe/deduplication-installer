#!/usr/bin/env bash
# Creates milestones and issues from ISSUES.md using the GitHub CLI.
# Usage: gh auth login && ./scripts/create_issues.sh OWNER/REPO
set -euo pipefail
REPO="${1:?usage: create_issues.sh OWNER/REPO}"
milestone=""
while IFS= read -r line; do
  if [[ "$line" =~ ^##\ (M[0-9]+\ -\ .*)$ ]]; then
    milestone="${BASH_REMATCH[1]}"
    gh api "repos/$REPO/milestones" -f title="$milestone" >/dev/null
    echo "milestone: $milestone"
  elif [[ "$line" =~ ^-\ (.*)$ && -n "$milestone" ]]; then
    title="${BASH_REMATCH[1]}"
    [[ "$title" == *"*(done)*" ]] && continue
    gh issue create --repo "$REPO" --title "$title" --milestone "$milestone" --body "Part of $milestone. See docs/manifest-spec.md." >/dev/null
    echo "  issue: $title"
  fi
done < ISSUES.md
