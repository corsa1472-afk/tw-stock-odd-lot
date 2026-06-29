import os
import json
import time
import threading
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "sinopac_config.json")
ORDERS_STORE_FILE = os.path.join(BASE_DIR, "orders_store.json")

class SinoPacConnector:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.is_logged_in = True
        self.api_key = "YahooFinance"
        self.secret_key = "YahooFinance"
        self.person_id = "DefaultUser"
        self.ca_path = ""
        self.ca_password = ""
        self.enabled = True
        
        self.orders = []
        self.monitor_thread = None
        self.stop_monitor = False
        
        self.load_orders()
        self.load_config()
        self.start_monitor_thread()

    def load_config(self):
        # We always stay enabled and logged in using Yahoo Finance
        self.enabled = True
        self.is_logged_in = True
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.person_id = config.get("person_id", "DefaultUser")
                    self.enabled = config.get("enabled", True)
            except Exception as e:
                print(f"Error loading config: {e}")

    def login(self, api_key="", secret_key="", person_id="", ca_path="", ca_password="", enabled=True):
        # Always succeed for simulated Yahoo mode
        self.is_logged_in = True
        self.enabled = enabled
        self.person_id = person_id if person_id else "DefaultUser"
        
        config = {
            "api_key": "YahooFinance",
            "secret_key": "YahooFinance",
            "person_id": self.person_id,
            "ca_path": ca_path,
            "ca_password": ca_password,
            "enabled": enabled
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
        self.start_monitor_thread()
        return True, "已成功切換至 Yahoo 數據模擬帳戶"

    def disable(self):
        self.enabled = False
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config["enabled"] = False
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return True

    def get_realtime_price(self, symbol):
        """
        Fetch the latest price using yfinance.
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1d")
            if not df.empty:
                return float(df['Close'].iloc[-1])
        except Exception as e:
            print(f"SinoPac Mock: Failed to fetch price for {symbol}: {e}")
        return None

    def load_orders(self):
        self.orders = []
        self.trailing_orders = []
        if os.path.exists(ORDERS_STORE_FILE):
            try:
                with open(ORDERS_STORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.orders = data.get("orders", [])
                        self.trailing_orders = data.get("trailing_orders", [])
                    else:
                        self.orders = data
                    print(f"SinoPac Mock: Loaded {len(self.orders)} orders from store.")
            except Exception as e:
                print(f"SinoPac Mock: Error loading orders store: {e}")
                
    def save_orders(self):
        try:
            os.makedirs(os.path.dirname(ORDERS_STORE_FILE), exist_ok=True)
            data_to_save = {
                "orders": self.orders,
                "trailing_orders": getattr(self, "trailing_orders", [])
            }
            with open(ORDERS_STORE_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"SinoPac Mock: Error saving orders store: {e}")

    def start_monitor_thread(self):
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.stop_monitor = False
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("SinoPac Mock: Background monitor thread started.")

    def place_odd_lot_order(self, code, action, price, quantity, lot_type="ODD", dry_run=True):
        """
        Mock placing an order (supports ODD/ROUND lot).
        """
        print(f"SinoPac Mock Order: {action} {quantity} shares ({lot_type}) of {code} at {price}")
        mock_id = f"mock-{lot_type.lower()}-{action.lower()}-{code}-{int(time.time())}"
        return {
            "status": "success",
            "order_id": mock_id,
            "message": f"模擬下單成功 (Action: {action}, Qty: {quantity}, Price: {price}, Type: {lot_type})",
            "dry_run": True
        }

    def _monitor_loop(self):
        cooldown_until = 0.0
        while not self.stop_monitor:
            try:
                if self.enabled:
                    trailing_orders = getattr(self, "trailing_orders", [])
                    # Keep displayed prices fresh even after a stop-loss/take-profit
                    # trigger. Only cancelled/deleted items stop receiving quotes.
                    monitoring_orders = [
                        o for o in self.orders + trailing_orders
                        if o.get("status") != "CANCELLED" and self._is_order_market_open(o)
                    ]
                    if monitoring_orders:
                        current_time = time.time()
                        if current_time < cooldown_until:
                            time.sleep(5)
                            continue
                            
                        symbols = list({o.get("symbol", f"{o['code']}.TW") for o in monitoring_orders})
                        try:
                            # Batch download latest 2-day price for all symbols under monitoring
                            df = yf.download(symbols, period="2d", progress=False)
                            if df.empty:
                                raise Exception("Empty dataframe returned from yfinance batch download")
                                
                            prices_map = {}
                            for sym in symbols:
                                if isinstance(df.columns, pd.MultiIndex):
                                    if ('Close', sym) in df.columns:
                                        series = df[('Close', sym)].dropna()
                                        if not series.empty:
                                            prices_map[sym] = {
                                                "close": float(series.iloc[-1]),
                                                "ref": float(series.iloc[-2]) if len(series) >= 2 else float(series.iloc[-1])
                                            }
                                else:
                                    if 'Close' in df.columns:
                                        series = df['Close'].dropna()
                                        if not series.empty:
                                            prices_map[sym] = {
                                                "close": float(series.iloc[-1]),
                                                "ref": float(series.iloc[-2]) if len(series) >= 2 else float(series.iloc[-1])
                                            }
                                            
                            updated = False
                            for o in monitoring_orders:
                                sym = o.get("symbol", f"{o['code']}.TW")
                                p_data = prices_map.get(sym)
                                if p_data is not None:
                                    current_price = p_data["close"]
                                    ref_price = p_data["ref"]
                                    o["last_price"] = current_price
                                    o["reference_price"] = ref_price
                                    updated = True
                                    
                                    sl = o.get("stop_loss_price")
                                    tp = o.get("stop_profit_price")
                                    triggered = False
                                    trigger_type = ""
                                    
                                    if sl and current_price <= sl:
                                        triggered = True
                                        trigger_type = "STOP_LOSS_TRIGGERED"
                                    elif tp and current_price >= tp:
                                        triggered = True
                                        trigger_type = "TAKE_PROFIT_TRIGGERED"
                                        
                                    if triggered and o.get("status") == "MONITORING":
                                        print(f"SinoPac Mock Monitor: {o['name']} ({o['code']}) triggered {trigger_type} at price {current_price}")
                                        o["status"] = trigger_type
                                        
                                        # Reversing order
                                        reverse_action = "SELL" if o["action"] == "BUY" else "BUY"
                                        lot_type = o.get("lot_type", "ODD")
                                        
                                        try:
                                            sell_res = self.place_odd_lot_order(
                                                code=o["code"],
                                                action=reverse_action,
                                                price=current_price,
                                                quantity=o["quantity"],
                                                lot_type=lot_type,
                                                dry_run=True
                                            )
                                            o["trigger_order_id"] = sell_res.get("order_id", "mock-trigger")
                                            o["message"] = f"觸發反向賣出，委託單號: {o['trigger_order_id']}"
                                            print(f"SinoPac Mock Monitor: Sell order placed: {sell_res}")
                                        except Exception as se:
                                            print(f"SinoPac Mock Monitor: Failed to place trigger sell order: {se}")
                                            o["status"] = "FAILED"
                                            o["error"] = str(se)
                                            
                            if updated:
                                self.save_orders()
                                
                        except Exception as e:
                            err_msg = str(e)
                            print(f"SinoPac Mock Monitor: Failed to fetch batch prices: {err_msg}")
                            # If we hit rate limits, trigger a 120-second cooldown
                            if "Too Many Requests" in err_msg or "Rate limit" in err_msg or "429" in err_msg:
                                print("SinoPac Mock Monitor: Rate limit hit, cooling down for 120s...")
                                cooldown_until = time.time() + 120
                            else:
                                cooldown_until = time.time() + 30
            except Exception as loop_err:
                print(f"SinoPac Mock Monitor: Exception in loop: {loop_err}")
                
            time.sleep(20)

    @staticmethod
    def _is_order_market_open(order):
        symbol = str(order.get("symbol", "")).upper()
        market = str(order.get("market", "")).upper()
        is_us = market == "US" or (symbol and not symbol.endswith((".TW", ".TWO")))
        timezone = ZoneInfo("America/New_York" if is_us else "Asia/Taipei")
        now = datetime.now(timezone)
        if now.weekday() >= 5:
            return False
        current = now.time().replace(tzinfo=None)
        if is_us:
            return dt_time(9, 30) <= current <= dt_time(16, 0)
        return dt_time(9, 0) <= current <= dt_time(13, 30)
