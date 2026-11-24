#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SOURCE="$REPO_ROOT/agents/AGENTS.md"
COPILOT_DIR="$HOME/Library/Application Support/Code/User/prompts"
PI_DIR="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
SKILL_FILES=(
  code-review/SKILL.md
  security-review/SKILL.md
  essayist/SKILL.md
  essayist/references/writing-guide.md
)

backup_file() {
  local target="$1"
  local backup="$target.bak"
  local suffix=1

  if [[ -d "$target" ]]; then
    printf 'Refusing to replace directory: %s\n' "$target" >&2
    return 1
  fi
  while [[ -e "$backup" || -L "$backup" ]]; do
    backup="$target.bak.$suffix"
    suffix=$((suffix + 1))
  done
  mv "$target" "$backup"
  printf '  ↪ Backed up %s to %s\n' "$target" "$backup"
}

write_file() {
  local target="$1"
  local content
  content="$(cat)"

  if [[ -f "$target" ]] && [[ "$(cat "$target")" == "$content" ]]; then
    return
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    backup_file "$target"
  fi
  printf '%s\n' "$content" > "$target"
}

link_file() {
  local source="$1" target="$2"
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    return
  fi
  if [[ -f "$target" ]] && cmp -s "$source" "$target"; then
    rm "$target"
  elif [[ -e "$target" || -L "$target" ]]; then
    backup_file "$target"
  fi
  ln -s "$source" "$target"
}

[[ -f "$SOURCE" ]] || { printf 'Missing shared instructions: %s\n' "$SOURCE" >&2; exit 1; }
for file in "${SKILL_FILES[@]}"; do
  [[ -f "$REPO_ROOT/agents/skills/$file" ]] || { echo "❌ Missing managed skill file." >&2; exit 1; }
done
[[ "$PI_DIR" == /* ]] || { echo "❌ PI_CODING_AGENT_DIR must be an absolute path." >&2; exit 1; }
if [[ -e "$PI_DIR/AGENTS.override.md" || -L "$PI_DIR/AGENTS.override.md" ]]; then
  echo "❌ Pi AGENTS.override.md would hide the shared instructions. Review it before running setup." >&2
  exit 1
fi

echo "⚙️ Configuring shared agent instructions..."
mkdir -p "$HOME/.agents" "$HOME/.claude" "$HOME/.copilot" "$COPILOT_DIR" "$PI_DIR"
link_file "$SOURCE" "$HOME/.agents/AGENTS.md"
link_file "$HOME/.agents/AGENTS.md" "$PI_DIR/AGENTS.md"
link_file "$HOME/.agents/AGENTS.md" "$HOME/.copilot/copilot-instructions.md"
for file in "${SKILL_FILES[@]}"; do
  target="$HOME/.agents/skills/$file"
  mkdir -p "$(dirname "$target")"
  link_file "$REPO_ROOT/agents/skills/$file" "$target"
done

write_file "$HOME/.claude/CLAUDE.md" << 'EOF'
@~/.agents/AGENTS.md
EOF

write_file "$COPILOT_DIR/global.instructions.md" << EOF
---
description: "Shared personal instructions for work across repositories."
applyTo: "**"
---

Read and follow the [shared global instructions](<$HOME/.agents/AGENTS.md>) before working.
Repository-specific conventions add context without weakening shared safety rules, subject to the tool's higher-priority instructions.
EOF

echo "✅ Shared agent instructions and skills configured!"
