# Fable5 Watch

Tiny local watcher for Claude Fable 5 revival signals.

It watches primary Anthropic/Claude sources and makes noise when the evidence becomes strong enough to check immediately.

## What It Checks

- Anthropic Fable page: `https://www.anthropic.com/claude/fable`
- Claude Status unresolved incidents API: `https://status.claude.com/api/v2/incidents/unresolved.json`
- Anthropic Models API, if `ANTHROPIC_API_KEY` is set
- Anthropic Messages API probe, only if explicitly enabled

It does not use OpenRouter model lists or broad X/Twitter search for revival proof. Those are not primary sources and can produce false positives.

## Requirements

- Python 3.11+
- No third-party Python packages
- Optional Anthropic API key for model-list checks and direct probe

## Quick Start

```powershell
python .\fable5_watch.py --self-test
python .\fable5_watch.py --once
python .\fable5_watch.py --status
```

Continuous mode:

```powershell
python .\fable5_watch.py --run
```

Stop the alarm or watcher with `Ctrl+C`.

## Environment

Optional variables:

```env
ANTHROPIC_API_KEY=
FABLE5_PROBE_ENABLED=false
FABLE5_POLL_SECONDS=300
FABLE5_ALARM_SECONDS=0
```

`FABLE5_ALARM_SECONDS=0` means alarm forever in `--run` when an alarm state is reached.

## States

- `down`: official sources still say Fable 5 is unavailable or suspended.
- `probe_needed`: official wording changed or Anthropic Models API lists `claude-fable-5`.
- `available`: direct Anthropic Messages API probe succeeded.
- `unknown`: public checks repeatedly failed.
- `watching`: no high-confidence change yet.

The script only marks `available` after a successful direct Messages API probe.

## Direct Probe

The probe is off by default because it calls the Anthropic API.

Enable it explicitly:

```powershell
$env:ANTHROPIC_API_KEY="..."
$env:FABLE5_PROBE_ENABLED="true"
python .\fable5_watch.py --once --probe-now
```

Probe request uses:

- model: `claude-fable-5`
- max tokens: `1`
- prompt: `Reply OK.`

## Output Files

Runtime state is written to:

```text
fable5-watch-state.json
```

This file is ignored by git.

## Publish Notes

This project is intentionally just a script. No database, scheduler library, notification package, web UI, or OpenRouter/X polling is included in v1.

For long-running use on Windows, either run `--run` in a terminal or schedule `python .\fable5_watch.py --once` every 5 minutes with Task Scheduler.

## License

MIT.
