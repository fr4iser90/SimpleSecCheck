FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3-pip wget curl jq git

# Upgrade pip and install Semgrep
RUN pip3 install --upgrade pip
RUN pip3 install semgrep

# Install Trivy (always latest)
RUN export TRIVY_URL=$(wget -qO- https://api.github.com/repos/aquasecurity/trivy/releases/latest | grep browser_download_url | grep Linux-64bit.deb | cut -d '"' -f 4) && \
    wget -O trivy.deb $TRIVY_URL && \
    dpkg -i trivy.deb && \
    rm trivy.deb

# Install ZAP Baseline (ZAP CLI tools)
RUN wget https://github.com/zaproxy/zaproxy/releases/download/v2.16.1/ZAP_2.16.1_Linux.tar.gz && \
    tar -xvzf ZAP_2.16.1_Linux.tar.gz -C /opt && \
    rm ZAP_2.16.1_Linux.tar.gz

RUN ln -s /opt/ZAP_2.16.1/zap-baseline.py /usr/local/bin/zap-baseline.py && \
    chmod +x /usr/local/bin/zap-baseline.py
    
# Copy SecuLite files
COPY . /seculite
WORKDIR /seculite

# Make script executable
RUN chmod +x scripts/security-check.sh

ENTRYPOINT ["./scripts/security-check.sh"]