#!/usr/bin/env bash
# SimpleSecCheck — standalone scanner helper (docker run)
# Wraps the correct env vars for scanner.core.orchestrator (see docs/CLI_DOCKER.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults (override via env)
SSC_SCANNER_IMAGE="${SSC_SCANNER_IMAGE:-simpleseccheck/scanner:latest}"
PROFILE="${PROFILE:-standard}"
RESULTS_DIR=""
VERBOSE=0
EXCLUDE=""
GIT_BRANCH=""
NETWORK_HOST="${NETWORK_HOST:-127.0.0.1}"
SCAN_TYPE_OVERRIDE=""
TARGET_TYPE_OVERRIDE=""
FORCE_GIT=0
NO_ENV_FILE=0
LIST_SCANNERS=0
BOOTSTRAP_ASSETS=0
ORCH_HELP=0
EXTRA_DOCKER_ARGS=()

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
  sed 's/^  //' <<EOF
${BLUE}SimpleSecCheck — scanner helper${NC}

${GREEN}Usage:${NC}
  $0 [options] <target>
  $0 [options] --type image <image:tag>
  $0 --list
  $0 --bootstrap-assets

${GREEN}Targets (auto-detected unless --type is set):${NC}
  /path/to/project     Local code (read-only mount at /target)
  https://example.com  Website / DAST (SCAN_TYPE=website)
  network              Host / Docker-bench style (needs Docker socket)

${GREEN}Profiles (--profile):${NC}
  quick      Faster, lighter tool settings (manifest-driven)
  standard   Default
  deep       Thorough (longer runtimes)

${GREEN}Options:${NC}
  -h, --help              Show this help
  -p, --profile NAME      quick | standard | deep (default: standard)
  -t, --type TYPE         code | website | network | image | git
      --git               Treat <target> as a Git clone URL (not a website scan)
  -o, --results-dir PATH  Host folder for /app/results (default: ${SCRIPT_DIR}/results)
  -v, --verbose           SSC_SCAN_LOG_VERBOSE=1 (noisy container console)
      --exclude LIST      EXCLUDE_PATHS (comma-separated)
      --git-branch NAME   GIT_BRANCH (git mode only)
      --network-host H    SCAN_TARGET for network_host (default: ${NETWORK_HOST})
      --image NAME        Scanner image (default: ${SSC_SCANNER_IMAGE})
      --no-env-file       Do not source ${SCRIPT_DIR}/.env
      --docker-arg ARG      Extra arg for docker run (repeatable), e.g. --docker-arg --network=host
      --list                List scanners (orchestrator --list)
      --bootstrap-assets    Run manifest asset bootstrap inside the image
      --orchestrator-help   Print orchestrator --help (env vars)

${GREEN}Environment:${NC}
  SSC_SCANNER_IMAGE   Default image if --image not passed
  NVD_API_KEY, SNYK_TOKEN  Passed through when set (also read from ${SCRIPT_DIR}/.env)

${GREEN}Examples:${NC}
  $0 -p quick /home/me/myapp
  $0 -p deep https://example.com
  $0 network
  $0 --type image nginx:alpine
  $0 --git --profile standard https://github.com/org/repo.git
  $0 --git-branch main --git https://github.com/org/repo.git

Results are written under RESULTS_DIR; each run uses a new SCAN_ID folder inside that tree.
EOF
}

log_info() { echo -e "${BLUE}[run-scanner]${NC} $*"; }
log_ok() { echo -e "${GREEN}[run-scanner]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[run-scanner]${NC} $*"; }
log_err() { echo -e "${RED}[run-scanner]${NC} $*" >&2; }

GIT_WORKDIR=""
cleanup() {
  if [[ -n "${GIT_WORKDIR}" && -d "${GIT_WORKDIR}" ]]; then
    rm -rf "${GIT_WORKDIR}"
  fi
}
trap cleanup EXIT

