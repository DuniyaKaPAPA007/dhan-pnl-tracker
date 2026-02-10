import os
import time
from datetime import datetime, timedelta, timezone
from dhanhq import dhanhq

# IST Timezone Setup
IST = timezone(timedelta(hours=5, minutes=30))

# Secrets se data uthana
CLIENT_ID = os.getenv('DHAN_CLIENT_ID')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN')
SL_PERCENTAGE = -7.5 

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

def sell_all_holdings():
    print("\n🚨 LOSS LIMIT HIT! EXITING ALL POSITIONS...")
    holdings = dhan.get_holdings()
    if holdings['status'] == 'success' and holdings['data']:
        for stock in holdings['data']:
            symbol = stock.get('tradingSymbol')
            qty = int(stock.get('totalQty', 0))
            security_id = stock.get('securityId')
            
            if qty > 0:
                try:
                    # Dhan API require price=0 for MARKET orders
                    dhan.place_order(
                        tag='AutoExit', 
                        transaction_type=dhan.SELL,
                        exchange_segment=dhan.NSE, 
                        product_type=dhan.CNC,
                        order_type=dhan.MARKET, 
                        validity='DAY',
                        security_id=security_id, 
                        quantity=qty,
                        price=0  # Fix for your error
                    )
                    print(f"✅ Sold: {symbol} | Qty: {qty}")
                except Exception as e:
                    print(f"❌ Failed to sell {symbol}: {e}")
        return True
    return False

def monitor():
    print(f"🛡️ Shield Active. SL: {SL_PERCENTAGE}% | Check: Every 15 Sec")
    while True:
        now_ist = datetime.now(IST)
        
        # 3:35 PM IST par script stop hogi
        if now_ist.hour == 15 and now_ist.minute >= 35:
            print(f"Market Closed ({now_ist.strftime('%H:%M')}). Stopping.")
            break
            
        try:
            holdings = dhan.get_holdings()
            if holdings['status'] == 'success' and holdings['data']:
                t_buy, t_curr = 0, 0
                for s in holdings['data']:
                    q = s.get('totalQty', 0)
                    t_buy += (s.get('avgCostPrice', 0) * q)
                    t_curr += (s.get('lastPrice', 0) * q)
                
                if t_buy > 0:
                    pnl = ((t_curr - t_buy) / t_buy) * 100
                    print(f"Time: {now_ist.strftime('%H:%M:%S')} | PnL: {pnl:.2f}%")
                    if pnl <= SL_PERCENTAGE:
                        if sell_all_holdings(): break
            else:
                print("Checking... (No holdings or API issue)")
        except Exception as e:
            print(f"\nError: {e}")
            
        time.sleep(15) # 15 seconds interval

if __name__ == "__main__":
    monitor()
