#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


MODEL_ID = "claude-fable-5"
STATE_FILE = Path(__file__).with_name("anastasis-state.json")
FABLE_PAGE = "https://www.anthropic.com/claude/fable"
STATUS_INCIDENTS = "https://status.claude.com/api/v2/incidents/unresolved.json"
ANTHROPIC_MODELS = "https://api.anthropic.com/v1/models"
ANTHROPIC_MESSAGES = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def http_json(url, headers=None, data=None, timeout=20):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "user-agent": "anastasis/1.0",
            "content-type": "application/json",
            **(headers or {}),
        },
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_text(url, timeout=20):
    req = urllib.request.Request(url, headers={"user-agent": "anastasis/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def fetch_result(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return {"status": "http_error", "code": exc.code, "body": body[:500]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def classify_fable_page(text):
    text_l = text.lower()
    if "currently unavailable" in text_l:
        return "down"
    if "claude fable 5" in text_l or MODEL_ID in text_l:
        return "maybe_up"
    return "unknown"


def check_fable_page():
    result = fetch_result(http_text, FABLE_PAGE)
    if isinstance(result, dict):
        return {"source": "fable_page", "result": "unknown", "detail": result}
    _, text = result
    return {"source": "fable_page", "result": classify_fable_page(text)}


def fable_suspension_text(value):
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return bool(re.search(r"fable", text, re.I) and re.search(r"suspend|unavailable", text, re.I))


def classify_status_incidents(payload):
    incidents = payload.get("incidents", [])
    if any(fable_suspension_text(item) for item in incidents):
        return "down"
    return "maybe_up"


def check_status_incidents():
    result = fetch_result(http_json, STATUS_INCIDENTS)
    if isinstance(result, dict):
        return {"source": "claude_status", "result": "unknown", "detail": result}
    _, payload = result
    return {"source": "claude_status", "result": classify_status_incidents(payload)}


def anthropic_headers():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    return {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION}


def check_models_api():
    headers = anthropic_headers()
    if not headers:
        return {"source": "models_api", "result": "skipped", "detail": "ANTHROPIC_API_KEY not set"}
    result = fetch_result(http_json, ANTHROPIC_MODELS, headers=headers)
    if isinstance(result, dict):
        code = result.get("code")
        if code in {401, 403}:
            return {"source": "models_api", "result": "auth_error", "code": code}
        return {"source": "models_api", "result": "unknown", "detail": {k: v for k, v in result.items() if k != "body"}}
    _, payload = result
    models = payload.get("data", [])
    found = any(item.get("id") == MODEL_ID for item in models if isinstance(item, dict))
    return {"source": "models_api", "result": "candidate_present" if found else "candidate_absent"}


def probe_messages_api():
    headers = anthropic_headers()
    if not headers:
        return {"source": "messages_probe", "result": "skipped", "detail": "ANTHROPIC_API_KEY not set"}
    payload = {
        "model": MODEL_ID,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "Reply OK."}],
    }
    result = fetch_result(http_json, ANTHROPIC_MESSAGES, headers=headers, data=payload)
    if isinstance(result, dict):
        code = result.get("code")
        body = (result.get("body") or "").lower()
        if code in {401, 403}:
            return {"source": "messages_probe", "result": "auth_error", "code": code}
        if code == 404 or "not_found" in body or "not found" in body or "unavailable" in body or "suspend" in body:
            return {"source": "messages_probe", "result": "unavailable", "code": code}
        if code == 429:
            return {"source": "messages_probe", "result": "rate_limited", "code": code}
        return {"source": "messages_probe", "result": "unknown", "code": code}
    status, payload = result
    if status == 200 and payload.get("content"):
        return {"source": "messages_probe", "result": "usable"}
    return {"source": "messages_probe", "result": "unknown"}


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"previous_state_unreadable": True}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_FILE)


def should_probe(results, force=False):
    if force:
        return True
    return any(
        item["result"] in {"maybe_up", "candidate_present"}
        for item in results
        if item["source"] in {"fable_page", "claude_status", "models_api"}
    )


