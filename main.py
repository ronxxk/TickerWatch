from price_manager import PriceManager
from websocket_client import WebSocket

import os
from getpass import getpass

from dotenv import load_dotenv, set_key

ENV_FILE = ".env"
ENV_VAR = "api"  # must match os.getenv("api") in websocket_client.py


def ensure_api_key():
    load_dotenv(ENV_FILE)
    if os.getenv(ENV_VAR):
        return

    print("No Upstox access token found in environment or .env.")
    while True:
        token = getpass("Paste your Upstox access token (hidden): ").strip()
        if token:
            break
        print("Token can't be empty.")

    os.environ[ENV_VAR] = token  # used by WebSocket for this run

    save = input(f"Save to {ENV_FILE} for next time? (y/n) [n]: ").strip().lower()
    if save == "y":
        set_key(ENV_FILE, ENV_VAR, token)
        print(f"Saved to {ENV_FILE}.")
        
def ask_instruments() -> list[str]:
    print(
        "Enter the Instrument Keys for Upstox (e.g. NSE_EQ|INE002A01018).\n"
        "You can find keys via a search engine or the Upstox documentation.\n"
        "Press Enter on an empty line (or type ok) when finished."
    )
    keys = []
    while True:
        x = input("> ").strip()
        if x == "" or x.lower() == "ok":
            if keys:
                return keys
            print("Add at least one instrument first.")
            continue
        if x not in keys:
            keys.append(x)


def ask_choice(prompt: str, options: tuple, default: str) -> str:
    while True:
        x = input(f"{prompt} {options} [default: {default}]: ").strip().lower()
        if x == "":
            return default
        if x in options:
            return x
        print(f"Choose one of {options}.")


def ask_float(prompt: str, default: float) -> float:
    while True:
        x = input(f"{prompt} [default: {default}]: ").strip()
        if x == "":
            return default
        try:
            value = float(x)
            if value > 0:
                return value
        except ValueError:
            pass
        print("Enter a number greater than 0.")


def main(mode: str, instruments: list[str], min_difference: float = 2.00, min_percen: float = 1.00):
    manager = PriceManager(mode=mode, min_difference=min_difference, min_percen=min_percen)
    stream = WebSocket(manager.handle_incoming_tick, *instruments)
    stream.start()  # blocks until Ctrl+C


if __name__ == "__main__":
    try:
        ensure_api_key()
        instruments = ask_instruments()
        mode = ask_choice("Mode", ("points", "percent"), "points")
        if mode == "points":
            main(mode, instruments, min_difference=ask_float("Alert every how many points", 2.00))
        else:
            main(mode, instruments, min_percen=ask_float("Alert every how many % from prev close", 1.00))
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")