#!/usr/bin/env bash
# Install every Homunculus skill globally for Claude Code, Codex, and Cursor.
# Optionally install the full pstack Claude Code plugin (subagent workflows).
#
# Usage:
#   ./scripts/install.sh                  # from github.com/ben196888/homunculus
#   ./scripts/install.sh /path/to/clone   # from a local checkout
#   ./scripts/install.sh .                # from this repo
#
# Safe to rerun. Requires network access the first time npx fetches `skills`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:-github.com/ben196888/homunculus}"

if [[ "${SOURCE}" == "." ]]; then
  SOURCE="${ROOT}"
fi

AGENTS=(claude-code codex cursor)

echo "Installing Homunculus skills from: ${SOURCE}"
for agent in "${AGENTS[@]}"; do
  echo ""
  echo "==> ${agent}"
  npx -y skills add "${SOURCE}" --skill '*' --agent "${agent}" --copy -g -y
done

echo ""
if ! command -v claude >/dev/null 2>&1; then
  echo "Skipping pstack Claude Code plugin: claude not on PATH."
  echo "Install Claude Code, then rerun this script (or run the two commands below)."
  echo "  claude plugin marketplace add cursor/plugins"
  echo "  claude plugin install pstack@cursor-plugins -y"
  exit 0
fi

echo "==> Claude Code pstack plugin"
if ! claude plugin marketplace list 2>/dev/null | grep -qiE 'cursor/plugins|cursor-plugins'; then
  echo "Adding cursor/plugins marketplace..."
  if ! claude plugin marketplace add cursor/plugins; then
    echo "Note: marketplace add failed; continuing. Install pstack manually if needed."
  fi
else
  echo "cursor/plugins marketplace already configured."
fi

if claude plugin install pstack@cursor-plugins -y; then
  echo "Installed pstack@cursor-plugins."
else
  echo "Note: pstack plugin install failed (Claude may need a signed-in session)."
  echo "Retry after 'claude auth login', or run:"
  echo "  claude plugin install pstack@cursor-plugins -y"
fi

echo ""
echo "Done."
