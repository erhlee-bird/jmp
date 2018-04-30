#!/bin/bash
set -e

function usage {
  echo "$(basename "$0") -p {PREFIX} -b {BASHRC_FILE}"
  echo "    PREFIX      = /usr/ \$HOME/prefix/ ..."
  echo "    BASHRC_FILE = \$HOME/.bashrc \$HOME/.basrc.local ..."
  exit 1
}

if [[ ! "$1" = "-p" ]] || [[ -z "$2" ]]; then
  usage
fi
PREFIX="$(dirname "$2/_")"
COMP_DIR="$PREFIX/share/bash-completion/completions"
shift; shift

if [[ ! "$1" = "-b" ]] || [[ -z "$2" ]]; then
  usage
fi
BASHRC_FILE="$2"
shift; shift

# Clean source line.
if [[ "$(uname)" = "Darwin" ]]; then
  sed -Ee "/source .*\/jmp/d" "$BASHRC_FILE" > "$BASHRC_FILE.new"
else
  sed -re "/source .*\/jmp/d" "$BASHRC_FILE" > "$BASHRC_FILE.new"
fi
mv "$BASHRC_FILE.new" "$BASHRC_FILE"
