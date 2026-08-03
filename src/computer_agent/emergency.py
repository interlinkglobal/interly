"""Global emergency-stop handling for active Interly sessions."""

from threading import Event
from typing import Any


class EmergencyStop:
    """Listen for Escape globally and expose a thread-safe cancellation flag."""

    def __init__(self) -> None:
        self._event = Event()
        self._listener: Any | None = None

    def start(self) -> bool:
        """Start the global Escape listener, returning False if hooks are unavailable."""
        try:
            from pynput import keyboard

            def on_press(key: Any) -> None:
                if key == keyboard.Key.esc:
                    self._event.set()

            self._listener = keyboard.Listener(on_press=on_press)
            self._listener.daemon = True
            self._listener.start()
        except (ImportError, OSError, RuntimeError):
            return False
        return True

    def reset(self) -> None:
        self._event.clear()

    def requested(self) -> bool:
        return self._event.is_set()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
