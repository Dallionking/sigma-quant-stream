#!/usr/bin/env python3
"""
notify.py - Quant Research Team Voice Notification System
==========================================================

Provides text-to-speech notifications for the Quant Research Team using
ElevenLabs API with fallback to system TTS (macOS 'say' command).

Usage:
    python notify.py "Your notification message"
    python notify.py --event=strategy_promoted --strategy="RSI_Divergence" --sharpe=1.8
    python notify.py --event=budget_cap --spent=50.00

Events:
    strategy_promoted    - Strategy moved to good/
    prop_firm_complete   - Prop firm validation done
    pane_milestone       - Pane reached iteration milestone
    budget_cap           - Budget cap reached
    all_complete         - All panes finished
    error                - Critical error occurred

Environment Variables:
    ELEVENLABS_API_KEY: Your ElevenLabs API key (optional)
    ELEVENLABS_VOICE_ID: Voice ID (default: Rachel)
    QUANT_TTS_ENABLED: Set to 'false' to disable TTS
"""

import os
import sys
import subprocess
import tempfile
import argparse
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

# Try to import requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Voice ID mapping
VOICE_MAP = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "drew": "29vD33N1CtxCmqQRPOHJ",
    "clyde": "2EiwWnXFnvU5JabPnv8n",
    "paul": "5Q0t7uMcjvnagumLfvZi",
    "domi": "AZnzlk1XvdvUeBnXmlld",
    "dave": "CYw3kZ02Hs0563khs1Fj",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
}

# Settings
TTS_ENABLED = os.getenv("QUANT_TTS_ENABLED", "true").lower() != "false"


def get_event_message(event: str, **kwargs) -> str:
    """Generate message for specific events."""
    messages = {
        "strategy_promoted": (
            f"Quant Team found a promising strategy! "
            f"{kwargs.get('strategy', 'New strategy')} with Sharpe {kwargs.get('sharpe', 'unknown')}. "
            f"Moving to good folder."
        ),
        "prop_firm_complete": (
            f"Prop firm validation complete for {kwargs.get('strategy', 'strategy')}. "
            f"Passing {kwargs.get('passing', 0)} of 14 firms. "
            f"{'Ready for deployment!' if kwargs.get('passing', 0) >= 3 else 'Needs optimization.'}"
        ),
        "pane_milestone": (
            f"Pane {kwargs.get('pane', '?')} completed {kwargs.get('iterations', 0)} iterations. "
            f"{kwargs.get('validated', 0)} strategies validated so far."
        ),
        "budget_cap": (
            f"Budget cap reached. Quant team paused at ${kwargs.get('spent', 0):.2f} spent. "
            f"Review results and increase budget to continue."
        ),
        "all_complete": (
            f"All panes complete! "
            f"{kwargs.get('total_validated', 0)} strategies validated. "
            f"{kwargs.get('prop_firm_ready', 0)} ready for prop firm trading."
        ),
        "strategy_deployed": (
            f"Strategy {kwargs.get('strategy', '')} successfully deployed. "
            f"Ready for live trading."
        ),
        "error": (
            f"Critical error in Quant Team. "
            f"Pane {kwargs.get('pane', '?')}: {kwargs.get('error', 'Unknown error')}. "
            f"Please check logs."
        ),
        "startup": (
            f"Quant Research Team starting. "
            f"{kwargs.get('panes', 6)} panes, {kwargs.get('iterations', 100)} iterations target. "
            f"Budget cap: ${kwargs.get('budget', 50):.2f}."
        ),
        "research_insight": (
            f"Research insight discovered. "
            f"{kwargs.get('insight', 'New finding')}. "
            f"Adding to research playbook."
        ),
    }
    return messages.get(event, kwargs.get("message", "Quant Team notification"))


def speak_elevenlabs(text: str, voice_id: str = ELEVENLABS_VOICE_ID) -> bool:
    """Use ElevenLabs API for high-quality TTS."""
    if not ELEVENLABS_API_KEY:
        return False

    if not HAS_REQUESTS:
        print("Warning: 'requests' package not installed. Run: pip install requests", file=sys.stderr)
        return False

    try:
        response = requests.post(
            f"{ELEVENLABS_API_URL}/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                }
            },
            timeout=30,
        )

        if response.status_code != 200:
            print(f"ElevenLabs API error: {response.status_code}", file=sys.stderr)
            return False

        # Save to temp file and play
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(response.content)
            temp_path = f.name

        # Play audio
        play_audio(temp_path)

        # Cleanup
        os.unlink(temp_path)
        return True

    except Exception as e:
        print(f"ElevenLabs error: {e}", file=sys.stderr)
        return False


