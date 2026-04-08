#!/bin/zsh
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <to_email> <subject> <body_file>" >&2
  exit 1
fi

to_email="$1"
subject="$2"
body_file="$3"

if [[ ! -f "$body_file" ]]; then
  echo "Body file not found: $body_file" >&2
  exit 1
fi

gws gmail +send \
  --to "$to_email" \
  --subject "$subject" \
  --body "$(cat "$body_file")"
