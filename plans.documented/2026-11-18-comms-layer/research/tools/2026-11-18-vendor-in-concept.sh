#!/usr/bin/env bash
# Control: Instantly is a host name. It must not be a type in the oracle.
# Run from repo root. Prints counts. Never prints a secret.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
echo "=== oracle (control: Instantly as a type should be 0) ==="
rg -n -w 'InstantlyComms|type Instantly' leadqualifier/workitem.fsx && echo FAIL || echo "workitem.fsx InstantlyComms: 0"
echo "=== host adapter named InstantlyComms ==="
rg -n 'class InstantlyComms|def default_comms' leadqualifier/comms.py
echo "=== glance v1 live-email row ==="
rg -n 'Instantly' plans.documented/2026-11-18-comms-layer/ARCHITECTURE-AT-A-GLANCE_v1_comms-layer.md | head
echo "=== playbook URLs (control: a present https would count) ==="
rg -n 'https?://' data/playbook.json && echo "playbook has URLs" || echo "data/playbook.json https: 0"
