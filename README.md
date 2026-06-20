# Anastasis

Tiny local watcher for Claude Fable 5 revival signals.

Anastasis watches primary Anthropic/Claude sources and makes noise when the evidence becomes strong enough to check immediately.

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
python .\anastasis.py --self-test
python .\anastasis.py --once
python .\anastasis.py --status
```

Continuous mode:

```powershell
python .\anastasis.py --run
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

`FABLE5_POLL_SECONDS` is clamped to at least 60 seconds to avoid accidental aggressive polling.

## States

- `down`: the Fable page says unavailable/suspended, or Claude Status has an unresolved Fable suspension incident.
- `probe_needed`: official wording changed or Anthropic Models API lists `claude-fable-5`.
- `available`: direct Anthropic Messages API probe succeeded.
- `unknown`: public checks repeatedly failed.
- `watching`: no high-confidence change yet.

Claude Status having no unresolved Fable incident is neutral. It is not treated as restoration evidence by itself.

The script only marks `available` after a successful direct Messages API probe.

## Direct Probe

The probe is off by default because it calls the Anthropic API.

Enable it explicitly:

```powershell
$env:ANTHROPIC_API_KEY="..."
$env:FABLE5_PROBE_ENABLED="true"
python .\anastasis.py --once --probe-now
```

Probe request uses:

- model: `claude-fable-5`
- max tokens: `1`
- prompt: `Reply OK.`

## Output Files

Runtime state is written to:

```text
anastasis-state.json
```

This file is ignored by git.

## Publish Notes

Anastasis is intentionally just a script. No database, scheduler library, notification package, web UI, or OpenRouter/X polling is included in v1.

HTTP error bodies are not stored in the state file, so API error details do not accidentally leak into local state.

For long-running use on Windows, either run `--run` in a terminal or schedule `python .\anastasis.py --once` every 5 minutes with Task Scheduler.

## License

MIT.
