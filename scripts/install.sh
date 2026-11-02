#!/usr/bin/env bash
# Homunculus machine setup for coding agents (Codex, Claude Code, Cursor).
# Idempotent; works on macOS (bash 3.2) and Linux. Steps:
#
#   1. Global instructions, generated from agentic/AGENTS.md:
#        Codex        ~/.codex/AGENTS.md
#        Claude Code  ~/.claude/CLAUDE.md
#        Cursor       ~/.cursor/rules/homunculus-global.mdc (alwaysApply)
#   2. Skills. pstack-derived = aliases in skill-aliases.yml whose source is
#      cursor/plugins.
#        Claude Code  non-pstack Homunculus skills (~/.claude/skills)
#        Cursor       non-pstack Homunculus skills (~/.agents/skills; native pstack plugin)
#        Codex        full Homunculus set under ~/.codex/skills (the skills CLI
#                     cannot give Codex pstack copies without also exposing
#                     them to Cursor via the shared ~/.agents/skills store)
#   3. pstack Claude Code plugin.
#   4. MCP servers from agentic/mcp-servers.json, only for detected tools.
#      Skipped automatically on a Grok Bot machine.
#
# One-liner (fetches a pinned copy into ~/.homunculus, reruns update it):
#   curl -fsSL https://raw.githubusercontent.com/ben196888/homunculus/main/scripts/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --yes --dry-run
#
# Run ./scripts/install.sh --help for flags.

set -euo pipefail

ORIG_ARGS=("$@")
REPO_URL="${HOMUNCULUS_REPO_URL:-https://github.com/ben196888/homunculus.git}"
REF="${HOMUNCULUS_REF:-main}"
INSTALL_HOME="${HOMUNCULUS_HOME:-${HOME}/.homunculus}"
GROK_BOT_MARKER="${HOMUNCULUS_GROK_BOT_MARKER:-/home/box/agent-data}"
CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
CURSOR_DIR="${HOME}/.cursor"

usage() {
  cat <<'EOF'
Usage: install.sh [options] [SOURCE]

Set up Codex, Claude Code, and Cursor on this machine. Safe to rerun.

SOURCE is where skills are installed from: a local checkout path, "." for
this checkout, or github.com/ben196888/homunculus (default when run from a
checkout; the one-liner uses its ~/.homunculus copy).

Options:
  -n, --dry-run        Print what would change; write nothing
  -y, --yes            Never prompt; use defaults (merge) for differing files
      --merge          Differing instruction files: back up, then put the
                       Homunculus block on top and keep existing content below
      --overwrite      Differing instruction files: back up, then replace
      --skip           Differing instruction files: leave untouched
      --tools LIST     Comma-separated subset of codex,claude,cursor
                       (default: all three)
      --source SOURCE  Same as the SOURCE argument
      --ref REF        Git ref for the ~/.homunculus copy (default: main;
                       env HOMUNCULUS_REF)
      --no-instructions  Skip global AGENTS.md / CLAUDE.md / Cursor rule
      --no-skills      Skip skill installation
      --no-plugin      Skip the pstack Claude Code plugin
      --no-mcp         Skip MCP configuration
      --mcp            Configure MCP even on a Grok Bot machine
  -h, --help           Show this help

Environment:
  HOMUNCULUS_HOME          Checkout used by the one-liner (default ~/.homunculus)
  HOMUNCULUS_REF           Same as --ref
  HOMUNCULUS_REPO_URL      Git URL for the one-liner checkout
  HOMUNCULUS_GROK_BOT      1 forces Grok Bot mode (MCP skipped), 0 disables
                           detection; unset = detect via /home/box/agent-data
  CODEX_HOME, CLAUDE_CONFIG_DIR  Respected for Codex / Claude Code paths
EOF
}

die() {
  echo "install.sh: $*" >&2
  exit 1
}

DRY_RUN=0
MODE=ask
YES=0
SOURCE=""
TOOLS="codex,claude,cursor"
DO_INSTRUCTIONS=1
DO_SKILLS=1
DO_PLUGIN=1
MCP=auto

