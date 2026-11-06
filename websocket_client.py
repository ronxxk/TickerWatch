import os
import signal
import threading

import upstox_client
from dotenv import load_dotenv

load_dotenv()


class WebSocket:
    def __init__(self, on_data_callback, *args: str):
        self.configuration = upstox_client.Configuration()
        self.configuration.access_token = os.getenv("api")

        self.instruments = list(args)
        self.on_data_callback = on_data_callback

        self._stop_event = threading.Event()  # set = shutdown requested
        self._closed = False                  # set = cleanup already done

        self.streamer = upstox_client.MarketDataStreamerV3(
            upstox_client.ApiClient(self.configuration),
            self.instruments,
            "ltpc",
        )

        self.streamer.on("open", self.on_open)
        self.streamer.on("message", self.on_message)
        self.streamer.on("error", self.on_error)
        self.streamer.on("close", self.on_close)

    def on_open(self):
        print("Connected to Upstox WebSocket!")

    def on_error(self, error):
        print("WebSocket Error:", error, "Please Ensure You are using right Instrument Keys\n")

    def on_close(self, *args):
        if self._stop_event.is_set():
            print("WebSocket Disconnected")
        else:
            print("WebSocket connection lost, auto-reconnect will try to restore it...")

    def on_message(self, message):
        if self._stop_event.is_set():
            return  
        feeds = message.get("feeds", {})
        for stock_name, data in feeds.items():
            ltpc_data = data.get("ltpc", {})
            ltp = ltpc_data.get("ltp")
            cp = ltpc_data.get("cp")

            if ltp is None or cp is None:
                continue

            try:
                self.on_data_callback({"stock_name": stock_name, "ltp": ltp, "cp": cp})
            except Exception as e:
                print(f"Callback error for {stock_name}: {e!r}")


    def _handle_signal(self, signum, frame):
        self._stop_event.set()  

    def stop(self):
        """Request shutdown. Safe to call from any thread."""
        self._stop_event.set()

    def _shutdown(self):
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        print("\nExiting stream...")

        try:
            self.streamer.auto_reconnect(False)  
        except Exception:
            pass
        try:
            self.streamer.disconnect()
        except Exception as e:
            print("Error while disconnecting:", e)

    def start(self):
        old_int = signal.signal(signal.SIGINT, self._handle_signal)
        old_term = signal.signal(signal.SIGTERM, self._handle_signal)
        try:
            self.streamer.auto_reconnect(True, 5, 10)
            self.streamer.connect()
            while not self._stop_event.wait(0.5):
                pass
        finally:
            self._shutdown()
            signal.signal(signal.SIGINT, old_int)
            signal.signal(signal.SIGTERM, old_term)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._shutdown()