# Lokaler Code-Scan
docker-compose run --rm \
  -v /path/to/project:/target:ro \
  -v $(pwd)/results:/SimpleSecCheck/results \
  -v $(pwd)/logs:/SimpleSecCheck/logs \
  scanner python3 -m scanner.core.orchestrator

# Oder mit Docker Hub Image (standalone)
docker run --rm \
  -v /path/to/project:/target:ro \
  -v $(pwd)/results:/SimpleSecCheck/results \
  -v $(pwd)/logs:/SimpleSecCheck/logs \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator

# Website Scan
docker-compose run --rm \
  -e SCAN_TYPE=website \
  -e ZAP_TARGET=https://example.com \
  -v $(pwd)/results:/SimpleSecCheck/results \
  scanner python3 -m scanner.core.orchestrator

# Network Scan
docker-compose run --rm \
  -e SCAN_TYPE=network \
  -v $(pwd)/results:/SimpleSecCheck/results \
  scanner python3 -m scanner.core.orchestrator