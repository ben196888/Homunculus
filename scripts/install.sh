#!/usr/bin/env bash
# Install Homunculus skills so each harness gets one copy of pstack-derived skills.
#
# pstack-derived = aliases in skill-aliases.yml whose source is cursor/plugins.
#
#   Claude Code  — non-pstack Homunculus skills + pstack Claude Code plugin
#   Cursor       — non-pstack Homunculus skills only (native pstack plugin)
#   Codex        — full Homunculus set under ~/.codex/skills (skills CLI cannot
#                  give Codex pstack copies without also exposing them to Cursor,
#                  because both use the universal ~/.agents/skills store)
#
# Safe to rerun: strips leftover Homunculus pstack copies from Claude Code and
# the universal agents store before reinstalling.
#
# Usage:
#   ./scripts/install.sh                  # skills from github.com/ben196888/homunculus
#   ./scripts/install.sh /path/to/clone   # skills from a local checkout
#   ./scripts/install.sh .                # skills from this repo
#
# Requires network the first time npx fetches `skills`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:-github.com/ben196888/homunculus}"

if [[ "${SOURCE}" == "." ]]; then
  SOURCE="${ROOT}"
fi

list_skill_sets() {
  # Prints three lines to stdout (values single-quoted for safe eval):
  #   PSTACK='...'
  #   NON_PSTACK='...'
  #   ALL='...'
  python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
import skill_alias  # noqa: E402

skill_alias.REPO_ROOT = root
skill_alias.MANIFEST_PATH = root / "skill-aliases.yml"
skill_alias.SKILLS_ROOT = root / "skills"

manifest = skill_alias.read_manifest()
pstack = {
    skill_alias.generated_skill_name(manifest.namespace, alias)
    for alias, cfg in manifest.aliases.items()
    if cfg.source == "cursor/plugins"
}

all_names: list[str] = []
for skill_file in sorted((root / "skills").rglob("SKILL.md")):
    all_names.append(skill_alias.frontmatter_name(skill_file))

missing = sorted(pstack - set(all_names))
if missing:
    raise SystemExit(
        "skill-aliases.yml lists cursor/plugins skills not present under skills/: "
        + ", ".join(missing)
    )

non_pstack = [name for name in all_names if name not in pstack]
pstack_ordered = [name for name in all_names if name in pstack]


def render(names: list[str]) -> str:
    joined = " ".join(names)
    escaped = joined.replace("'", "'\\''")
    return f"'{escaped}'"


print(f"PSTACK={render(pstack_ordered)}")
print(f"NON_PSTACK={render(non_pstack)}")
print(f"ALL={render(all_names)}")
PY
}

install_skills() {
  local agent="$1"
  shift
  local skills=("$@")
  if [[ ${#skills[@]} -eq 0 ]]; then
    echo "No skills to install for ${agent}; skipping."
    return 0
  fi
  npx -y skills add "${SOURCE}" --skill "${skills[@]}" --agent "${agent}" --copy -g -y
}

sync_codex_skills() {
  # Mirror every Homunculus skill into ~/.codex/skills/<public-name>/.
  # Codex natively reads $CODEX_HOME/skills (default ~/.codex/skills).
  python3 - "$ROOT" "${HOME}/.codex/skills" <<'PY'
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
dest_root = Path(sys.argv[2])
sys.path.insert(0, str(root / "scripts"))
import skill_alias  # noqa: E402

dest_root.mkdir(parents=True, exist_ok=True)
wanted: set[str] = set()

for skill_file in sorted((root / "skills").rglob("SKILL.md")):
    name = skill_alias.frontmatter_name(skill_file)
    wanted.add(name)
    src = skill_file.parent
    dest = dest_root / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git"))
    print(f"Synced {name} → {dest}")

# Drop stale Homunculus skills no longer in the repo.
for child in list(dest_root.iterdir()):
    if child.is_dir() and child.name.startswith("homunculus-") and child.name not in wanted:
        shutil.rmtree(child)
        print(f"Removed stale {child}")
PY
}

echo "Installing Homunculus skills from: ${SOURCE}"
echo "Reading pstack exclusion list from ${ROOT}/skill-aliases.yml (source: cursor/plugins)"

eval "$(list_skill_sets)"

# shellcheck disable=SC2206
PSTACK_ARR=( ${PSTACK} )
# shellcheck disable=SC2206
NON_PSTACK_ARR=( ${NON_PSTACK} )
# shellcheck disable=SC2206
ALL_ARR=( ${ALL} )

echo "pstack-derived skills (plugin on Claude Code / Cursor): ${#PSTACK_ARR[@]}"
echo "non-pstack Homunculus skills: ${#NON_PSTACK_ARR[@]}"
echo "all Homunculus skills (Codex ~/.codex/skills): ${#ALL_ARR[@]}"

echo ""
echo "==> claude-code (non-pstack Homunculus skills)"
install_skills claude-code "${NON_PSTACK_ARR[@]}"

echo ""
echo "==> cursor (non-pstack Homunculus skills; universal store)"
install_skills cursor "${NON_PSTACK_ARR[@]}"

echo ""
echo "==> codex (full set → ~/.codex/skills)"
# Ensure Codex is detectable by the skills CLI on later runs.
mkdir -p "${HOME}/.codex"
sync_codex_skills
# Also register non-pstack via skills CLI when possible (shared store; no pstack).
install_skills codex "${NON_PSTACK_ARR[@]}" || true

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
