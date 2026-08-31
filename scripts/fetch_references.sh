#!/usr/bin/env bash
set -euo pipefail

INCLUDE_RESTRICTED=0
REFRESH=0
for arg in "$@"; do
  case "$arg" in
    --include-restricted) INCLUDE_RESTRICTED=1 ;;
    --refresh) REFRESH=1 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF_ROOT="$ROOT/_references"
mkdir -p "$REF_ROOT"

clone_or_refresh() {
  local name="$1"
  local url="$2"
  local branch="${3:-}"
  local dest="$REF_ROOT/$name"

  if [[ -d "$dest/.git" ]]; then
    if [[ "$REFRESH" -eq 1 ]]; then
      echo "[refresh] $name"
      git -C "$dest" fetch --depth 1 origin
      git -C "$dest" reset --hard origin/HEAD
    else
      echo "[skip] $name already exists. Use --refresh to update."
    fi
    return
  fi

  echo "[clone] $name"
  if [[ -n "$branch" ]]; then
    git clone --depth 1 --filter=blob:none --branch "$branch" "$url" "$dest"
  else
    git clone --depth 1 --filter=blob:none "$url" "$dest"
  fi
}

clone_or_refresh "cytoscape.js" "https://github.com/cytoscape/cytoscape.js.git"
clone_or_refresh "nhs-processmining" "https://github.com/nhsengland/ProcessMining.git"
clone_or_refresh "bpmn-js-examples" "https://github.com/bpmn-io/bpmn-js-examples.git"

if [[ "$INCLUDE_RESTRICTED" -eq 1 ]]; then
  echo "WARNING: GPL/AGPL/LGPL repos are read-only references. Review OPEN_SOURCE_REFERENCE_GUIDE.md."
  clone_or_refresh "pm4py" "https://github.com/process-intelligence-solutions/pm4py.git" "release"
  clone_or_refresh "apromore-core" "https://github.com/apromore/ApromoreCore.git"
  clone_or_refresh "cortado" "https://github.com/cortado-tool/cortado.git"
fi

echo
echo "References ready under: $REF_ROOT"
echo "Next: use templates/REFERENCE_ADOPTION_PROMPT.md with your AI coding agent."
