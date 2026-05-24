#!/usr/bin/env bash
# Executa o Clified via PyPI (clified-install) ou checkout local (dev).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=install-bootstrap.sh
source "$SCRIPT_DIR/install-bootstrap.sh"
clified_bootstrap "$@"
