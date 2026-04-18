#!/usr/bin/env bash
# Build infra/lambda_layer.zip for Python 3.12 Lambda (compatible with local Python 3.11 dev machines).
# Requires Docker. See README "Deploy Lambda" for details.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING="${ROOT}/build/layer_staging"
TARGET="${STAGING}/python/lib/python3.12/site-packages"
OUT_ZIP="${ROOT}/infra/lambda_layer.zip"
IMAGE="${LAMBDA_LAYER_BUILD_IMAGE:-public.ecr.aws/sam/build-python3.12}"

rm -rf "${STAGING}"
mkdir -p "${TARGET}"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker not found. Install Docker Desktop or use Python 3.12 locally:" >&2
  echo "  python3.12 -m pip install -r requirements-lambda.txt -t ${TARGET}" >&2
  echo "  (cd build/layer_staging && zip -qr \"${OUT_ZIP}\" python)" >&2
  exit 1
fi

echo "Building layer with ${IMAGE} (linux/amd64 for default Lambda x86_64)..."
docker pull --platform linux/amd64 "${IMAGE}" >/dev/null

docker run --rm --platform linux/amd64 \
  -v "${ROOT}/requirements-lambda.txt:/requirements-lambda.txt:ro" \
  -v "${TARGET}:/target" \
  "${IMAGE}" \
  /bin/bash -c "pip install --no-cache-dir -r /requirements-lambda.txt -t /target"

(
  cd "${STAGING}"
  rm -f "${OUT_ZIP}"
  zip -qr "${OUT_ZIP}" python
)

echo "Wrote ${OUT_ZIP}"
