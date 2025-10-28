FROM ubuntu:22.04

# Version information
ARG VERSION=1.0.0
LABEL version=$VERSION
LABEL maintainer="SimpleSecCheck Team"

# Install dependencies with Node.js v18+
RUN apt-get update && \
    apt-get install -y python3-pip wget curl jq git openjdk-17-jre unzip docker.io && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    ln -s /usr/bin/python3 /usr/bin/python

# Ensure Python 3 and pip are available for ZAP
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    ln -sf /usr/bin/python3 /usr/bin/python

# Upgrade pip and install Semgrep with proper dependencies
RUN pip3 install --upgrade pip setuptools wheel
# Clean install to avoid conflicts
RUN pip3 uninstall -y typing_extensions pydantic pydantic_core semgrep || true
# Install with correct versions - must install pydantic requirements FIRST
RUN pip3 install --force-reinstall --no-cache-dir "typing_extensions>=4.14.1" && \
    pip3 install --force-reinstall --no-cache-dir "pydantic>=2.0.0" "pydantic-core>=2.0.0" && \
    pip3 install semgrep
RUN pip3 install pyyaml
RUN pip3 install python-owasp-zap-v2.4
RUN pip3 install beautifulsoup4
RUN pip3 install pyyaml json5  # Added for configuration script
RUN pip3 install flask
RUN pip3 install requests  # Added for LLM connector