while [ "$#" -gt 0 ]; do
  case "$1" in
    -n|--dry-run) DRY_RUN=1 ;;
    -y|--yes) YES=1 ;;
    --merge) MODE=merge ;;
    --overwrite) MODE=overwrite ;;
    --skip) MODE=skip ;;
    --tools) [ "$#" -ge 2 ] || die "--tools needs a value"; TOOLS="$2"; shift ;;
    --tools=*) TOOLS="${1#*=}" ;;
    --source) [ "$#" -ge 2 ] || die "--source needs a value"; SOURCE="$2"; shift ;;
    --source=*) SOURCE="${1#*=}" ;;
    --ref) [ "$#" -ge 2 ] || die "--ref needs a value"; REF="$2"; shift ;;
    --ref=*) REF="${1#*=}" ;;
    --no-instructions) DO_INSTRUCTIONS=0 ;;
    --no-skills) DO_SKILLS=0 ;;
    --no-plugin) DO_PLUGIN=0 ;;
    --no-mcp) MCP=off ;;
    --mcp) MCP=on ;;
    -h|--help) usage; exit 0 ;;
    -*) usage >&2; die "unknown option: $1" ;;
    *) SOURCE="$1" ;;
  esac
  shift
done

for tool in $(echo "${TOOLS}" | tr ',' ' '); do
  case "${tool}" in
    codex|claude|cursor) ;;
    *) die "unknown tool in --tools: ${tool} (expected codex, claude, cursor)" ;;
  esac
done

if [ "${YES}" = 1 ] && [ "${MODE}" = ask ]; then
  MODE=merge
fi

want() {
  case ",${TOOLS}," in
    *",$1,"*) return 0 ;;
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# Bootstrap: when piped from curl (or run from outside a checkout), fetch a
# pinned copy into ${INSTALL_HOME} and rerun from there.
# ---------------------------------------------------------------------------

ROOT=""
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [ -n "${SCRIPT_PATH}" ] && [ -f "${SCRIPT_PATH}" ]; then
  ROOT="$(cd "$(dirname "${SCRIPT_PATH}")/.." && pwd)"
fi

is_checkout() {
  [ -n "$1" ] && [ -f "$1/agentic/AGENTS.md" ] && [ -f "$1/skill-aliases.yml" ] \
    && [ -f "$1/scripts/agent_setup.py" ]
}

fetch_ref() {
  git -C "$1" fetch --quiet --depth 1 origin "${REF}"
  git -C "$1" checkout --quiet --detach FETCH_HEAD
}

bootstrap() {
  [ -z "${HOMUNCULUS_BOOTSTRAPPED:-}" ] || die "${INSTALL_HOME} at ${REF} is not a usable Homunculus checkout"
  command -v git >/dev/null 2>&1 || die "git is required for the one-liner (macOS: xcode-select --install)"
  local dir="${INSTALL_HOME}"
  local temp=""

  if [ -d "${dir}/.git" ]; then
    if [ "${DRY_RUN}" = 1 ]; then
      echo "[dry-run] would update ${dir} to ${REF}; planning from its current copy"
    elif [ -n "$(git -C "${dir}" status --porcelain)" ]; then
      echo "Warning: ${dir} has local changes; not updating it. Running the existing copy."
    else
      echo "Updating ${dir} to ${REF}"
      git -C "${dir}" remote set-url origin "${REPO_URL}"
      fetch_ref "${dir}"
    fi
  else
    if [ "${DRY_RUN}" = 1 ]; then
      temp="$(mktemp -d)"
      dir="${temp}"
      echo "[dry-run] would clone ${REPO_URL}@${REF} into ${INSTALL_HOME}; planning from a temp copy"
    else
      echo "Fetching ${REPO_URL}@${REF} into ${dir}"
      [ ! -e "${dir}" ] || [ -z "$(ls -A "${dir}")" ] || die "${dir} exists and is not a git checkout; move it aside or set HOMUNCULUS_HOME"
    fi
    git init --quiet "${dir}"
    git -C "${dir}" remote add origin "${REPO_URL}"
    fetch_ref "${dir}"
  fi
  echo "Homunculus $(git -C "${dir}" rev-parse --short HEAD) at ${dir}"

  local status=0
  HOMUNCULUS_BOOTSTRAPPED=1 bash "${dir}/scripts/install.sh" --source "${dir}" \
    ${ORIG_ARGS[@]+"${ORIG_ARGS[@]}"} || status=$?
  if [ -n "${temp}" ]; then
    rm -rf "${temp}"
  fi
  exit "${status}"
}

if ! is_checkout "${ROOT}"; then
  bootstrap
fi

SOURCE="${SOURCE:-github.com/ben196888/homunculus}"
if [ "${SOURCE}" = "." ]; then
  SOURCE="${ROOT}"
