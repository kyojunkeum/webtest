#!/usr/bin/env bash
# 업로드 폴더 실시간 모니터링 (실제 파일명만 표시)
# 사용: monitor_uploads.sh [/감시경로] [--no-exclude]
set -eo pipefail

WATCH_DIR="${1:-/var/tmp/uploads}"
EVENTS="create,close_write,modify,delete,moved_to,attrib"
EXCLUDE_REGEX='(^|/)\.|\.tmp$|\.part$|\.swp$|request_log\.jsonl$'
[[ "${2:-}" == "--no-exclude" ]] && EXCLUDE_REGEX=""

command -v inotifywait >/dev/null || { echo "inotify-tools 미설치"; exit 1; }
[[ -d "$WATCH_DIR" ]] || { echo "경로 없음: $WATCH_DIR"; exit 1; }

# URL 퍼센트 인코딩 디코드
urldecode() {
  local s="$1"
  s="${s//+/ }"
  printf '%b' "${s//%/\\x}"
}

# 파일 내부에서 filename 값 추출
extract_realname() {
  local path="$1" hdr val
  [[ -f "$path" ]] || { echo ""; return; }

  # 1) RFC5987 형식 (filename*=UTF-8''...)
  hdr="$(grep -aom1 -P "filename\\*=[^\\r\\n;]+" "$path" 2>/dev/null || true)"
  if [[ -n "$hdr" ]]; then
    val="${hdr#filename*=}"
    val="${val#UTF-8''}"
    echo "$(urldecode "$val")"
    return
  fi

  # 2) 일반 filename="..."
  hdr="$(grep -aom1 -P 'filename="[^"]+"' "$path" 2>/dev/null || true)"
  if [[ -n "$hdr" ]]; then
    val="${hdr#filename=\"}"
    val="${val%\"}"
    echo "$val"
    return
  fi

  # 3) 따옴표 없는 filename=...
  hdr="$(grep -aom1 -P 'filename=[^;\\r\\n]+' "$path" 2>/dev/null || true)"
  if [[ -n "$hdr" ]]; then
    val="${hdr#filename=}"
    echo "$val"
    return
  fi

  echo ""
}

log_line() {
  local ts="$1" ev="$2" path="$3"
  local real=""
  if [[ -f "$path" ]]; then
    real="$(extract_realname "$path")"
  fi
  printf "[%s] %-12s %s\n" "$ts" "$ev" "${real:-"(파일명 없음)"}"
}

echo "=== watching: $WATCH_DIR (events: $EVENTS) ==="
[[ -n "$EXCLUDE_REGEX" ]] && echo "=== exclude: $EXCLUDE_REGEX ==="

run_loop() {
  while IFS='|' read -r ts ev path; do
    case "$ev" in
      *DELETE*)      log_line "$ts" "DELETE"      "$path" ;;
      *MOVED_TO*)    log_line "$ts" "MOVED_TO"    "$path" ;;
      *CLOSE_WRITE*) log_line "$ts" "CLOSE_WRITE" "$path" ;;
      *CREATE*)      log_line "$ts" "CREATE"      "$path" ;;
      *MODIFY*)      log_line "$ts" "MODIFY"      "$path" ;;
      *ATTRIB*)      log_line "$ts" "ATTRIB"      "$path" ;;
      *)             log_line "$ts" "$ev"         "$path" ;;
    esac
  done
}

if [[ -n "$EXCLUDE_REGEX" ]]; then
  inotifywait -m -r -e "$EVENTS" --exclude "$EXCLUDE_REGEX" \
    --format '%T|%e|%w%f' --timefmt '%Y-%m-%d %H:%M:%S' "$WATCH_DIR" | run_loop
else
  inotifywait -m -r -e "$EVENTS" \
    --format '%T|%e|%w%f' --timefmt '%Y-%m-%d %H:%M:%S' "$WATCH_DIR" | run_loop
fi

