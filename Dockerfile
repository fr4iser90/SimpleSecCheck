FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3-pip wget curl jq git openjdk-17-jre && \
    ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip and install Semgrep
RUN pip3 install --upgrade pip
RUN pip3 install semgrep
RUN pip3 install pyyaml
RUN pip3 install python-owasp-zap-v2.4

# Install Trivy (always latest)
RUN export TRIVY_URL=$(wget -qO- https://api.github.com/repos/aquasecurity/trivy/releases/latest | grep browser_download_url | grep Linux-64bit.deb | cut -d '"' -f 4) && \
    wget -O trivy.deb $TRIVY_URL && \
    dpkg -i trivy.deb && \
    rm trivy.deb

# Install ZAP Baseline (ZAP CLI tools)
RUN wget https://github.com/zaproxy/zaproxy/releases/download/v2.16.1/ZAP_2.16.1_Linux.tar.gz && \
    tar -xvzf ZAP_2.16.1_Linux.tar.gz -C /opt && \
    rm ZAP_2.16.1_Linux.tar.gz
RUN wget https://raw.githubusercontent.com/zaproxy/zaproxy/main/docker/zap-baseline.py -O /usr/local/bin/zap-baseline.py && \
    chmod +x /usr/local/bin/zap-baseline.py

# Copy SecuLite files
COPY . /seculite
WORKDIR /seculite

# Make script executable
RUN chmod +x scripts/security-check.sh

ENTRYPOINT ["./scripts/security-check.sh"]