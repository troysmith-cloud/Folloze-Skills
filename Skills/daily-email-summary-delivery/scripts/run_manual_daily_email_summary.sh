#!/bin/zsh
set -euo pipefail

if [[ -z "${HOME:-}" ]]; then
  echo "HOME is not set." >&2
  exit 1
fi
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

workspace="${WORKSPACE:-$PWD}"
codex_home="${CODEX_HOME:-$HOME/.codex}"
skill_path="$codex_home/skills/daily-email-summary-delivery/SKILL.md"
codex_bin="${CODEX_BIN:-codex}"
status_dir="/tmp/daily-email-summary-manual"
mkdir -p "$status_dir"

run_type="${1:-test}"
date_stamp="$(date +%F)"
timestamp="$(date +%Y%m%d-%H%M%S)"
status_file="$status_dir/last-status-${timestamp}.txt"
run_log="$status_dir/run-${timestamp}.log"

if [[ "$run_type" == "scheduled" ]]; then
  subject_label="Daily Email Summary"
else
  subject_label="Daily Email Summary Test"
fi

prompt_file="$(mktemp /tmp/daily-email-summary-prompt.XXXXXX)"
cleanup() {
  rm -f "$prompt_file"
}
trap cleanup EXIT

cat > "$prompt_file" <<EOF
Use [\$daily-email-summary-delivery]($skill_path) to execute the full daily email summary workflow.

This is a ${run_type} run.

Requirements:
- Review recent incoming Gmail inbox messages and produce the real summary, not a placeholder.
- Group results into Urgent, Needs reply soon, Waiting, and FYI.
- Send the full summary as a Slack DM to Troy Smith using Slack user ID U08FTRBFX1R.
- Send the same full summary by real email to Troy.smith@folloze.com using the bundled delivery script.
- Use subject line "${subject_label} - ${date_stamp}".
- In the final answer, clearly state whether Slack delivery succeeded and whether email delivery succeeded.
- End with exactly one ::inbox-item directive.
EOF

{
  echo "[$(date -Iseconds)] starting daily email summary run type=${run_type}"
  "$codex_bin" exec \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  --cd "$workspace" \
  -o "$status_file" \
  - < "$prompt_file"
  rc=$?
  echo "[$(date -Iseconds)] finished rc=${rc}"
  echo "Saved final status to $status_file"
} 2>&1 | tee "$run_log"

exit ${pipestatus[1]}
