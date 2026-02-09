import os
import time
from datetime import datetime
from dhanhq import dhanhq

# GitHub Secrets se data uthana
CLIENT_ID = os.getenv('DHAN_CLIENT_ID')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN')
SL_PERCENTAGE = -7.5 

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

def sell_all_holdings():
    print("\n🚨 SL HIT! EXITING ALL POSITIONS...")
    holdings = dhan.get_holdings()
    if holdings['status'] == 'success' and holdings['data']:
        for stock in holdings['data']:
            symbol = stock.get('tradingSymbol')
            qty = int(stock.get('totalQty', 0))
            if qty > 0:
                dhan.place_order(
                    tag='AutoExit', transaction_type=dhan.SELL,
                    exchange_segment=dhan.NSE, product_type=dhan.CNC,
                    order_type=dhan.MARKET, validity='DAY',
                    security_id=stock.get('securityId'), quantity=qty
                )
                print(f"Sold: {symbol}")
        return True
    return False

def monitor():
    print(f"🛡️ Shield Active. SL: {SL_PERCENTAGE}% | Check: Every 1 Min")
    while True:
        # Market Time Check (IST 9:15 to 15:30)
        now = datetime.now().time()
        if now > datetime.strptime("15:35", "%H:%M").time():
            print("Market Closed. Stopping script.")
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
                    print(f"Time: {datetime.now().strftime('%H:%M:%S')} | PnL: {pnl:.2f}%", end="\r")
                    if pnl <= SL_PERCENTAGE:
                        if sell_all_holdings(): break
        except Exception as e:
            print(f"\nError: {e}")
            
        time.sleep(10) # 1 Minute interval

if __name__ == "__main__":
    monitor()
