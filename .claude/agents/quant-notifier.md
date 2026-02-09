---
name: quant-notifier
description: "ElevenLabs voice notifications for pipeline events"
version: "1.0.0"
parent_worker: optimizer
max_duration: 30s
parallelizable: false
---

# Quant Notifier Agent

## Purpose
Provides voice notifications via ElevenLabs TTS for key pipeline events. Announces: strategy optimization complete, validation results, promotion/rejection decisions, and critical alerts. This agent MUST run LAST in the pipeline to provide final status updates.

## Skills Used
- `/logging-monitoring` - For structured event logging
- `/workflow-automation` - For notification dispatch

## MCP Tools
- `sequential_thinking` - Compose notification message

## Input
```python
{
    "event_type": "optimization_complete"|"validation_complete"|"promotion"|"rejection"|"alert",
    "strategy_name": str,
    "routing_decision": str,         # From promo-router
    "quality_grade": str,            # A, B, C, or F
    "key_metrics": {
        "sharpe": float,
        "win_rate": float,
        "firms_passed": int
    },
    "action_items": [str],
    "rejection_reasons": [str],      # If applicable
    "notification_preferences": {
        "voice_enabled": bool,
        "voice_id": str,             # ElevenLabs voice ID
        "also_send_slack": bool,
        "also_send_discord": bool
    }
}
```

## Output
```python
{
    "notification_sent": bool,
    "channels": [str],               # ["voice", "slack", "discord"]
    "message_text": str,
    "audio_url": str,                # ElevenLabs audio URL (if voice)
    "timestamp": str
}
```

## Notification Templates

### Optimization Complete
```
"Strategy optimization complete for {strategy_name}.
Sharpe ratio is {sharpe:.2f}.
Win rate is {win_rate:.0%}.
Proceeding to validation."
```

### Validation Complete
```
"Validation complete for {strategy_name}.
Strategy passed {firms_passed} of 14 prop firms.
Robustness score is {robustness_score}.
{recommendation}."
```

### Promotion to good/
```
"Excellent news! {strategy_name} has been promoted to the good strategies folder.
Grade A quality with Sharpe of {sharpe:.2f}.
This strategy is ready for live trading."
```

### Promotion to prop_firm_ready/
```
"{strategy_name} is now prop firm ready.
Compatible with {firms_passed} prop firms.
Top recommendations are {top_firms}.
Ready for evaluation account setup."
```

### Rejection
```
"Strategy {strategy_name} has been rejected.
Reason: {primary_reason}.
{additional_context}.
Review the rejection report for details."
```

### Critical Alert
```
"Alert! Critical issue detected with {strategy_name}.
{alert_message}.
Immediate review required."
```

## ElevenLabs Integration

### Voice Configuration
```python
ELEVENLABS_CONFIG = {
    "api_key": "${ELEVENLABS_API_KEY}",
    "default_voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "model_id": "eleven_turbo_v2",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    }
}
```

### API Call
```python
async def generate_voice_notification(text: str, voice_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2",
                "voice_settings": ELEVENLABS_CONFIG["voice_settings"]
            }
        )
        # Save audio and return URL
        audio_path = save_audio(response.content)
        return audio_path
```

## Multi-Channel Dispatch

### Slack Notification
```python
async def send_slack_notification(message: str, channel: str):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    payload = {
        "channel": channel,
        "text": message,
        "icon_emoji": ":chart_with_upwards_trend:"
    }
    await httpx.post(webhook_url, json=payload)
```

### Discord Notification
```python
async def send_discord_notification(message: str, webhook_url: str):
    payload = {
        "content": message,
        "username": "Sigma-Quant"
    }
    await httpx.post(webhook_url, json=payload)
```

## Algorithm
```python
async def send_notification(event):
    # 1. Compose message from template
    message = compose_message(event)

    # 2. Send voice notification (if enabled)
    channels = []
    if event.notification_preferences.voice_enabled:
        audio_url = await generate_voice_notification(
            message,
            event.notification_preferences.voice_id
        )
        channels.append("voice")
        # Play audio locally
        await play_audio(audio_url)

    # 3. Send Slack (if enabled)
    if event.notification_preferences.also_send_slack:
        await send_slack_notification(message, "#quant-alerts")
        channels.append("slack")

    # 4. Send Discord (if enabled)
    if event.notification_preferences.also_send_discord:
        await send_discord_notification(message, DISCORD_WEBHOOK)
        channels.append("discord")

    # 5. Log notification
    log_notification(event, message, channels)

    return {
        "notification_sent": True,
        "channels": channels,
        "message_text": message,
        "audio_url": audio_url if "voice" in channels else None,
        "timestamp": datetime.now().isoformat()
    }
```

## Event Priority

| Event Type | Priority | Voice | Slack | Discord |
|------------|----------|-------|-------|---------|
| Critical Alert | P0 | Yes | Yes | Yes |
| Rejection | P1 | Yes | Yes | Optional |
| Promotion (good/) | P2 | Yes | Yes | Optional |
| Promotion (prop_firm_ready/) | P2 | Yes | Optional | Optional |
| Validation Complete | P3 | Optional | Optional | No |
| Optimization Complete | P4 | Optional | No | No |

## Rate Limiting
- Voice: Max 1 notification per 10 seconds
- Slack: Max 5 notifications per minute
- Discord: Max 5 notifications per minute

## Fallback Behavior
- If ElevenLabs fails: Log warning, continue with text channels
- If Slack fails: Log error, continue with other channels
- If all channels fail: Log critical error, raise alert

## Invocation
Spawn @quant-notifier when: Pipeline reaches a notification point. MUST run LAST in the pipeline to announce final results.

## Dependencies
- Requires: Previous pipeline step complete
- Runs after: `quant-promo-router`
- No downstream dependencies (terminal agent)

## Completion Marker
SUBAGENT_COMPLETE: quant-notifier
FILES_CREATED: 0
OUTPUT: Notification sent to configured channels
