#!/usr/bin/env bash
set -e

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"

link_dir() {
  local target="$1"
  local parent
  parent="$(dirname "$target")"
  mkdir -p "$parent"

  if [ -L "$target" ]; then
    rm "$target"
  elif [ -d "$target" ]; then
    # Check if directory only contains dotfiles (.DS_Store, etc.)
    if [ -z "$(ls "$target")" ]; then
      rm -rf "$target"
    else
      echo "  Warning: $target is non-empty, symlinking individual skills instead."
      for dir in "$SKILLS_DIR"/*/; do
        [ -f "$dir/SKILL.md" ] || continue
        ln -sf "$dir" "$target/$(basename "$dir")"
        echo "  Linked $(basename "$dir")"
      done
      return
    fi
  fi

  ln -sf "$SKILLS_DIR" "$target"
  echo "  Linked $SKILLS_DIR -> $target"
}

install_claude() {
  echo "Installing for Claude Code..."
  link_dir "$HOME/.claude/skills"
}

install_gemini() {
  echo "Installing for Gemini CLI..."
  if command -v gemini &>/dev/null; then
    gemini skills link "$SKILLS_DIR" 2>/dev/null || link_dir "$HOME/.gemini/skills"
  else
    link_dir "$HOME/.gemini/skills"
  fi
}

install_codex() {
  echo "Installing for Codex CLI..."
  link_dir "$HOME/.agents/skills"
}

install_copilot() {
  echo "Installing for GitHub Copilot..."
  link_dir "$HOME/.copilot/skills"
}

# If args provided, install only selected agents
if [ $# -gt 0 ]; then
  for arg in "$@"; do
    case "$arg" in
      claude) install_claude ;;
      gemini) install_gemini ;;
      codex)   install_codex ;;
      copilot) install_copilot ;;
      *) echo "Unknown agent: $arg (options: claude, gemini, codex, copilot)" ;;
    esac
  done
  echo "Done!"
  exit 0
fi

# Interactive selection
echo "Select agents to install (space to toggle, enter to confirm):"
echo ""

agents=("claude" "gemini" "codex" "copilot")
selected=(true true true true)

# Check if running in interactive terminal
if [ ! -t 0 ]; then
  echo "Non-interactive mode: installing all agents."
  install_claude
  install_gemini
  install_codex
  install_copilot
  echo "Done!"
  exit 0
fi

render() {
  # Move cursor up to overwrite previous render
  if [ "${1:-}" = "refresh" ]; then
    printf "\033[%dA" "${#agents[@]}"
  fi
  for i in "${!agents[@]}"; do
    if [ "${selected[$i]}" = true ]; then
      marker="[x]"
    else
      marker="[ ]"
    fi
    if [ "$i" = "$cursor" ]; then
      echo "> $marker ${agents[$i]}"
    else
      echo "  $marker ${agents[$i]}"
    fi
  done
}

cursor=0
render

while true; do
  IFS= read -rsn1 key
  case "$key" in
    $'\x1b')
      read -rsn2 rest
      case "$rest" in
        '[A') cursor=$(( (cursor - 1 + ${#agents[@]}) % ${#agents[@]} )) ;;  # Up
        '[B') cursor=$(( (cursor + 1) % ${#agents[@]} )) ;;                  # Down
      esac
      ;;
    ' ')
      if [ "${selected[$cursor]}" = true ]; then
        selected[cursor]=false
      else
        selected[cursor]=true
      fi
      ;;
    '') break ;;  # Enter
  esac
  render refresh
done

echo ""

installed=false
for i in "${!agents[@]}"; do
  if [ "${selected[$i]}" = true ]; then
    case "${agents[$i]}" in
      claude) install_claude ;;
      gemini) install_gemini ;;
      codex)   install_codex ;;
      copilot) install_copilot ;;
    esac
    installed=true
  fi
done

if [ "$installed" = false ]; then
  echo "No agents selected."
else
  echo "Done!"
fi
