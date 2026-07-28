#!/usr/bin/env bash
# Verify the ProofPress ledger of every tracked Markdown file that carries one.
#
# Documentation in this repository uses the `portable` policy: each file's
# history travels inside the file as a capsule, and the local git ledger ref is
# only a cache. A fresh clone therefore has no ledger, so import the capsule
# before verifying instead of requiring every contributor to do it by hand.
#
# Files are discovered by their capsule marker, so adding a new ledgered
# document needs no change here.

set -euo pipefail

cd "$(dirname "$0")/.."

# `proofpress import` writes ledger events with `git commit-tree`, which
# refuses to run without a configured identity. Set one scoped to this
# checkout only, and only if the environment has none (CI runners have none
# by default; a contributor's own identity is left untouched).
git config user.email >/dev/null 2>&1 || git config user.email "proofpress-ci@localhost"
git config user.name >/dev/null 2>&1 || git config user.name "ProofPress CI"

status=0
found=0

while IFS= read -r file; do
  grep -q 'proofpress:capsule' "$file" || continue
  found=$((found + 1))
  npx --no-install proofpress import "$file" >/dev/null
  # 0 = claims verified, 2 = version carries no claims to check. Anything else
  # is a real mismatch between the file and its recorded history.
  set +e
  npx --no-install proofpress verify "$file"
  code=$?
  set -e
  if [ "$code" -ne 0 ] && [ "$code" -ne 2 ]; then
    echo "FAILED ($code): $file" >&2
    status=1
  fi
done < <(git ls-files '*.md')

if [ "$found" -eq 0 ]; then
  echo "no ProofPress-ledgered Markdown found" >&2
  exit 1
fi

echo "verified $found ledgered document(s)"
exit "$status"
