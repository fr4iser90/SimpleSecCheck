# Lokaler Code-Scan
docker-compose run --rm \
  -v /path/to/project:/target:ro \
  -v $(pwd)/results:/SimpleSecCheck/results \
  -v $(pwd)/logs:/SimpleSecCheck/logs \
  scanner /SimpleSecCheck/bin/security-check.sh

# Oder mit Docker Hub Image (standalone)
docker run --rm \
  -v /path/to/project:/target:ro \
  -v $(pwd)/results:/SimpleSecCheck/results \
  -v $(pwd)/logs:/SimpleSecCheck/logs \
  fr4iser/simpleseccheck:latest \
  /SimpleSecCheck/bin/security-check.sh

# Website Scan
docker-compose run --rm \
  -e SCAN_TYPE=website \
  -e ZAP_TARGET=https://example.com \
  -v $(pwd)/results:/SimpleSecCheck/results \
  scanner /SimpleSecCheck/bin/security-check.sh

# Network Scan
docker-compose run --rm \
  -e SCAN_TYPE=network \
  -v $(pwd)/results:/SimpleSecCheck/results \
  scanner /SimpleSecCheck/bin/security-check.sh