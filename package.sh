#!/bin/sh
# Builds ../ledger-eval.zip for upload. Refuses to build if anything looks like a live credential.
set -eu
cd "$(dirname "$0")"
if grep -rIlE 'sk-or-v1-[A-Za-z0-9]{8,}|sk-ant-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9]{32,}' --exclude=package.sh --exclude=.env . ; then
  echo "Possible key in the files above. Nothing was zipped." >&2
  exit 1
fi
rm -f ../ledger-eval.zip
cd ..
zip -qr ledger-eval.zip ledger-eval -x '*/.env' '*/__pycache__/*' '*/.venv/*' '*.DS_Store' '*/SUBMISSION_TODO.md'
du -h ledger-eval.zip
unzip -l ledger-eval.zip | grep -E '\.env$|\.mp4|\.mov' || true
