#!/usr/bin/env bash
# Remove refs/original backup refs that can contain the large odc.mv.db file.
# When the IDE pushes "all refs", GitHub rejects because of that. This script
# only deletes those backup refs. Run from repo root. Then: git push origin main

set -e
cd "$(git rev-parse --show-toplevel)"

echo "=== Removing refs/original (backup refs that may contain the large file) ==="
git for-each-ref --format='%(refname)' refs/original/ 2>/dev/null | while read ref; do
  git update-ref -d "$ref"
  echo "  deleted $ref"
done || true

echo ""
echo "=== Done. Now run: ==="
echo "  git push origin main"
