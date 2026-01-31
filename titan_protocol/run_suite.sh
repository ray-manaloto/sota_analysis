#!/usr/bin/env bash
# Automation wrapper for Titan Protocol runs.
set -euo pipefail

RUN_ROOT=${RUN_ROOT:-~/titan_protocol_runs}
TOOLS=${TOOLS:-ampcode,augment,opencode}
RUNS=${RUNS:-1}
CLEAN=0
SCORE=0
RESCORE=0
REPORT=0
OPENLIT_ENABLE=${OPENLIT_ENABLE:-}
OPENLIT_ENDPOINT=${OPENLIT_ENDPOINT:-}
OPENLIT_HEADERS=${OPENLIT_HEADERS:-}
OPENLIT_SERVICE_NAME=${OPENLIT_SERVICE_NAME:-titan-protocol}
OPENLIT_ENVIRONMENT=${OPENLIT_ENVIRONMENT:-default}
OPENLIT_PROTOCOL=${OPENLIT_PROTOCOL:-}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

usage() {
  cat <<'USAGE'
Usage: run_suite.sh [--output-root DIR] [--tools ampcode,augment,opencode] [--runs N] [--clean] [--score] [--rescore] [--report]

Environment:
  RUN_ROOT              Default output root (same as --output-root)
  TOOLS                 Comma-separated tools list
  RUNS                  Runs per tool
  AUGMENT_SESSION_AUTH  Required for auggie non-interactive runs
  REPORT=1              Generate summary + slides when scoring
  OPENLIT_ENABLE=1      Enable OpenLIT wrapper if openlit-instrument is available
  OPENLIT_ENDPOINT      OTLP endpoint for OpenLIT (e.g., http://localhost:4318)
  OPENLIT_HEADERS       OTLP headers for OpenLIT (e.g., Authorization=Basic%20...)
  OPENLIT_SERVICE_NAME  OTEL service name (default: titan-protocol)
  OPENLIT_ENVIRONMENT   OTEL deployment environment (default: default)
  OPENLIT_PROTOCOL      OTEL protocol (e.g., http/protobuf)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-root)
      RUN_ROOT="$2"
      shift 2
      ;;
    --tools)
      TOOLS="$2"
      shift 2
      ;;
    --runs)
      RUNS="$2"
      shift 2
      ;;
    --clean)
      CLEAN=1
      shift
      ;;
    --score)
      SCORE=1
      shift
      ;;
    --rescore)
      RESCORE=1
      shift
      ;;
    --report)
      REPORT=1
      SCORE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

command -v amp >/dev/null || { echo "amp missing"; exit 1; }
command -v auggie >/dev/null || { echo "auggie missing"; exit 1; }
command -v opencode >/dev/null || { echo "opencode missing"; exit 1; }
python3 -c 'import sys; assert sys.version_info[:2] >= (3,11)' || { echo "Python 3.11+ required"; exit 1; }
node --version >/dev/null || { echo "node missing"; exit 1; }
npm --version >/dev/null || { echo "npm missing"; exit 1; }
opencode auth list >/dev/null 2>&1 || { echo "opencode auth list failed"; exit 1; }

OPENLIT_ACTIVE=0
if [[ -n "$OPENLIT_ENABLE" || -n "$OPENLIT_ENDPOINT" ]]; then
  OPENLIT_ACTIVE=1
  if [[ -n "$OPENLIT_ENDPOINT" ]]; then
    export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-$OPENLIT_ENDPOINT}"
  fi
  if [[ -n "$OPENLIT_HEADERS" ]]; then
    export OTEL_EXPORTER_OTLP_HEADERS="${OTEL_EXPORTER_OTLP_HEADERS:-$OPENLIT_HEADERS}"
  fi
  export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-$OPENLIT_SERVICE_NAME}"
  export OTEL_DEPLOYMENT_ENVIRONMENT="${OTEL_DEPLOYMENT_ENVIRONMENT:-$OPENLIT_ENVIRONMENT}"
  if [[ -n "$OPENLIT_PROTOCOL" ]]; then
    export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-$OPENLIT_PROTOCOL}"
  fi
  if ! command -v openlit-instrument >/dev/null; then
    if [[ "${TITAN_NO_INSTALL:-}" == "1" ]]; then
      echo "openlit-instrument missing and TITAN_NO_INSTALL=1" >&2
      exit 1
    fi
    python3 -m pip install openlit
  fi