# Optional .env (tokens)
load_env_file() {
  if [[ "${NO_ENV_FILE}" -eq 1 ]]; then
    return 0
  fi
  local f="${SCRIPT_DIR}/.env"
  if [[ ! -f "${f}" ]]; then
    return 0
  fi
  log_info "Loading NVD_API_KEY / SNYK_TOKEN from ${f} (only these keys; avoids overriding CLI flags)"
  local chunk
  chunk="$(grep -E '^(NVD_API_KEY|SNYK_TOKEN)=' "${f}" 2>/dev/null || true)"
  if [[ -n "${chunk}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source /dev/stdin <<<"${chunk}"
    set +a
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      -p|--profile)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        PROFILE="${2}"
        shift 2
        ;;
      -t|--type)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        SCAN_TYPE_OVERRIDE="${2}"
        shift 2
        ;;
      --target-type)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        TARGET_TYPE_OVERRIDE="${2}"
        shift 2
        ;;
      --git)
        FORCE_GIT=1
        shift
        ;;
      -o|--results-dir)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        RESULTS_DIR="${2}"
        shift 2
        ;;
      -v|--verbose)
        VERBOSE=1
        shift
        ;;
      --exclude)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        EXCLUDE="${2}"
        shift 2
        ;;
      --git-branch)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        GIT_BRANCH="${2}"
        shift 2
        ;;
      --network-host)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        NETWORK_HOST="${2}"
        shift 2
        ;;
      --image)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        SSC_SCANNER_IMAGE="${2}"
        shift 2
        ;;
      --no-env-file)
        NO_ENV_FILE=1
        shift
        ;;
      --docker-arg)
        if [[ -z "${2:-}" ]]; then log_err "Missing value for $1"; exit 2; fi
        EXTRA_DOCKER_ARGS+=("${2}")
        shift 2
        ;;
      --list)
        LIST_SCANNERS=1
        shift
        ;;
      --bootstrap-assets)
        BOOTSTRAP_ASSETS=1
        shift
        ;;
      --orchestrator-help)
        ORCH_HELP=1
        shift
        ;;
      --)
        shift
        break
        ;;
      -*)
        log_err "Unknown option: $1"
        usage
        exit 2
        ;;
      *)
        break
        ;;
    esac
  done
  REMAINING=("$@")
}

validate_profile() {
  case "${PROFILE}" in
    quick|standard|deep) ;;
    *)
      log_err "Invalid profile: ${PROFILE} (use quick, standard, or deep)"
      exit 2
      ;;
  esac
}

