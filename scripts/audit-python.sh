#!/usr/bin/env bash
set -euo pipefail

: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_JOB:?GITHUB_JOB is required}"

report_dir="$RUNNER_TEMP/security-$GITHUB_JOB"
audit_env="$RUNNER_TEMP/pip-audit-$GITHUB_JOB"
mkdir -p "$report_dir"

mapfile -t package_paths < <(python - <<'PY'
import sysconfig

for path in sorted({
    sysconfig.get_path("purelib"),
    sysconfig.get_path("platlib"),
}):
    print(path)
PY
)

python -m venv "$audit_env"

"$audit_env/bin/python" -m pip install \
  --disable-pip-version-check \
  'pip-audit==2.10.1'

args=()
for package_path in "${package_paths[@]}"; do
  args+=(--path "$package_path")
done

status=0
"$audit_env/bin/pip-audit" "${args[@]}" \
  --strict \
  --progress-spinner off \
  --format json \
  --output "$report_dir/pip-audit.json" || status=$?

python - "$report_dir/pip-audit.json" "$status" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

if not path.is_file():
    raise SystemExit("Audit failed: no report was generated")

data = json.loads(path.read_text())
dependencies = data["dependencies"]

if not dependencies:
    raise SystemExit(
        "Audit failed: no installed dependencies were collected"
    )

skipped = [
    item
    for item in dependencies
    if item.get("skip_reason")
]

if skipped:
    for item in skipped:
        print(
            f"Not audited: {item['name']}: "
            f"{item['skip_reason']}"
        )

    raise SystemExit(
        "Audit incomplete: review skipped packages"
    )

findings = sum(
    len(item.get("vulns", []))
    for item in dependencies
)

print(
    f"Audited {len(dependencies)} packages; "
    f"{findings} vulnerability findings"
)

if int(sys.argv[2]) != 0 or findings:
    raise SystemExit(1)
PY