def play_audio(filepath: str) -> None:
    """Play audio file using system player."""
    if sys.platform == "darwin":
        subprocess.run(["afplay", filepath], check=False)
    elif sys.platform.startswith("linux"):
        players = ["mpv", "ffplay", "aplay", "paplay"]
        for player in players:
            try:
                if player == "ffplay":
                    subprocess.run([player, "-nodisp", "-autoexit", filepath],
                                   check=True, capture_output=True)
                elif player == "mpv":
                    subprocess.run([player, "--no-video", filepath],
                                   check=True, capture_output=True)
                else:
                    subprocess.run([player, filepath], check=True, capture_output=True)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        print("No audio player found.", file=sys.stderr)
    elif sys.platform == "win32":
        subprocess.run(["start", "/wait", filepath], shell=True, check=False)


def speak_system(text: str) -> bool:
    """Use system TTS as fallback."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["say", text], check=True)
            return True
        elif sys.platform.startswith("linux"):
            for cmd in [["espeak", text], ["festival", "--tts"]]:
                try:
                    if "festival" in cmd:
                        subprocess.run(cmd, input=text.encode(), check=True)
                    else:
                        subprocess.run(cmd, check=True)
                    return True
                except FileNotFoundError:
                    continue
            print("No TTS found. Install espeak: sudo apt install espeak", file=sys.stderr)
            return False
        elif sys.platform == "win32":
            ps_cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
            subprocess.run(["powershell", "-Command", ps_cmd], check=True)
            return True
        else:
            return False
    except Exception as e:
        print(f"System TTS error: {e}", file=sys.stderr)
        return False


def speak(text: str, voice: Optional[str] = None, use_elevenlabs: bool = True) -> None:
    """Speak the given text using the best available TTS."""
    if not TTS_ENABLED:
        print(f"[TTS Disabled] {text}")
        return

    # Resolve voice ID
    voice_id = ELEVENLABS_VOICE_ID
    if voice:
        voice_lower = voice.lower()
        if voice_lower in VOICE_MAP:
            voice_id = VOICE_MAP[voice_lower]
        elif len(voice) > 10:
            voice_id = voice

    # Try ElevenLabs first
    if use_elevenlabs and ELEVENLABS_API_KEY:
        if speak_elevenlabs(text, voice_id):
            return

    # Fall back to system TTS
    if not speak_system(text):
        print(f"🔊 {text}")


def log_notification(event: str, message: str, **kwargs) -> None:
    """Log notification to file for tracking."""
    log_dir = Path(__file__).parent.parent.parent / "stream-quant" / "output" / "research-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}-notifications.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "message": message,
        **kwargs
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quant Research Team Voice Notification System"
    )
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Message to speak (or use --event)"
    )
    parser.add_argument(
        "--event", "-e",
        choices=[
            "strategy_promoted", "prop_firm_complete", "pane_milestone",
            "budget_cap", "all_complete", "strategy_deployed",
            "error", "startup", "research_insight"
        ],
        help="Event type (generates appropriate message)"
    )
    parser.add_argument(
        "--voice", "-v",
        default=None,
        help="Voice to use (rachel, drew, paul, etc.)"
    )
    parser.add_argument(
        "--no-elevenlabs",
        action="store_true",
        help="Skip ElevenLabs and use system TTS only"
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Don't log notification to file"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a test notification"
    )

    # Event-specific arguments
    parser.add_argument("--strategy", help="Strategy name")
    parser.add_argument("--sharpe", type=float, help="Sharpe ratio")
    parser.add_argument("--pane", type=int, help="Pane number")
    parser.add_argument("--iterations", type=int, help="Iterations count")
    parser.add_argument("--validated", type=int, help="Validated strategies count")
    parser.add_argument("--passing", type=int, help="Passing prop firms count")
    parser.add_argument("--spent", type=float, help="Amount spent")
    parser.add_argument("--budget", type=float, help="Budget cap")
    parser.add_argument("--panes", type=int, help="Number of panes")
    parser.add_argument("--total-validated", type=int, help="Total validated strategies")
    parser.add_argument("--prop-firm-ready", type=int, help="Prop firm ready count")
    parser.add_argument("--error-msg", dest="error", help="Error message")
    parser.add_argument("--insight", help="Research insight")

    args = parser.parse_args()

    if args.test:
        test_message = "Quant Research Team notification system is working correctly."
        print(f"Testing: {test_message}")
        speak(test_message, args.voice, not args.no_elevenlabs)
        return

    # Generate message
    if args.event:
        kwargs = {k: v for k, v in vars(args).items()
                  if v is not None and k not in ['event', 'message', 'voice', 'no_elevenlabs', 'no_log', 'test']}
        message = get_event_message(args.event, **kwargs)
    elif args.message:
        message = args.message
    else:
        parser.print_help()
        return

    # Log notification
    if not args.no_log:
        log_notification(
            event=args.event or "custom",
            message=message,
            **{k: v for k, v in vars(args).items() if v is not None}
        )

    # Speak
    speak(message, args.voice, not args.no_elevenlabs)


if __name__ == "__main__":
    main()