def decide_state(results, consecutive_failures=0):
    probe = next((r for r in results if r["source"] == "messages_probe"), None)
    if probe and probe["result"] == "usable":
        return "available"
    if probe and probe["result"] == "unavailable":
        return "down"
    if any(r["source"] in {"fable_page", "claude_status"} and r["result"] == "down" for r in results):
        return "down"
    if any(r["source"] in {"fable_page", "claude_status"} and r["result"] == "maybe_up" for r in results):
        return "probe_needed"
    if any(r["source"] == "models_api" and r["result"] == "candidate_present" for r in results):
        return "probe_needed"
    if consecutive_failures >= 3:
        return "unknown"
    return "watching"


def one_cycle(probe_now=False):
    old = load_state()
    results = [check_fable_page(), check_status_incidents(), check_models_api()]
    public_failed = all(r["result"] == "unknown" for r in results if r["source"] in {"fable_page", "claude_status"})
    failures = (old.get("consecutive_public_failures", 0) + 1) if public_failed else 0

    if env_bool("FABLE5_PROBE_ENABLED") and should_probe(results, probe_now):
        results.append(probe_messages_api())

    state = decide_state(results, failures)
    previous = old.get("state")
    notify = previous != state and state in {"probe_needed", "available"}
    new_state = {
        "state": state,
        "previous_state": previous,
        "checked_at": now(),
        "consecutive_public_failures": failures,
        "notify": notify,
        "results": results,
    }
    save_state(new_state)
    return new_state


def print_summary(state):
    print(f"{state['checked_at']} state={state['state']} previous={state.get('previous_state')}")
    for item in state["results"]:
        print(f"- {item['source']}: {item['result']}")
    if state.get("notify"):
        print("notification: alarm condition")


def alarm(seconds=0):
    end = None if seconds <= 0 else time.time() + seconds
    try:
        import winsound
        while end is None or time.time() < end:
            winsound.Beep(880, 350)
            winsound.Beep(660, 350)
            time.sleep(0.5)
    except ImportError:
        while end is None or time.time() < end:
            sys.stdout.write("\a")
            sys.stdout.flush()
            time.sleep(1)


def status():
    state = load_state()
    if not state:
        print("No state file yet.")
        return
    print_summary(state)


def self_test():
    assert classify_fable_page("Claude Fable 5 is currently unavailable.") == "down"
    assert classify_fable_page("Claude Fable 5 is priced at $10.") == "maybe_up"
    assert classify_status_incidents({"incidents": [{"name": "suspended access to Claude Fable 5"}]}) == "down"
    assert classify_status_incidents({"incidents": []}) == "maybe_up"
    assert decide_state([{"source": "fable_page", "result": "down"}]) == "down"
    assert decide_state([{"source": "claude_status", "result": "maybe_up"}]) == "probe_needed"
    assert decide_state([{"source": "models_api", "result": "candidate_present"}]) == "probe_needed"
    assert decide_state([{"source": "messages_probe", "result": "usable"}]) == "available"
    assert decide_state([{"source": "messages_probe", "result": "auth_error"}]) == "watching"
    old_state = {"state": "down"}
    new_state = "probe_needed"
    assert old_state["state"] != new_state and new_state in {"probe_needed", "available"}
    assert fable_suspension_text({"name": "We suspended access to Fable 5"})
    print("self-test passed")


def main():
    parser = argparse.ArgumentParser(description="Watch primary sources for Claude Fable 5 revival.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--probe-now", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return
    if args.status:
        status()
        return

    poll_seconds = int(os.getenv("FABLE5_POLL_SECONDS", "300"))
    alarm_seconds = int(os.getenv("FABLE5_ALARM_SECONDS", "0"))

    while True:
        state = one_cycle(probe_now=args.probe_now)
        print_summary(state)
        if state.get("notify"):
            if args.run:
                alarm(alarm_seconds)
            elif alarm_seconds > 0:
                alarm(alarm_seconds)
        if args.once:
            return
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
