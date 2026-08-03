"""Run Interlink from the terminal."""

import sys
from getpass import getpass

from computer_agent.browser import BROWSER
from computer_agent.chat import run_chat
from computer_agent.config import load_settings, save_api_key
from computer_agent.emergency import EmergencyStop
from computer_agent.models import GroqModel


def main() -> None:
    # Groq may return Unicode that the older Windows console encoding cannot print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    settings = load_settings()
    if not settings.groq_api_key:
        print("First-time Interly setup")
        print("Create a Groq API key at https://console.groq.com/keys")
        api_key = getpass("Paste your Groq API key (input is hidden): ").strip()
        if not api_key:
            raise SystemExit("No API key entered. Nothing was saved.")
        path = save_api_key(api_key)
        print(f"Saved the key for your Windows account in {path.parent}")
        settings.groq_api_key = api_key

    model = GroqModel(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
    )
    emergency_stop = EmergencyStop()
    if emergency_stop.start():
        print("Emergency stop: press Esc to cancel the current request.")
    else:
        print("Warning: the global Esc emergency stop could not be started.")
    try:
        run_chat(model=model, emergency_stop=emergency_stop)
    finally:
        BROWSER.close()
        emergency_stop.stop()


if __name__ == "__main__":
    main()
