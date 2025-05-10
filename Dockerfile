FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3-pip wget curl jq git && \
    pip3 install semgrep && \
    wget -qO- https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.49.1_Linux-64bit.deb > trivy.deb && \
    dpkg -i trivy.deb && \
    rm trivy.deb && \
    wget -O /usr/local/bin/zap-baseline.py https://github.com/zaproxy/zaproxy/releases/latest/download/zap-baseline.py && \
    chmod +x /usr/local/bin/zap-baseline.py

# Copy SecuLite files
COPY . /seculite
WORKDIR /seculite

# Make script executable
RUN chmod +x scripts/security-check.sh

ENTRYPOINT ["./scripts/security-check.sh"] 