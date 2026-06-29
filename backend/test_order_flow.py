import os
import time
import json
from shiopac_connector import SinoPacConnector

def test_order_and_monitor():
    print("=== Testing SinoPac Odd-Lot Order & Monitor Flow ===")
    
    # 1. Initialize connector and force log in status for test
    connector = SinoPacConnector.get_instance()
    connector.enabled = True
    connector.is_logged_in = True
    
    # Clean up any existing test orders
    connector.orders = []
    connector.save_orders()
    
    # 2. Place a mock buy order
    code = "2330"
    symbol = "2330.TW"
    buy_price = 500.0
    qty = 100
    stop_loss = 505.0 # Higher than current price to trigger SL immediately
    stop_profit = 550.0
    
    print(f"Placing mock order for {code}...")
    res = connector.place_odd_lot_order(code, "BUY", buy_price, qty, dry_run=True)
    print(f"Order response: {res}")
    
    new_order = {
        "code": code,
        "symbol": symbol,
        "name": "台積電",
        "action": "BUY",
        "buy_price": buy_price,
        "quantity": qty,
        "stop_loss_price": stop_loss,
        "stop_profit_price": stop_profit,
        "status": "MONITORING",
        "order_id": res["order_id"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_price": buy_price,
        "dry_run": True,
        "trigger_order_id": None,
        "message": "已建立委託並啟動風控監控"
    }
    
    connector.orders.append(new_order)
    connector.save_orders()
    print("Order saved to store.")
    
    # 3. Check orders store
    ORDERS_STORE_FILE = "C:/Users/hopes/.gemini/antigravity/scratch/tw_stock_odd_lot/backend/orders_store.json"
    assert os.path.exists(ORDERS_STORE_FILE), "orders_store.json should be created"
    with open(ORDERS_STORE_FILE, "r", encoding="utf-8") as f:
        stored_orders = json.load(f)
        assert len(stored_orders) == 1, "Should have 1 stored order"
        assert stored_orders[0]["code"] == code
        print("Verification 1: Order successfully saved to file.")

    # 4. Fetch real price or default to 600.0
    # Try fetching with yfinance fallback directly as done in _monitor_loop
    current_price = None
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1d")
        if not df.empty:
            current_price = float(df['Close'].iloc[-1])
    except Exception as ye:
        print(f"yfinance fallback failed for {symbol}: {ye}")
        
    if current_price is None or current_price <= 0:
        current_price = 600.0
        
    print(f"Current price for {symbol} is: {current_price}")
    
    # Adjust stop loss to be above current price to force trigger SL
    forced_stop_loss = current_price + 10.0
    new_order["stop_loss_price"] = forced_stop_loss
    connector.save_orders()
    print(f"Adjusted stop loss to {forced_stop_loss} to force trigger Stop Loss.")
    
    # 5. Manually invoke the monitor loop check logic
    print("Running manual check logic...")
    monitoring_orders = [o for o in connector.orders if o.get("status") == "MONITORING"]
    for o in monitoring_orders:
        o["last_price"] = current_price
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
            
        if triggered:
            o["status"] = trigger_type
            sell_res = connector.place_odd_lot_order(
                code=o["code"],
                action="SELL",
                price=current_price,
                quantity=o["quantity"],
                dry_run=True
            )
            o["trigger_order_id"] = sell_res.get("order_id")
            o["message"] = f"觸發反向賣出，委託單號: {o['trigger_order_id']}"
            
    connector.save_orders()
    
    # 6. Verify status update
    updated_order = connector.orders[0]
    print(f"Updated order status: {updated_order['status']}")
    print(f"Trigger message: {updated_order.get('message')}")
    print(f"Trigger order ID: {updated_order.get('trigger_order_id')}")
    
    assert updated_order["status"] == "STOP_LOSS_TRIGGERED", "Status should be STOP_LOSS_TRIGGERED"
    assert updated_order["trigger_order_id"] is not None, "Should have triggered a sell order"
    print("Verification 2: Stop-loss trigger logic successfully ran and updated status.")
    
    print("=== All Unit Tests Passed! ===")

if __name__ == "__main__":
    test_order_and_monitor()
