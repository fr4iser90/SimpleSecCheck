{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    python
    python.pkgs.pytest
    python.pkgs.pytest-asyncio
    python.pkgs.httpx
    python.pkgs.docker
    python.pkgs.pytest-xdist
    python.pkgs.defusedxml
    pkgs.ripgrep
    pkgs.curl
    pkgs.jq
  ];
}
  
  shellHook = ''
    echo "🧪 SimpleSecCheck Test Environment"
    echo "Available commands:"
    echo "  pytest tests/e2e/ -v -s                 # Run E2E tests"
    echo "  pytest -n auto tests/e2e/ -v -s         # Run E2E tests in parallel"
    echo ""
  '';
}