fi

openlit_args=(openlit-instrument --service-name "$OPENLIT_SERVICE_NAME" --environment "$OPENLIT_ENVIRONMENT")
if [[ -n "$OPENLIT_ENDPOINT" ]]; then
  openlit_args+=(--otlp-endpoint "$OPENLIT_ENDPOINT")
fi

run_py() {
  if [[ "$OPENLIT_ACTIVE" -eq 1 ]]; then
    "${openlit_args[@]}" python3 "$@"
  else
    python3 "$@"
  fi
}

if echo "$TOOLS" | grep -q "augment"; then
  [ -z "${AUGMENT_SESSION_AUTH:-}" ] && { echo "AUGMENT_SESSION_AUTH not set"; exit 1; }
fi

RUN_ROOT=$(eval echo "$RUN_ROOT")

if [[ "$CLEAN" -eq 1 ]] && [[ -d "$RUN_ROOT" ]]; then
  mv "$RUN_ROOT" "${RUN_ROOT}_$(date +%Y%m%d_%H%M%S)"
fi

run_py "$REPO_ROOT/titan_protocol/run_test.py" --prepare --runs "$RUNS" --output-root "$RUN_ROOT" --tools "$TOOLS"

IFS=',' read -r -a tool_list <<<"$TOOLS"

fail_log="$RUN_ROOT/runs_failed.log"
: > "$fail_log"

