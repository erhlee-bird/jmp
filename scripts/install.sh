#!/bin/bash
source "$(dirname $BASH_SOURCE)/opts.sh"

mkdir -p "$COMP_DIR"
ln -fns "$(pwd)/jmp_completion" "$COMP_DIR"
echo "source $(pwd)/jmp" >> "$BASHRC_FILE"