# Install Trivy (always latest)
RUN export TRIVY_URL=$(wget -qO- https://api.github.com/repos/aquasecurity/trivy/releases/latest | jq -r '.assets[] | select(.name | test("Linux-64bit.deb")) | .browser_download_url') && \
    wget -O trivy.deb $TRIVY_URL && \
    dpkg -i trivy.deb && \
    rm trivy.deb

# Install CodeQL CLI and Query Packs
RUN export CODEQL_URL=$(wget -qO- https://api.github.com/repos/github/codeql-cli-binaries/releases/latest | jq -r '.assets[] | select(.name | test("codeql-linux64.zip")) | .browser_download_url') && \
    wget -O codeql.zip $CODEQL_URL && \
    unzip codeql.zip -d /opt && \
    rm codeql.zip && \
    ln -s /opt/codeql/codeql /usr/local/bin/codeql && \
    codeql pack download codeql/python-queries && \
    codeql pack download codeql/javascript-queries && \
    codeql pack download codeql/java-queries && \
    codeql pack download codeql/cpp-queries && \
    codeql pack download codeql/csharp-queries && \
    codeql pack download codeql/go-queries

# Install Nuclei CLI
RUN export NUCLEI_URL=$(wget -qO- https://api.github.com/repos/projectdiscovery/nuclei/releases/latest | jq -r '.assets[] | select(.name | test("nuclei.*linux.*amd64.zip")) | .browser_download_url') && \
    wget -O nuclei.zip $NUCLEI_URL && \
    unzip nuclei.zip -d /opt && \
    rm nuclei.zip && \
    ln -s /opt/nuclei /usr/local/bin/nuclei

# Install OWASP Dependency Check
RUN export OWASP_DC_URL=$(wget -qO- https://api.github.com/repos/jeremylong/DependencyCheck/releases/latest | jq -r '.assets[] | select(.name | test("dependency-check.*release.zip") and (test("ant") | not) and (test("asc") | not)) | .browser_download_url') && \
    wget -O dependency-check.zip $OWASP_DC_URL && \
    unzip dependency-check.zip -d /opt && \
    rm dependency-check.zip && \
    ln -s /opt/dependency-check/bin/dependency-check.sh /usr/local/bin/dependency-check && \
    mkdir -p /SimpleSecCheck/owasp-dependency-check-data
    # Note: Database initialization happens at runtime via volume mount to avoid rebuilding on every code change

# Install Safety (Python security scanner)
RUN pip3 install safety

# Install Bandit (Python code security scanner)
RUN pip3 install bandit[toml]

# Install Brakeman (Ruby on Rails security scanner)
RUN apt-get update && apt-get install -y ruby ruby-dev build-essential && \
    gem install brakeman --no-document

# Install Detect-secrets (Python secret detection tool)
RUN pip3 install detect-secrets

# Install Checkov (Terraform security scanner)
RUN pip3 install checkov  # typing_extensions already upgraded above

# Install Wapiti (Web vulnerability scanner)
RUN pip3 install wapiti3 && \
    pip3 install --force-reinstall --no-cache-dir "typing_extensions>=4.14.1"

# Install TruffleHog CLI
RUN export TRUFFLEHOG_URL=$(wget -qO- https://api.github.com/repos/trufflesecurity/trufflehog/releases/latest | jq -r '.assets[] | select(.name | test("trufflehog.*linux.*amd64.tar.gz")) | .browser_download_url') && \
    wget -O trufflehog.tar.gz $TRUFFLEHOG_URL && \
    tar -xvzf trufflehog.tar.gz -C /opt && \
    rm trufflehog.tar.gz && \
    ln -s /opt/trufflehog /usr/local/bin/trufflehog

# Install GitLeaks CLI
RUN export GITLEAKS_URL=$(wget -qO- https://api.github.com/repos/gitleaks/gitleaks/releases/latest | jq -r '.assets[] | select(.name | test("gitleaks.*linux_x64.tar.gz")) | .browser_download_url') && \
    wget -O gitleaks.tar.gz $GITLEAKS_URL && \
    tar -xvzf gitleaks.tar.gz -C /opt && \
    rm gitleaks.tar.gz && \
    ln -s /opt/gitleaks /usr/local/bin/gitleaks

# Install ESLint and security plugins
RUN npm install -g eslint eslint-plugin-security @typescript-eslint/parser @typescript-eslint/eslint-plugin

# Install Nikto (Web server scanner)
RUN apt-get update && apt-get install -y perl libwww-perl liblwp-protocol-https-perl unzip && \
    wget https://github.com/sullo/nikto/archive/master.zip -O nikto.zip && \
    unzip nikto.zip && \
    mv nikto-master /opt/nikto && \
    ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto && \
    rm nikto.zip

# Install Burp Suite (Web application security scanner)
# Note: Burp Suite Community Edition can be run in headless mode
RUN wget -q 'https://portswigger.net/burp/releases/download?product=community&version=2024.2.5' -O burp-suite.jar && \
    mkdir -p /opt/burp && \
    mv burp-suite.jar /opt/burp/ && \
    chmod +x /opt/burp/burp-suite.jar

# Install Snyk CLI
RUN curl -s https://static.snyk.io/cli/latest/snyk-linux -o snyk && \
    chmod +x snyk && \
    mv snyk /usr/local/bin/

# Install SonarQube Scanner CLI via npm
RUN npm install -g sonar-scanner

# Install ZAP Baseline (ZAP CLI tools)
RUN wget https://github.com/zaproxy/zaproxy/releases/download/v2.16.1/ZAP_2.16.1_Linux.tar.gz && \
    tar -xvzf ZAP_2.16.1_Linux.tar.gz -C /opt && \
    rm ZAP_2.16.1_Linux.tar.gz
RUN wget https://raw.githubusercontent.com/zaproxy/zaproxy/main/docker/zap-baseline.py -O /usr/local/bin/zap-baseline.py && \
    chmod +x /usr/local/bin/zap-baseline.py
RUN wget https://raw.githubusercontent.com/zaproxy/zaproxy/main/docker/zap_common.py -O /usr/local/bin/zap_common.py

# Install Kube-hunter (Kubernetes penetration testing tool)
RUN pip3 install kube-hunter

# Install Kube-bench (Kubernetes compliance testing tool)
RUN export KUBE_BENCH_URL=$(wget -qO- https://api.github.com/repos/aquasecurity/kube-bench/releases/latest | jq -r '.assets[] | select(.name | test("kube-bench.*linux.*amd64.tar.gz")) | .browser_download_url') && \
    wget -O kube-bench.tar.gz $KUBE_BENCH_URL && \
    tar -xvzf kube-bench.tar.gz -C /opt && \
    rm kube-bench.tar.gz && \
    ln -s /opt/kube-bench /usr/local/bin/kube-bench

# Install Docker Bench (Docker daemon compliance testing tool) - needs full repo
RUN git clone https://github.com/docker/docker-bench-security.git /opt/docker-bench-security && \
    ln -s /opt/docker-bench-security/docker-bench-security.sh /usr/local/bin/docker-bench-security && \
    chmod +x /opt/docker-bench-security/docker-bench-security.sh

# Install Anchore Grype (container image vulnerability scanner)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Copy SimpleSecCheck files FIRST (as root)
COPY . /SimpleSecCheck
WORKDIR /SimpleSecCheck

# Create required directories and set permissions
RUN mkdir -p /SimpleSecCheck/results /SimpleSecCheck/logs /SimpleSecCheck/owasp-dependency-check-data /zap/wrk && \
    mkdir -p /zap/wrk/zap && \
    cp /SimpleSecCheck/zap/baseline.conf /zap/wrk/zap/baseline.conf && \
    cp -r /opt/ZAP_2.16.1/* /zap/ && \
    ln -sf /zap/zap.sh /zap/zap-x.sh

# Create non-root user (1000:1000 matches typical host user)
RUN useradd -m -u 1000 -s /bin/bash scanner && \
    (groupadd -g 999 docker || true) && \
    usermod -aG docker scanner && \
    chown -R scanner:scanner /SimpleSecCheck /zap

# Make scripts executable
RUN chmod +x /SimpleSecCheck/scripts/security-check.sh
RUN chmod +x /SimpleSecCheck/scripts/configure.py

# Install sudo and configure passwordless sudo for scanner user
RUN apt-get install -y sudo && \
    echo 'scanner ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER scanner

# Set CodeQL environment variables
ENV CODEQL_HOME=/opt/codeql
ENV CODEQL_CONFIG_PATH=/SimpleSecCheck/codeql/config.yaml
ENV CODEQL_QUERIES_PATH=/SimpleSecCheck/codeql/queries

# Set Nuclei environment variables
ENV NUCLEI_HOME=/opt/nuclei
ENV NUCLEI_CONFIG_PATH=/SimpleSecCheck/nuclei/config.yaml
ENV NUCLEI_TEMPLATES_PATH=/SimpleSecCheck/nuclei/templates

# Set OWASP Dependency Check environment variables
ENV OWASP_DC_HOME=/opt/dependency-check
ENV OWASP_DC_CONFIG_PATH=/SimpleSecCheck/owasp-dependency-check/config.yaml
ENV OWASP_DC_DATA_DIR=/SimpleSecCheck/owasp-dependency-check-data

# Set Safety environment variables
ENV SAFETY_CONFIG_PATH=/SimpleSecCheck/safety/config.yaml

# Set Snyk environment variables
ENV SNYK_CONFIG_PATH=/SimpleSecCheck/snyk/config.yaml

# Set SonarQube environment variables
ENV SONARQUBE_CONFIG_PATH=/SimpleSecCheck/sonarqube/config.yaml
ENV SONARQUBE_SCANNER_HOME=/opt/sonar-scanner

# Set Checkov environment variables
ENV TERRAFORM_SECURITY_CONFIG_PATH=/SimpleSecCheck/terraform-security/config.yaml

# Set TruffleHog environment variables
ENV TRUFFLEHOG_CONFIG_PATH=/SimpleSecCheck/trufflehog/config.yaml

# Set GitLeaks environment variables
ENV GITLEAKS_CONFIG_PATH=/SimpleSecCheck/gitleaks/config.yaml

# Set Detect-secrets environment variables
ENV DETECT_SECRETS_CONFIG_PATH=/SimpleSecCheck/detect-secrets/config.yaml

# Set Wapiti environment variables
ENV WAPITI_CONFIG_PATH=/SimpleSecCheck/wapiti/config.yaml

# Set Nikto environment variables
ENV NIKTO_CONFIG_PATH=/SimpleSecCheck/nikto/config.yaml

# Set Burp Suite environment variables
ENV BURP_CONFIG_PATH=/SimpleSecCheck/burp/config.yaml
ENV BURP_HOME=/opt/burp

# Set Kube-hunter environment variables
ENV KUBE_HUNTER_CONFIG_PATH=/SimpleSecCheck/kube-hunter/config.yaml

# Set Kube-bench environment variables
ENV KUBE_BENCH_CONFIG_PATH=/SimpleSecCheck/kube-bench/config.yaml

# Set Docker Bench environment variables
ENV DOCKER_BENCH_CONFIG_PATH=/SimpleSecCheck/docker-bench/config.yaml

# Set ESLint environment variables
ENV ESLINT_CONFIG_PATH=/SimpleSecCheck/eslint/config.yaml

# Set Brakeman environment variables
ENV BRAKEMAN_CONFIG_PATH=/SimpleSecCheck/brakeman/config.yaml

# Set Bandit environment variables
ENV BANDIT_CONFIG_PATH=/SimpleSecCheck/bandit/config.yaml

# Set Anchore environment variables
ENV ANCHORE_CONFIG_PATH=/SimpleSecCheck/anchore/config.yaml

WORKDIR /zap/wrk
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]