{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python312;
  
  # Test helper scripts
  test-unit = pkgs.writeShellScriptBin "test-unit" ''
    python -m pytest tests/unit/ -v
  '';

  test-unit-backend = pkgs.writeShellScriptBin "test-unit-backend" ''
    python -m pytest tests/unit/ -v -k "backend or middleware or api"
  '';

  test-unit-worker = pkgs.writeShellScriptBin "test-unit-worker" ''
    python -m pytest tests/unit/ -v -k "worker"
  '';

  test-unit-scanner = pkgs.writeShellScriptBin "test-unit-scanner" ''
    python -m pytest tests/unit/ -v -k "scanner"
  '';

  test-integration = pkgs.writeShellScriptBin "test-integration" ''
    python -m pytest tests/integration/ -v -s
  '';

  test-setup = pkgs.writeShellScriptBin "test-setup" ''
    python -m pytest tests/integration/test_setup_wizard.py -v -s
  '';

  test-setup-clean = pkgs.writeShellScriptBin "test-setup-clean" ''
    python -m pytest tests/integration/test_setup_wizard.py --cleanup -v -s
  '';

  test-e2e = pkgs.writeShellScriptBin "test-e2e" ''
    python -m pytest tests/e2e/ -v -s
  '';

  test-e2e-parallel = pkgs.writeShellScriptBin "test-e2e-parallel" ''
    python -m pytest tests/e2e/ -n auto -v -s
  '';

  test-all = pkgs.writeShellScriptBin "test-all" ''
    echo "🧪 Running all tests..."
    python -m pytest tests/unit/ tests/integration/ tests/e2e/ -v
  '';

  test-all-clean = pkgs.writeShellScriptBin "test-all-clean" ''
    echo "🧪 Running all tests with cleanup..."
    python -m pytest tests/unit/ tests/integration/ tests/e2e/ --cleanup -v -s
  '';

  test-quick = pkgs.writeShellScriptBin "test-quick" ''
    echo "⚡ Quick test run (unit tests only)..."
    python -m pytest tests/unit/ -v
  '';

in

pkgs.mkShell {
  buildInputs = [
    (python.withPackages (ps: with ps; [
      pytest
      pytest-asyncio
      pytest-xdist
      httpx
      docker
      email-validator
      defusedxml
      fastapi
      uvicorn
      pydantic
      pydantic-settings
      asyncpg
      sqlalchemy
      alembic
      redis
      aioredis
      pyjwt
      passlib
      python-multipart
      structlog
      pyyaml
      python-dateutil
      python-dotenv
      prometheus-fastapi-instrumentator
      cryptography
      argon2-cffi
      # dependency-injector fix
      (dependency-injector.overridePythonAttrs (old: {
        nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ ps.cython ];
        doCheck = false;
      }))
    ]))

    pkgs.ripgrep
    pkgs.curl
    pkgs.jq
    pkgs.docker
    pkgs.docker-compose
    
    # Test helper scripts
    test-unit
    test-unit-backend
    test-unit-worker
    test-unit-scanner
    test-integration
    test-setup
    test-setup-clean
    test-e2e
    test-e2e-parallel
    test-all
    test-all-clean
    test-quick
  ];

  shellHook = ''
    echo "🧪 SimpleSecCheck Dev Environment"
    echo ""
    echo "📋 Test Commands:"
    echo ""
    echo "  Unit Tests:"
    echo "    test-unit              - Run all unit tests"
    echo "    test-unit-backend      - Backend unit tests"
    echo "    test-unit-worker       - Worker unit tests"
    echo "    test-unit-scanner      - Scanner unit tests"
    echo ""
    echo "  Integration Tests:"
    echo "    test-integration       - Run all integration tests"
    echo "    test-setup             - Setup wizard tests"
    echo "    test-setup-clean       - Setup tests with cleanup"
    echo ""
    echo "  E2E Tests:"
    echo "    test-e2e               - Run all E2E tests"
    echo "    test-e2e-parallel      - E2E tests in parallel"
    echo ""
    echo "  All Tests:"
    echo "    test-all               - Run all tests (unit + integration + e2e)"
    echo "    test-all-clean         - All tests with cleanup"
    echo ""
    echo "  Quick Tests:"
    echo "    test-quick             - Quick test run (unit only)"
    echo ""
    echo "💡 Tip: Use 'nix-shell --run \"test-unit\"' to run tests"
    echo ""
  '';
}
