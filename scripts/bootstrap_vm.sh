#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv postgresql-client docker.io
curl -LsSf https://astral.sh/uv/install.sh | sh
echo "Bootstrap complete."
