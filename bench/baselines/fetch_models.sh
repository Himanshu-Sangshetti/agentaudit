#!/usr/bin/env bash
# Download the pinned baseline model revisions into data/raw/models/ (plain HTTPS, no custom code).
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p data/raw/models
for spec in \
  "protectai/deberta-v3-base-prompt-injection-v2@90c9989b1a342275dd0d1a95aad283c04e075671" \
  "deepset/deberta-v3-base-injection@80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1"; do
  repo=${spec%@*}; rev=${spec#*@}; dir=data/raw/models/$(basename "$repo")
  mkdir -p "$dir"
  files=$(curl -s "https://huggingface.co/api/models/$repo/revision/$rev" | python3 -I -c \
    "import sys,json;print(' '.join(s['rfilename'] for s in json.load(sys.stdin)['siblings'] if s['rfilename'].endswith(('.json','.model','.safetensors','.txt')) and '/' not in s['rfilename']))")
  for f in $files; do
    [ -s "$dir/$f" ] || curl -sL --fail -o "$dir/$f" "https://huggingface.co/$repo/resolve/$rev/$f"
  done
done
