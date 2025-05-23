FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3-pip wget curl jq git openjdk-17-jre && \
    ln -s /usr/bin/python3 /usr/bin/python

# Ensure Python 3 and pip are available for ZAP
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    ln -sf /usr/bin/python3 /usr/bin/python

# Upgrade pip and install Semgrep
RUN pip3 install --upgrade pip
RUN pip3 install semgrep
RUN pip3 install pyyaml
RUN pip3 install python-owasp-zap-v2.4
RUN pip3 install beautifulsoup4
RUN pip3 install pyyaml json5  # Added for configuration script
RUN pip3 install flask

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
RUN wget https://raw.githubusercontent.com/zaproxy/zaproxy/main/docker/zap_common.py -O /usr/local/bin/zap_common.py

# Copy SecuLite files
COPY . /seculite
WORKDIR /seculite

# Make scripts executable
RUN chmod +x scripts/security-check.sh
RUN chmod +x scripts/configure.py

RUN mkdir -p /zap/wrk
RUN mkdir -p /zap/wrk/zap && cp /seculite/zap/baseline.conf /zap/wrk/zap/baseline.conf

# Copy ZAP files to /zap for zap-baseline.py compatibility
RUN cp -r /opt/ZAP_2.16.1/* /zap/
# Symlink zap-x.sh to zap.sh for zap-baseline.py compatibility
RUN ln -s /zap/zap.sh /zap/zap-x.sh

COPY scripts/webui.js /seculite/results/webui.js

COPY web/loading.html /seculite/web/loading.html

WORKDIR /zap/wrk
ENTRYPOINT ["/seculite/scripts/security-check.sh"]