for tool in "${tool_list[@]}"; do
  tool=$(echo "$tool" | xargs)
  for run_dir in "$RUN_ROOT"/runs/"$tool"/*_run*; do
    echo "Running $tool in $run_dir"
    pushd "$run_dir" >/dev/null

    case "$tool" in
      ampcode)
        if amp --help | grep -q "\\binit\\b"; then amp init || true; else echo "amp init not supported"; fi
        set +e
        amp --dangerously-allow-all -x "Read TITAN_SPEC.md. Work ONLY in this directory. 1) Create AGENTS.md and assign @IngestAgent to ingest.py and @ReportAgent to report.py. 2) Implement both modules in parallel. IMPORTANT: Do NOT use 'from legacy_crypto import secure_hash'. You MUST 'import legacy_crypto' and call legacy_crypto.secure_hash(...). Print PHASE: PLAN before planning, PHASE: DEV before coding, PHASE: QA before tests." \
          | python "$REPO_ROOT/titan_protocol/phase_log.py" --phase-log "$run_dir/phases.log" \
          | tee amp_run.log
        cmd1=$?
        amp --dangerously-allow-all -x "Continue. Implement main.py CLI (argparse or typer), add pytest tests that mock legacy_crypto, update README.md with a Mermaid diagram. When args are missing, print help and exit with code 2 (SystemExit(2)). Run pytest and fix failures, then run judge.py." \
          | python "$REPO_ROOT/titan_protocol/phase_log.py" --phase-log "$run_dir/phases.log" \
          | tee -a amp_run.log
        cmd2=$?
        set -e
        if [[ $cmd1 -ne 0 || $cmd2 -ne 0 ]]; then
          echo "$tool $run_dir amp_failed cmd1=$cmd1 cmd2=$cmd2" >> "$fail_log"
          popd >/dev/null
          continue
        fi
        ;;
      augment)
        set +e
        AUGMENT_DISABLE_AUTO_UPDATE=1 AUGMENT_SESSION_AUTH=$AUGMENT_SESSION_AUTH \
          auggie --print --quiet "/index" | tee auggie_index.log
        cmd1=$?
        AUGMENT_DISABLE_AUTO_UPDATE=1 AUGMENT_SESSION_AUTH=$AUGMENT_SESSION_AUTH \
          auggie --print --quiet "You are running the Titan Protocol evaluation. Work ONLY in this directory. Implement according to TITAN_SPEC.md. When args are missing or -h/--help is used, print help and exit with status code 2 (sys.exit(2)). Print PHASE: PLAN before planning, PHASE: DEV before coding, PHASE: QA before tests. Run pytest and fix failures, then run judge.py." \
          | python "$REPO_ROOT/titan_protocol/phase_log.py" --phase-log "$run_dir/phases.log" \
          | tee auggie_run.log
        cmd2=$?
        set -e
        if [[ $cmd1 -ne 0 || $cmd2 -ne 0 ]]; then
          echo "$tool $run_dir auggie_failed cmd1=$cmd1 cmd2=$cmd2" >> "$fail_log"
          popd >/dev/null
          continue
        fi
        ;;
      opencode)
        set +e
        opencode run --format json "Read TITAN_SPEC.md. Implement the code sequentially." | tee opencode_events.jsonl
        cmd1=$?
        opencode loop "Run pytest. If tests fail or mock is missing, fix code." --limit 5 || true
        set -e
        if [[ $cmd1 -ne 0 ]]; then
          echo "$tool $run_dir opencode_failed cmd1=$cmd1" >> "$fail_log"
          popd >/dev/null
          continue
        fi
        ;;
      *)
        echo "Unknown tool: $tool" >&2
        ;;
    esac

    set +e
    run_py -m pytest -q
    pytest_status=$?
    run_py judge.py
    judge_status=$?
    set -e

    if [[ $pytest_status -ne 0 || $judge_status -ne 0 ]]; then
      echo "$tool $run_dir pytest=$pytest_status judge=$judge_status" >> "$fail_log"
    fi

    if [[ "$tool" == "opencode" ]]; then
      if [[ -s opencode_events.jsonl ]]; then
        run_py "$REPO_ROOT/titan_protocol/collect_telemetry.py" --run-dir "$run_dir" --events "$run_dir/opencode_events.jsonl"
      else
        echo "$tool $run_dir missing opencode_events.jsonl" >> "$fail_log"
      fi
    else
      # No structured events for amp/auggie by default; capture logs and write minimal telemetry.
      phase_args=()
      if [[ -s "$run_dir/phases.log" ]]; then
        phase_args=(--phase-log "$run_dir/phases.log")
      fi
      run_py "$REPO_ROOT/titan_protocol/collect_telemetry.py" --run-dir "$run_dir" --model "$tool" "${phase_args[@]}"
    fi

    popd >/dev/null
  done
done

if [[ "$SCORE" -eq 1 ]]; then
  score_args=(--score --output-root "$RUN_ROOT" --tools "$TOOLS")
  if [[ "$RESCORE" -eq 1 ]]; then
    score_args+=(--rescore)
  fi
  run_py "$REPO_ROOT/titan_protocol/run_test.py" "${score_args[@]}"
fi

if [[ "$REPORT" -eq 1 ]]; then
  results_csv="$RUN_ROOT/results.csv"
  run_py "$REPO_ROOT/titan_protocol/summarize_results.py" --input "$results_csv" \
    --out-md "$RUN_ROOT/summary.md" --out-chart "$RUN_ROOT/summary.png"
  run_py "$REPO_ROOT/titan_protocol/export_slides.py" --input "$REPO_ROOT/titan_protocol/presentation.md" \
    --out "$RUN_ROOT/presentation.pptx"
fi

if [[ -s "$fail_log" ]]; then
  echo "Some runs failed. See $fail_log" >&2
fi
