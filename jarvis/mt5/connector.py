import os
import json

class MT5Connector:
    def __init__(self):
        self.connected = False
        self.terminal_path = "C:/Program Files/MetaTrader 5/terminal64.exe" # Default

    def connect(self):
        # Simulated connection
        print(f"Connecting to MT5 at {self.terminal_path}")
        self.connected = True
        return self.connected

    def send_order(self, symbol, order_type, volume, price, sl, tp):
        if not self.connected:
            return {"status": "error", "message": "MT5 not connected"}

        print(f"Sending {order_type} for {symbol}: Vol={volume}, P={price}, SL={sl}, TP={tp}")
        return {"status": "success", "ticket": 12345678}

    def get_account_info(self):
        return {
            "balance": 10420.50,
            "equity": 10420.50,
            "margin": 0.0,
            "drawdown": 0.0
        }