fi

# Detect tools by binary on PATH or installed app bundle only. Never by
# ~/.codex, ~/.claude or ~/.cursor: this script creates those itself, so
# using them would make MCP eligibility differ between the first and second run.
has() { command -v "$1" >/dev/null 2>&1; }
has_app() { [ -d "/Applications/$1.app" ] || [ -d "${HOME}/Applications/$1.app" ]; }
HAS_CODEX=0; HAS_CLAUDE=0; HAS_CURSOR=0
if has codex || has_app Codex; then HAS_CODEX=1; fi
if has claude; then HAS_CLAUDE=1; fi
if has cursor || has cursor-agent || has_app Cursor; then HAS_CURSOR=1; fi

is_grok_bot() {
  case "${HOMUNCULUS_GROK_BOT:-}" in
    1|true|yes) return 0 ;;
    0|false|no) return 1 ;;
  esac
  [ -d "${GROK_BOT_MARKER}" ]
}

DRY_FLAG=""
if [ "${DRY_RUN}" = 1 ]; then
  DRY_FLAG="--dry-run"
  echo "Dry run: nothing will be written."
fi

run() {
  if [ "${DRY_RUN}" = 1 ]; then
    echo "[dry-run] would run: $*"
  else
    "$@"
  fi
}

setup_py() {
  python3 "${ROOT}/scripts/agent_setup.py" "$@"
}

# ---------------------------------------------------------------------------
# 1. Global instructions
# ---------------------------------------------------------------------------

install_instructions() {
  echo ""
  echo "==> Global instructions (from ${ROOT}/agentic/AGENTS.md)"
  if want codex; then
    setup_py instructions --tool codex --dest "${CODEX_DIR}/AGENTS.md" --mode "${MODE}" ${DRY_FLAG}
  fi
  if want claude; then
    setup_py instructions --tool claude --dest "${CLAUDE_DIR}/CLAUDE.md" --mode "${MODE}" ${DRY_FLAG}
  fi
  if want cursor; then
    setup_py instructions --tool cursor --dest "${CURSOR_DIR}/rules/homunculus-global.mdc" --mode "${MODE}" ${DRY_FLAG}
  fi
}

# ---------------------------------------------------------------------------
# 2. Skills
# ---------------------------------------------------------------------------

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
  if [ "$#" -eq 0 ]; then
    echo "No skills to install for ${agent}; skipping."
    return 0
  fi
  if ! has npx; then
    echo "Skipping ${agent} skills via the skills CLI: npx not on PATH (install Node.js, then rerun)."
    return 0
  fi
  run npx -y skills add "${SOURCE}" --skill "$@" --agent "${agent}" --copy -g -y
}

sync_codex_skills() {
  # Mirror every Homunculus skill into ${CODEX_DIR}/skills/<public-name>/.
  # Codex natively reads $CODEX_HOME/skills (default ~/.codex/skills).
  python3 - "$ROOT" "${CODEX_DIR}/skills" "${DRY_RUN}" <<'PY'
import filecmp
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
dest_root = Path(sys.argv[2])
dry_run = sys.argv[3] == "1"
sys.path.insert(0, str(root / "scripts"))
import skill_alias  # noqa: E402


def same_tree(a: Path, b: Path) -> bool:
    if not b.is_dir():
        return False
    cmp = filecmp.dircmp(a, b, ignore=[".git"])
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs)


wanted: set[str] = set()
for skill_file in sorted((root / "skills").rglob("SKILL.md")):
    name = skill_alias.frontmatter_name(skill_file)
    wanted.add(name)
    src = skill_file.parent
    dest = dest_root / name
    if same_tree(src, dest):
        continue
    if dry_run:
        print(f"[dry-run] would sync {name} → {dest}")
        continue
    dest_root.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git"))
    print(f"Synced {name} → {dest}")

# Drop stale Homunculus skills no longer in the repo.
if dest_root.is_dir():
    for child in list(dest_root.iterdir()):
        if child.is_dir() and child.name.startswith("homunculus-") and child.name not in wanted:
            if dry_run:
                print(f"[dry-run] would remove stale {child}")
                continue
            shutil.rmtree(child)
            print(f"Removed stale {child}")
print(f"Codex skills in sync ({len(wanted)}) at {dest_root}")
PY
}

