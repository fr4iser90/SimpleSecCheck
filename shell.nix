{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    python311Packages.pytest
    python311Packages.pytest-asyncio
    python311Packages.httpx
    python311Packages.docker
    python311Packages.pytest-xdist
  ];
  
  shellHook = ''
    echo "🧪 SimpleSecCheck Test Environment"
    echo "Available commands:"
    echo "  pytest tests/e2e/ -v -s                 # Run E2E tests"
    echo "  pytest -n auto tests/e2e/ -v -s         # Run E2E tests in parallel"
    echo ""
  '';
}
