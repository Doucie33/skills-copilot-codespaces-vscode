#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="dist"
OUT_FILE="$OUT_DIR/LDIC-G.zip"
mkdir -p "$OUT_DIR"

zip -r "$OUT_FILE" \
  LDIC-G.md \
  ldic.py \
  ldic_validator.py \
  ldic_parser.py \
  ldic_compiler.py \
  ldic_runtime.py \
  examples \
  README.md \
  LICENSE \
  -x "*/__pycache__/*" "*.pyc" ".git/*" "dist/*"

echo "Archive créée: $OUT_FILE"
