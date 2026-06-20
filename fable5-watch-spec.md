# Fable5 Revival Watcher - Primary-Source Spec

Status: implementation-ready  
Date: 2026-06-20  

## Goal

Build a tiny local watcher that checks primary Anthropic/Claude sources for Claude Fable 5 revival.

The watcher should be boring:

- one Python 3.11+ script,
- no third-party packages,
- one JSON state file,
- no OpenRouter model-list detection,
- no broad X search,
- loud local alarm only when confidence is high.

## Primary Sources

Use only these v1 signals:

1. Anthropic Fable page: `https://www.anthropic.com/claude/fable`
2. Claude Status API: `https://status.claude.com/api/v2/incidents/unresolved.json`
3. Anthropic Models API: `GET https://api.anthropic.com/v1/models`
4. Anthropic Messages API probe: `POST https://api.anthropic.com/v1/messages`

Do not use OpenRouter as proof of restoration. It can list a model while the upstream model is unavailable.

Do not use general X search in v1. It is not primary-source evidence.

## State Rules

States:

- `down`: official page/status still says Fable 5 is unavailable or suspended.
- `probe_needed`: official wording changed, or Anthropic Models API lists `claude-fable-5`.
- `available`: Anthropic Messages API probe succeeds for `claude-fable-5`.
- `unknown`: primary-source checks repeatedly fail.
- `watching`: checks ran, but there is no high-confidence change.

Decision order:

```txt
if Messages probe succeeds:
  available
elif Messages probe says model unavailable/suspended/not found:
  down
elif Fable page says "currently unavailable":
  down
elif Claude Status unresolved incidents mention Fable and suspended:
  down
elif Fable page or Status no longer show the old unavailable/suspended wording:
  probe_needed
elif Anthropic Models API lists claude-fable-5:
  probe_needed
elif public checks failed 3 cycles in a row:
  unknown
else:
  watching
```

## Probe Rules

The Messages API probe may cost money, so it is off by default.

Run the probe only when:

- `FABLE5_PROBE_ENABLED=true`, and
- official wording changed, Models API lists Fable 5, or `--probe-now` is passed.

Probe request:

```json
{
  "model": "claude-fable-5",
  "max_tokens": 1,
  "messages": [{"role": "user", "content": "Reply OK."}]
}
```

## Alarm Rules

Alarm when state changes into:

- `probe_needed`
- `available`

Default:

- `--run`: keep alarming until interrupted.
- `--once`: print the state, but do not block forever.

Use Python standard library only:

- Windows: `winsound.Beep`
- Other platforms: terminal bell `\a`

## Files

- `fable5_watch.py`
- `fable5-watch-state.json`

Environment variables:

```env
ANTHROPIC_API_KEY=
FABLE5_PROBE_ENABLED=false
FABLE5_POLL_SECONDS=300
FABLE5_ALARM_SECONDS=0
```

`FABLE5_ALARM_SECONDS=0` means alarm forever in `--run`.

## CLI

```powershell
python .\fable5_watch.py --once
python .\fable5_watch.py --run
python .\fable5_watch.py --status
python .\fable5_watch.py --self-test
python .\fable5_watch.py --once --probe-now
```

## Acceptance Criteria

- Runs without API keys.
- Uses Claude Status API instead of scraping status HTML.
- Does not crash when any source fails.
- Does not log or store API keys.
- Does not use OpenRouter or broad X search.
- Does not claim `available` unless Messages API probe succeeds.
- Sounds an alarm on transition into `probe_needed` or `available`.
- Has `--self-test` with plain asserts.
