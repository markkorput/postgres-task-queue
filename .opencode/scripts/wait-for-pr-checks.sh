#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  printf 'Usage: %s <pr-selector> [timeout-seconds] [poll-seconds]\n' "$0" >&2
  exit 64
fi

pr_selector="$1"
timeout_seconds="${2:-5400}"
poll_seconds="${3:-30}"

if ! [[ "$timeout_seconds" =~ ^[0-9]+$ ]] || ! [[ "$poll_seconds" =~ ^[0-9]+$ ]]; then
  printf 'timeout-seconds and poll-seconds must be integers\n' >&2
  exit 64
fi

deadline=$(( $(date +%s) + timeout_seconds ))
empty_observations=0

collect_snapshot() {
  local pr_json repo_json head_sha repo checks_json status_json runs_json

  pr_json="$(gh pr view "$pr_selector" --json number,url,headRefName,headRefOid)"
  repo_json="$(gh repo view --json nameWithOwner)"
  head_sha="$(jq -r '.headRefOid' <<<"$pr_json")"
  repo="$(jq -r '.nameWithOwner' <<<"$repo_json")"

  checks_json="$(gh api -H 'Accept: application/vnd.github+json' "repos/$repo/commits/$head_sha/check-runs?per_page=100")"
  status_json="$(gh api -H 'Accept: application/vnd.github+json' "repos/$repo/commits/$head_sha/status")"
  runs_json="$(gh api -H 'Accept: application/vnd.github+json' "repos/$repo/actions/runs?head_sha=$head_sha&per_page=100")"

  jq -n \
    --argjson pr "$pr_json" \
    --argjson repo "$repo_json" \
    --argjson checks "$checks_json" \
    --argjson statuses "$status_json" \
    --argjson runs "$runs_json" \
    '
      def success_conclusions: ["success", "neutral", "skipped"];
      def failure_conclusions: ["failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"];
      def pending_statuses: ["queued", "in_progress", "requested", "waiting", "pending"];
      def pending_states: ["pending"];
      def failure_states: ["error", "failure"];
      def check_run_record:
        {
          name: .name,
          kind: "check_run",
          status: .status,
          conclusion: .conclusion,
          details_url: (.details_url // .html_url),
          app: (.app.name // null)
        };
      def status_context_record:
        {
          name: .context,
          kind: "status_context",
          status: .state,
          conclusion: .state,
          details_url: .target_url,
          app: (.creator.login // null)
        };
      def failed_runs:
        [
          $runs.workflow_runs[]?
          | select(.head_sha == $pr.headRefOid)
          | select(.conclusion != null and (.conclusion | IN(failure_conclusions[])))
          | {
              id: .id,
              name: .name,
              status: .status,
              conclusion: .conclusion,
              event: .event,
              html_url: .html_url,
              run_attempt: .run_attempt
            }
        ];
      def pending_check_runs:
        [
          $checks.check_runs[]?
          | select(.status != "completed" or (.status | IN(pending_statuses[])) or (.conclusion == null) or ((.conclusion | tostring) | IN("queued", "in_progress", "requested", "waiting", "pending")))
          | check_run_record
        ];
      def failed_check_runs:
        [
          $checks.check_runs[]?
          | select(.status == "completed")
          | select(.conclusion != null and (.conclusion | IN(failure_conclusions[])))
          | check_run_record
        ];
      def successful_check_runs:
        [
          $checks.check_runs[]?
          | select(.status == "completed")
          | select(.conclusion != null and (.conclusion | IN(success_conclusions[])))
          | check_run_record
        ];
      def pending_status_contexts:
        [
          $statuses.statuses[]?
          | select(.state | IN(pending_states[]))
          | status_context_record
        ];
      def failed_status_contexts:
        [
          $statuses.statuses[]?
          | select(.state | IN(failure_states[]))
          | status_context_record
        ];
      def successful_status_contexts:
        [
          $statuses.statuses[]?
          | select(.state == "success")
          | status_context_record
        ];
      (pending_check_runs + pending_status_contexts) as $pending_checks
      | (failed_check_runs + failed_status_contexts) as $failed_checks
      | (successful_check_runs + successful_status_contexts) as $successful_checks
      | failed_runs as $failed_runs
      | ((($checks.check_runs // []) | length) > 0 or (($statuses.statuses // []) | length) > 0 or (($runs.workflow_runs // []) | length) > 0) as $has_any_checks
      | {
          status:
            if (not $has_any_checks) then "no_checks"
            elif (($pending_checks | length) > 0) then "pending"
            elif (($failed_checks | length) > 0) then "failure"
            else "success"
            end,
          repo: $repo.nameWithOwner,
          pr: {
            number: $pr.number,
            url: $pr.url,
            branch: $pr.headRefName,
            head_sha: $pr.headRefOid
          },
          summary: {
            failed: ($failed_checks | length),
            pending: ($pending_checks | length),
            successful: ($successful_checks | length),
            failed_runs: ($failed_runs | length)
          },
          failed_checks: $failed_checks,
          pending_checks: $pending_checks,
          failed_runs: $failed_runs
        }
    '
}

while true; do
  snapshot="$(collect_snapshot)"
  status="$(jq -r '.status' <<<"$snapshot")"

  case "$status" in
    success)
      printf '%s\n' "$snapshot"
      exit 0
      ;;
    failure)
      printf '%s\n' "$snapshot"
      exit 1
      ;;
    no_checks)
      empty_observations=$((empty_observations + 1))
      if (( empty_observations >= 3 )); then
        printf '%s\n' "$snapshot"
        exit 3
      fi
      ;;
    pending)
      empty_observations=0
      ;;
    *)
      printf '%s\n' "$snapshot"
      exit 1
      ;;
  esac

  if (( $(date +%s) >= deadline )); then
    timed_out_snapshot="$(jq '.status = "timeout"' <<<"$snapshot")"
    printf '%s\n' "$timed_out_snapshot"
    exit 2
  fi

  sleep "$poll_seconds"
done
