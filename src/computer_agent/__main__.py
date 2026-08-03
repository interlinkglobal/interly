"""Run Interlink from the terminal."""

import sys
from collections.abc import Callable
from getpass import getpass

from groq import APIError, AuthenticationError, Groq

from computer_agent.browser import BROWSER
from computer_agent.chat import run_chat
from computer_agent.config import load_settings, save_api_key
from computer_agent.emergency import EmergencyStop
from computer_agent.models import GroqModel

SecretInput = Callable[[str], str]
Output = Callable[[str], None]


def prompt_for_valid_groq_key(
    secret_input: SecretInput = getpass,
    output: Output = print,
) -> str | None:
    """Prompt once, validate the key with Groq, and save only a working non-empty value."""
    output("Create a Groq API key at https://console.groq.com/keys")
    api_key = secret_input("Paste your Groq API key (input is hidden): ").strip()
    if not api_key:
        output("No API key entered. Nothing was saved.")
        return None
    try:
        Groq(api_key=api_key).models.list()
    except AuthenticationError:
        output("Groq rejected that API key. Nothing was saved.")
        return None
    except (APIError, OSError, RuntimeError) as error:
        output(f"Could not validate the key right now: {error}. Nothing was saved.")
        return None
    path = save_api_key(api_key)
    output(f"Validated and saved the key for your Windows account in {path.parent}")
    return api_key


def main() -> None:
    # Groq may return Unicode that the older Windows console encoding cannot print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    settings = load_settings()
    if not settings.groq_api_key:
        print("First-time Interly setup")
        api_key = prompt_for_valid_groq_key()
        if not api_key:
            raise SystemExit(1)
        settings.groq_api_key = api_key

    model = GroqModel(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
    )

    def reconfigure_groq() -> bool:
        api_key = prompt_for_valid_groq_key()
        if not api_key:
            return False
        model.update_api_key(api_key)
        return True
    emergency_stop = EmergencyStop()
    if emergency_stop.start():
        print("Emergency stop: press Esc to cancel the current request.")
    else:
        print("Warning: the global Esc emergency stop could not be started.")
    try:
        run_chat(
            model=model,
            emergency_stop=emergency_stop,
            reconfigure_groq=reconfigure_groq,
        )
    finally:
        BROWSER.close()
        emergency_stop.stop()


if __name__ == "__main__":
    main()
