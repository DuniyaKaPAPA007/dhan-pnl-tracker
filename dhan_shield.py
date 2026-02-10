import os
import time
from datetime import datetime, timedelta, timezone
from dhanhq import dhanhq

IST = timezone(timedelta(hours=5, minutes=30))
CLIENT_ID = os.getenv('DHAN_CLIENT_ID')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN')
SL_PERCENTAGE = -7.5 

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

def sell_all_holdings(actual_pnl):
    print(f"\n🚨 TRIGGERED! PnL was {actual_pnl:.2f}%. SELLING EVERYTHING...")
    holdings = dhan.get_holdings()
    if holdings['status'] == 'success' and holdings['data']:
        for stock in holdings['data']:
            symbol = stock.get('tradingSymbol')
            qty = int(stock.get('totalQty', 0))
            if qty > 0:
                try:
                    dhan.place_order(
                        tag='AutoExit', transaction_type=dhan.SELL,
                        exchange_segment=dhan.NSE, product_type=dhan.CNC,
                        order_type=dhan.MARKET, validity='DAY',
                        security_id=stock.get('securityId'), quantity=qty, price=0
                    )
                    print(f"✅ Sold: {symbol}")
                except Exception as e:
                    print(f"❌ Error selling {symbol}: {e}")
        return True
    return False

def monitor():
    print(f"🛡️ Shield RE-ARMED. Safety Lock: ON | SL: {SL_PERCENTAGE}%")
    while True:
        now_ist = datetime.now(IST)
        if now_ist.hour == 15 and now_ist.minute >= 35: break
            
        try:
            holdings = dhan.get_holdings()
            if holdings['status'] == 'success' and holdings.get('data'):
                t_buy, t_curr = 0, 0
                valid_data = True
                
                for s in holdings['data']:
                    q = s.get('totalQty', 0)
                    bp = s.get('avgCostPrice', 0)
                    lp = s.get('lastPrice', 0)
                    
                    # SAFETY LOCK: Agar price 0 hai, toh calculation skip karo (API Glitch)
                    if lp <= 0 or bp <= 0:
                        valid_data = False
                        break
                        
                    t_buy += (bp * q)
                    t_curr += (lp * q)
                
                if valid_data and t_buy > 0:
                    pnl = ((t_curr - t_buy) / t_buy) * 100
                    print(f"Time: {now_ist.strftime('%H:%M:%S')} | Live PnL: {pnl:.2f}%")
                    
                    if pnl <= SL_PERCENTAGE:
                        if sell_all_holdings(pnl): break
                else:
                    print("⚠️ Waiting for valid API data... (Price was 0)")
            
        except Exception as e:
            print(f"Error: {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    monitor()
