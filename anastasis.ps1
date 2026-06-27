$ErrorActionPreference = "Stop"

$intervalSeconds = 300  # 5 minutes
$model = "claude-fable-5"

if ([string]::IsNullOrWhiteSpace($env:ANTHROPIC_API_KEY)) {
  Write-Host "ANTHROPIC_API_KEY is not set."
  exit 1
}

function Beep-Alert {
  for ($i = 0; $i -lt 20; $i++) {
    [console]::beep(1000, 300)
    Start-Sleep -Milliseconds 300
  }
}

function Read-ErrorBody($response) {
  if ($null -eq $response) {
    return ""
  }

  $stream = $response.GetResponseStream()
  if ($null -eq $stream) {
    return ""
  }

  $reader = New-Object System.IO.StreamReader($stream)
  try {
    return $reader.ReadToEnd()
  }
  finally {
    $reader.Dispose()
  }
}

while ($true) {
  $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

  $bodyObj = @{
    model = $model
    max_tokens = 1
    messages = @(
      @{
        role = "user"
        content = "Reply with exactly: pong"
      }
    )
  }

  $body = $bodyObj | ConvertTo-Json -Depth 10 -Compress
  $utf8Body = [System.Text.Encoding]::UTF8.GetBytes($body)

  try {
    Invoke-RestMethod `
      -Uri "https://api.anthropic.com/v1/messages" `
      -Method Post `
      -Headers @{
        "x-api-key" = $env:ANTHROPIC_API_KEY
        "anthropic-version" = "2023-06-01"
      } `
      -ContentType "application/json; charset=utf-8" `
      -Body $utf8Body `
      -TimeoutSec 30 | Out-Null

    Write-Host "[$now] Fable 5 appears to be AVAILABLE."

    while ($true) {
      Beep-Alert
      Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] Fable 5 AVAILABLE."
      Start-Sleep -Seconds 10
    }
  }
  catch {
    $statusCode = $null
    $message = $_.Exception.Message

    if ($null -ne $_.Exception.Response) {
      $statusCode = [int]$_.Exception.Response.StatusCode
      $message = Read-ErrorBody $_.Exception.Response
    }

    if ($statusCode -eq 404 -or $message -match "(?i)unavailable|not found|not_found|suspend") {
      Write-Host "[$now] Not available yet."
    }
    elseif ($message -match "(?i)credit balance is too low|insufficient credit") {
      Write-Host "[$now] Cannot verify: credit balance too low."
    }
    elseif ($statusCode -eq 401 -or $statusCode -eq 403) {
      Write-Host "[$now] Cannot verify: API key rejected or lacks access."
    }
    elseif ($statusCode -eq 429) {
      Write-Host "[$now] Rate limited. Waiting 30 minutes."
      Start-Sleep -Seconds 1800
      continue
    }
    else {
      Write-Host "[$now] Cannot verify: unexpected API or network error."
    }
  }

  Start-Sleep -Seconds $intervalSeconds
}
