#!/usr/bin/env bash
# ScholarShield — ClamAV + YARA + Tesseract OCR setup for local/dev environments (Ubuntu/Debian).
#
# Installs the real ClamAV daemon and YARA, and creates a minimal local
# signature database containing the industry-standard EICAR test signature
# so the daemon can start even if your network cannot reach ClamAV's
# official CDN (database.clamav.net) — some sandboxed/CI environments and
# some corporate networks block or rate-limit it.
#
# On a normal machine with unrestricted internet access, run `sudo freshclam`
# after this script to pull the FULL official signature database (~1M+
# signatures) instead of relying on the minimal local one.

set -e

echo "==> Installing ClamAV daemon + YARA + Tesseract OCR..."
sudo apt-get update
sudo apt-get install -y clamav-daemon clamav-freshclam yara libyara-dev tesseract-ocr poppler-utils

echo "==> Attempting to fetch the official virus database (freshclam)..."
if sudo freshclam; then
  echo "==> Official database downloaded successfully."
else
  echo "==> freshclam failed (network-restricted environment?). Falling back to a minimal local database with the EICAR test signature."
  sudo mkdir -p /var/lib/clamav
  echo "44d88612fea8a8f36de82e1278abb02f:68:Eicar-Test-Signature" | sudo tee /var/lib/clamav/local.hdb > /dev/null
  sudo chown clamav:clamav /var/lib/clamav/local.hdb
fi

echo "==> Starting clamd..."
sudo mkdir -p /var/run/clamav /var/log/clamav
sudo chown clamav:clamav /var/run/clamav /var/log/clamav
sudo -u clamav clamd --config-file=/etc/clamav/clamd.conf &
sleep 5

echo "==> Verifying with the EICAR standard antivirus test string..."
printf 'X5O!P%%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.com
clamdscan /tmp/eicar.com && echo "WARNING: EICAR was not detected!" || echo "==> EICAR correctly detected. ClamAV is working."

echo "==> Done. Backend will connect to clamd at /var/run/clamav/clamd.ctl"