infer_mode() {
  local raw="${1:-}"
  if [[ -z "${raw}" ]]; then
    log_err "Missing <target>."
    usage
    exit 2
  fi

  if [[ -n "${SCAN_TYPE_OVERRIDE}" ]]; then
    case "${SCAN_TYPE_OVERRIDE}" in
      code|website|network|image|git) ;;
      *)
        log_err "Invalid --type: ${SCAN_TYPE_OVERRIDE}"
        exit 2
        ;;
    esac
    MODE="${SCAN_TYPE_OVERRIDE}"
    return 0
  fi

  if [[ "${FORCE_GIT}" -eq 1 ]]; then
    MODE="git"
    return 0
  fi

  if [[ "${raw}" == "network" ]]; then
    MODE="network"
    return 0
  fi

  if [[ "${raw}" =~ ^https?:// ]]; then
    MODE="website"
    return 0
  fi

  if [[ -e "${raw}" ]]; then
    MODE="code"
    return 0
  fi

  log_err "Could not infer scan type for: ${raw}"
  log_err "Use -t / --type, or pass an existing path, a http(s) URL, or the keyword 'network'."
  exit 2
}

run_docker() {
  local -a cmd=(docker run --rm)
  if [[ -t 1 ]]; then
    cmd+=(-i -t)
  else
    cmd+=(-i)
  fi
  cmd+=("${EXTRA_DOCKER_ARGS[@]}")
  cmd+=("$@")
  "${cmd[@]}"
}

main() {
  parse_args "$@"
  load_env_file
  validate_profile

  if [[ "${LIST_SCANNERS}" -eq 1 ]]; then
    log_ok "Listing scanners (${SSC_SCANNER_IMAGE})"
    run_docker "${SSC_SCANNER_IMAGE}" python3 -m scanner.core.orchestrator --list
    exit 0
  fi
  if [[ "${BOOTSTRAP_ASSETS}" -eq 1 ]]; then
    log_ok "Bootstrap assets (${SSC_SCANNER_IMAGE})"
    run_docker "${SSC_SCANNER_IMAGE}" python3 -m scanner.core.orchestrator --bootstrap-assets
    exit 0
  fi
  if [[ "${ORCH_HELP}" -eq 1 ]]; then
    run_docker "${SSC_SCANNER_IMAGE}" python3 -m scanner.core.orchestrator --help
    exit 0
  fi

  if [[ ${#REMAINING[@]} -lt 1 ]]; then
    usage
    exit 2
  fi

  local TARGET="${REMAINING[0]}"
  infer_mode "${TARGET}"

  RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/results}"
  mkdir -p "${RESULTS_DIR}"
  local RESULTS_ABS
  RESULTS_ABS="$(cd "${RESULTS_DIR}" && pwd)"

  local scan_type="" target_type="" scan_target="" target_path_host="" tpi="/target"

  case "${MODE}" in
    code)
      scan_type="code"
      target_type="${TARGET_TYPE_OVERRIDE:-local_mount}"
      scan_target="/target"
      local ap
      ap="$(cd "$(dirname "${TARGET}")" && pwd)/$(basename "${TARGET}")"
      target_path_host="${ap}"
      ;;
    website)
      scan_type="website"
      target_type="${TARGET_TYPE_OVERRIDE:-website}"
      scan_target="${TARGET}"
      ;;
    network)
      scan_type="network"
      target_type="${TARGET_TYPE_OVERRIDE:-network_host}"
      scan_target="${NETWORK_HOST}"
      ;;
    image)
      scan_type="image"
      target_type="${TARGET_TYPE_OVERRIDE:-container_registry}"
      scan_target="${TARGET}"
      ;;
    git)
      scan_type="code"
      target_type="${TARGET_TYPE_OVERRIDE:-git_repo}"
      scan_target="${TARGET}"
      GIT_WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/ssc-git.XXXXXX")"
      ;;
    *)
      log_err "Internal error: MODE=${MODE}"
      exit 3
      ;;
  esac

  local -a envs=(
    -e "SCAN_TYPE=${scan_type}"
    -e "TARGET_TYPE=${target_type}"
    -e "COLLECT_METADATA=true"
    -e "SCAN_PROFILE=${PROFILE}"
    -e "SCAN_TARGET=${scan_target}"
    -e "RESULTS_DIR_IN_CONTAINER=/app/results"
    -e "TARGET_PATH_IN_CONTAINER=${tpi}"
  )

  if [[ -n "${target_path_host}" ]]; then
    envs+=(-e "TARGET_PATH_HOST=${target_path_host}")
  fi
  if [[ -n "${EXCLUDE}" ]]; then
    envs+=(-e "EXCLUDE_PATHS=${EXCLUDE}")
  fi
  if [[ -n "${GIT_BRANCH}" ]]; then
    envs+=(-e "GIT_BRANCH=${GIT_BRANCH}")
  fi
  if [[ "${VERBOSE}" -eq 1 ]]; then
    envs+=(-e "SSC_SCAN_LOG_VERBOSE=1")
  fi
  if [[ -n "${NVD_API_KEY:-}" ]]; then
    envs+=(-e "NVD_API_KEY=${NVD_API_KEY}")
  fi
  if [[ -n "${SNYK_TOKEN:-}" ]]; then
    envs+=(-e "SNYK_TOKEN=${SNYK_TOKEN}")
  fi

  local -a vols=( -v "${RESULTS_ABS}:/app/results" )

  case "${MODE}" in
    code)
      vols+=( -v "${target_path_host}:${tpi}:ro" )
      ;;
    git)
      vols+=( -v "${GIT_WORKDIR}:${tpi}" )
      ;;
    network|image)
      vols+=( -v /var/run/docker.sock:/var/run/docker.sock:ro )
      ;;
  esac

  echo ""
  log_ok "Image:      ${SSC_SCANNER_IMAGE}"
  log_ok "Profile:    ${PROFILE}"
  log_ok "Scan type:  ${scan_type} (target_type=${target_type})"
  log_ok "Results:    ${RESULTS_ABS}/<scan_id>/"
  echo ""

  run_docker \
    "${vols[@]}" \
    "${envs[@]}" \
    "${SSC_SCANNER_IMAGE}"
}

main "$@"