install_all_skills() {
  echo ""
  echo "==> Skills from: ${SOURCE}"
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

  if want claude; then
    echo ""
    echo "==> claude-code (non-pstack Homunculus skills)"
    install_skills claude-code ${NON_PSTACK_ARR[@]+"${NON_PSTACK_ARR[@]}"}
  fi

  if want cursor; then
    echo ""
    echo "==> cursor (non-pstack Homunculus skills; universal store)"
    install_skills cursor ${NON_PSTACK_ARR[@]+"${NON_PSTACK_ARR[@]}"}
  fi

  if want codex; then
    echo ""
    echo "==> codex (full set → ${CODEX_DIR}/skills)"
    # Ensure Codex is detectable by the skills CLI on later runs.
    run mkdir -p "${CODEX_DIR}"
    sync_codex_skills
    # Also register non-pstack via skills CLI when possible (shared store; no pstack).
    install_skills codex ${NON_PSTACK_ARR[@]+"${NON_PSTACK_ARR[@]}"} || true
  fi
}

# ---------------------------------------------------------------------------
# 3. pstack Claude Code plugin
# ---------------------------------------------------------------------------

install_pstack_plugin() {
  echo ""
  echo "==> Claude Code pstack plugin"
  if ! has claude; then
    echo "Skipping pstack Claude Code plugin: claude not on PATH."
    echo "Install Claude Code, then rerun this script (or run the two commands below)."
    echo "  claude plugin marketplace add cursor/plugins"
    echo "  claude plugin install pstack@cursor-plugins -y"
    return 0
  fi

  # Dry run never invokes claude: even read-only subcommands create ~/.claude.json.
  if [ "${DRY_RUN}" = 1 ]; then
    echo "[dry-run] would run (unless already configured): claude plugin marketplace add cursor/plugins"
    echo "[dry-run] would run: claude plugin install pstack@cursor-plugins -y"
    return 0
  fi

  if ! claude plugin marketplace list 2>/dev/null | grep -qiE 'cursor/plugins|cursor-plugins'; then
    echo "Adding cursor/plugins marketplace..."
    if ! run claude plugin marketplace add cursor/plugins; then
      echo "Note: marketplace add failed; continuing. Install pstack manually if needed."
    fi
  else
    echo "cursor/plugins marketplace already configured."
  fi

  if run claude plugin install pstack@cursor-plugins -y; then
    [ "${DRY_RUN}" = 1 ] || echo "pstack@cursor-plugins installed."
  else
    echo "Note: pstack plugin install failed (Claude may need a signed-in session)."
    echo "Retry after 'claude auth login', or run:"
    echo "  claude plugin install pstack@cursor-plugins -y"
  fi
}

# ---------------------------------------------------------------------------
# 4. MCP servers (detected tools only)
# ---------------------------------------------------------------------------

configure_mcp() {
  echo ""
  echo "==> MCP servers (from ${ROOT}/agentic/mcp-servers.json)"
  if [ "${MCP}" = off ]; then
    echo "Skipping MCP: --no-mcp."
    return 0
  fi
  if [ "${MCP}" = auto ] && is_grok_bot; then
    echo "Skipping MCP: Grok Bot machine detected (it supplies its own connectors). Use --mcp to force."
    return 0
  fi

  if want codex; then
    if [ "${HAS_CODEX}" = 1 ]; then
      setup_py mcp-codex --config "${CODEX_DIR}/config.toml" ${DRY_FLAG}
    else
      echo "Codex not detected; skipping its MCP config."
    fi
  fi
  if want claude; then
    if [ "${HAS_CLAUDE}" = 1 ]; then
      setup_py mcp-claude ${DRY_FLAG}
    else
      echo "Claude Code CLI not detected; skipping its MCP config."
    fi
  fi
  if want cursor; then
    if [ "${HAS_CURSOR}" = 1 ]; then
      setup_py mcp-cursor --config "${CURSOR_DIR}/mcp.json" ${DRY_FLAG}
    else
      echo "Cursor not detected; skipping its MCP config."
    fi
  fi
}

echo "Homunculus agent setup (tools: ${TOOLS})"

if [ "${DO_INSTRUCTIONS}" = 1 ]; then
  install_instructions
fi
if [ "${DO_SKILLS}" = 1 ]; then
  install_all_skills
fi
if [ "${DO_PLUGIN}" = 1 ] && want claude; then
  install_pstack_plugin
fi
configure_mcp

echo ""
echo "Done."
