from websocket_client import WebSocket

class PriceManager:
    def __init__(self, mode: str = "points", min_difference: float = 2.00, min_percen: float = 1.00):
        if mode not in ("points", "percent"):
            raise ValueError("mode must be 'points' or 'percent'")
        print("Trading Engine Initialized.")
        self.mode = mode
        self.min_difference = min_difference  # points mode: move since last print
        self.min_percen = min_percen          # percent mode: band width vs prev close
        self.last_printed = {}  # name -> LTP at last print (points mode)
        self.last_band = {}     # name -> % band at last print (percent mode)

    def handle_incoming_tick(self, data: dict):
        name = data.get("stock_name")
        ltp = data.get("ltp")
        cp = data.get("cp")

        if name is None or ltp is None or not cp:
            return  # bad tick or cp == 0

        pct_change = round(((ltp - cp) / cp) * 100, 3)

        if self.mode == "points":
            prev = self.last_printed.get(name)
            qualified = prev is None or abs(ltp - prev) >= self.min_difference
            if qualified:
                self.last_printed[name] = ltp
        else:
            band = int(pct_change / self.min_percen)  # truncates toward 0
            qualified = self.last_band.get(name) != band  # True on first tick
            if qualified:
                self.last_band[name] = band

        if qualified:
            print(f"[RECEIVED TICK] {name} -> LTP: {ltp} | Prev Close: {cp} | Change: {pct_change}%")


if __name__ == "__main__":
    from websocket_client import WebSocket

    manager = PriceManager(mode="points", min_difference=2.00)
    # manager = PriceManager(mode="percent", min_percen=1.00)

    stream = WebSocket(
        manager.handle_incoming_tick,
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|Nifty 100",
    )
    stream.start()