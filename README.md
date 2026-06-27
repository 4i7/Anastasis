# Anastasis

Anastasis is a tiny PowerShell script that keeps checking whether Claude Fable 5 is usable.

It calls Anthropic's Messages API every 5 minutes with `claude-fable-5`.

- If the model is still unavailable, it prints `Not available yet.`
- If the API key is bad, rate limited, or out of credit, it says so.
- If the request succeeds, it beeps until you stop it.

No OpenRouter. No X/Twitter scraping. No database. No Python packages.

## Requirements

- Windows PowerShell
- `ANTHROPIC_API_KEY` in your environment

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\anastasis.ps1
```

If you copied the script to `$env:USERPROFILE\fable-watch\watch-fable.ps1`, this is the same thing:

```powershell
cd $env:USERPROFILE\fable-watch
powershell -ExecutionPolicy Bypass -File .\watch-fable.ps1
```

Stop it with `Ctrl+C`.

## What It Sends

```json
{
  "model": "claude-fable-5",
  "max_tokens": 1,
  "messages": [
    {
      "role": "user",
      "content": "Reply with exactly: pong"
    }
  ]
}
```

## License

MIT.
