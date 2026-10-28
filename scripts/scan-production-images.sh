#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${TRIVY_IMAGE:?TRIVY_IMAGE is required}"

report_dir="$RUNNER_TEMP/security-images"
cache_dir="$RUNNER_TEMP/trivy-cache"

mkdir -p "$report_dir" "$cache_dir"

docker pull "$TRIVY_IMAGE"

status=0

for component in backend worker frontend; do
  image="penflow-$component:$IMAGE_TAG"

  if docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$report_dir:/reports" \
    -v "$cache_dir:/root/.cache/trivy" \
    "$TRIVY_IMAGE" image \
    --image-src docker \
    --scanners vuln \
    --ignorefile /dev/null \
    --timeout 10m \
    --exit-code 0 \
    --format json \
    --output "/reports/$component.json" \
    "$image"; then

    if ! python3 - "$report_dir/$component.json" "$component" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
results = data.get("Results")

if not results or not any(
    item.get("Class") == "os-pkgs"
    for item in results
):
    raise SystemExit(
        "Incomplete image scan: expected OS package results"
    )

blocked = [
    (result.get("Target"), vulnerability)
    for result in results
    for vulnerability in result.get("Vulnerabilities", [])
    if vulnerability.get("Severity") in {"HIGH", "CRITICAL"}
]

for target, item in blocked:
    print(
        f"{sys.argv[2]}: {item['VulnerabilityID']} "
        f"{item['Severity']} {item['PkgName']} "
        f"installed={item['InstalledVersion']} "
        f"fixed={item.get('FixedVersion') or 'not available'} "
        f"target={target}"
    )

print(
    f"{sys.argv[2]}: {len(blocked)} blocking findings"
)

raise SystemExit(1 if blocked else 0)
PY
    then
      status=1
    fi
  else
    echo "::error::Trivy could not complete the $component image scan"
    status=1
  fi
done

exit "$status"