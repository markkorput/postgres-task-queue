---
description: Initialize work directory structure
agent: lightweight-command-runner
model: mistral/mistral-small-latest
---

You MUST execute the following steps exactly and in order.
Do NOT explain, analyze, plan, or add extra steps.

1. Verify `$(pwd)/.opencode/custom/init/init.sh` exists; if not, verify `$HOME/.config/opencode/custom/init/init.sh` exists.
2. Run the repo-local script when present; otherwise run the global script.
3. If neither script exists, stop and report the failure reason.

```bash
if [ -x "$(pwd)/.opencode/custom/init/init.sh" ]; then
  "$(pwd)/.opencode/custom/init/init.sh"
elif [ -x "$HOME/.config/opencode/custom/init/init.sh" ]; then
  "$HOME/.config/opencode/custom/init/init.sh"
else
  echo "Init script not found in local .opencode or global ~/.config/opencode"
  exit 1
fi
```
