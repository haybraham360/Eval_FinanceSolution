#!/bin/sh
# Vercel build for the Ledger-Eval Explorer: export the data from the repository, then build the static site.
# Works whether the Vercel project's Root Directory is the repository root or frontend/.
set -eu

START="$PWD"
if [ -d "$START/frontend" ] && [ -d "$START/scripts" ]; then ROOT="$START"; else ROOT="$(cd "$START/.." && pwd)"; fi

cd "$ROOT"
python3 scripts/export_explorer_data.py --out frontend/public/explorer-data.json
cd frontend
npm run build

# Vercel reads outputDirectory relative to where it started. If it started inside frontend/ but is using the
# root vercel.json (outputDirectory "frontend/dist"), put a copy where it will look.
if [ "$START" != "$ROOT" ] && [ ! -d "$START/frontend/dist" ]; then
  mkdir -p "$START/frontend"
  cp -R "$ROOT/frontend/dist" "$START/frontend/dist"
fi
