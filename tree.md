 fr4iser@Gaming  ~/Documents/Git/SimpleSecCheck  ↱ main ±  tree -I 'node_modules|__pycache__|*.pyc|dist|build|.git|results|logs|owasp-dependency-check-data' -L 3
.
├── assets
│   ├── 1.png
│   ├── 2.png
│   ├── 3.png
│   ├── background.png
│   ├── transparent.png
│   └── webui.png
├── bin
│   ├── run-docker.sh
│   ├── security-check.sh
│   └── update-owasp-db.sh
├── BRAINSTORM_BULK_SCAN.md
├── build.log
├── CHANGELOG.md
├── CLI_BASH.md
├── CLI_DOCKER.md
├── config
│   ├── policy
│   │   ├── finding_policy.json
│   │   └── fp_whitelist.json
│   └── tools
│       ├── anchore
│       ├── bandit
│       ├── brakeman
│       ├── burp
│       ├── cfn-lint
│       ├── checkov
│       ├── clair
│       ├── codeql
│       ├── detect-secrets
│       ├── docker-bench
│       ├── eslint
│       ├── gitleaks
│       ├── kube-bench
│       ├── kube-hunter
│       ├── nikto
│       ├── npm-audit
│       ├── nuclei
│       ├── owasp-dependency-check
│       ├── safety
│       ├── snyk
│       ├── sonarqube
│       ├── terraform-security
│       ├── trivy
│       ├── trufflehog
│       ├── wapiti
│       └── zap
├── docker-compose.yml
├── Dockerfile
├── docs
│   ├── implementation_summary.md
│   ├── ui_ux_implementation_example.html
│   ├── ui_ux_improvements_analysis.md
│   ├── ui_ux_key_insights.md
│   ├── webui_network_scan_analysis.md
│   └── webui_ui_ux_plan.md
├── entrypoint.sh
├── env.example
├── LICENSE
├── README.md
├── rules
│   ├── api-security.yml
│   ├── code-bugs.yml
│   ├── llm-ai-security.yml
│   ├── prompt-injection.yml
│   ├── react-native-security.yml
│   ├── README.md
│   └── secrets.yml
├── scripts
│   ├── tools
│   │   ├── run_anchore.sh
│   │   ├── run_android_manifest_scanner.sh
│   │   ├── run_bandit.sh
│   │   ├── run_brakeman.sh
│   │   ├── run_burp.sh
│   │   ├── run_checkov.sh
│   │   ├── run_clair.sh
│   │   ├── run_codeql.sh
│   │   ├── run_detect_secrets.sh
│   │   ├── run_docker_bench.sh
│   │   ├── run_eslint.sh
│   │   ├── run_gitleaks.sh
│   │   ├── run_ios_plist_scanner.sh
│   │   ├── run_kube_bench.sh
│   │   ├── run_kube_hunter.sh
│   │   ├── run_nikto.sh
│   │   ├── run_npm_audit.sh
│   │   ├── run_nuclei.sh
│   │   ├── run_owasp_dependency_check.sh
│   │   ├── run_safety.sh
│   │   ├── run_semgrep.sh
│   │   ├── run_snyk.sh
│   │   ├── run_sonarqube.sh
│   │   ├── run_terraform_security.sh
│   │   ├── run_trivy.sh
│   │   ├── run_trufflehog.sh
│   │   ├── run_wapiti.sh
│   │   └── run_zap.sh
│   ├── wait-for-results.sh
│   └── zap_xml_parser.py
├── shell.nix
├── src
│   ├── core
│   │   ├── configure.py
│   │   ├── finding_policy.py
│   │   ├── llm_connector.py
│   │   ├── path_setup.py
│   │   ├── project_detector.py
│   │   └── scan_metadata.py
│   ├── processors
│   │   ├── anchore_processor.py
│   │   ├── android_manifest_processor.py
│   │   ├── bandit_processor.py
│   │   ├── brakeman_processor.py
│   │   ├── burp_processor.py
│   │   ├── checkov_processor.py
│   │   ├── clair_processor.py
│   │   ├── codeql_processor.py
│   │   ├── detect_secrets_processor.py
│   │   ├── docker_bench_processor.py
│   │   ├── eslint_processor.py
│   │   ├── gitleaks_processor.py
│   │   ├── ios_plist_processor.py
│   │   ├── kube_bench_processor.py
│   │   ├── kube_hunter_processor.py
│   │   ├── nikto_processor.py
│   │   ├── npm_audit_processor.py
│   │   ├── nuclei_processor.py
│   │   ├── owasp_dependency_check_processor.py
│   │   ├── safety_processor.py
│   │   ├── semgrep_processor.py
│   │   ├── snyk_processor.py
│   │   ├── sonarqube_processor.py
│   │   ├── terraform_security_processor.py
│   │   ├── trivy_processor.py
│   │   ├── trufflehog_processor.py
│   │   ├── wapiti_processor.py
│   │   └── zap_processor.py
│   └── reporting
│       ├── ai_prompt_modal.ts
│       ├── generate-html-report.py
│       ├── html_utils.py
│       ├── package.json
│       ├── package-lock.json
│       ├── tsconfig.json
│       └── webui.ts
├── VERSION
└── webui
    ├── backend
    │   ├── app
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── docker-entrypoint.sh
    ├── Dockerfile.compose
    ├── frontend
    │   ├── Dockerfile
    │   ├── index.html
    │   ├── package.json
    │   ├── package-lock.json
    │   ├── src
    │   ├── tsconfig.json
    │   ├── tsconfig.node.json
    │   └── vite.config.ts
    ├── README.md
    └── SECURITY.md

45 directories, 121 files
 fr4iser@Gaming  ~/Documents/Git/SimpleSecCheck  ↱ main ±  