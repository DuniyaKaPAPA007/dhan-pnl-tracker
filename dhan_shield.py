import os
import time
import sys
from datetime import datetime, timedelta, timezone
from dhanhq import dhanhq

# --- CONFIGURATION ---
IST = timezone(timedelta(hours=5, minutes=30))
CLIENT_ID = os.getenv('DHAN_CLIENT_ID')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN')
SL_PERCENTAGE = -7.5  # Aapka Stop Loss limit

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

def format_indian_currency(number):
    """Paisa ko Indian Style mein dikhane ke liye (e.g. 2,37,000)"""
    s = str(int(number))
    if len(s) <= 3: return "₹" + s
    last_three = s[-3:]
    others = s[:-3]
    res = ""
    while len(others) > 2:
        res = "," + others[-2:] + res
        others = others[:-2]
    final = others + res + "," + last_three if others else last_three
    return "₹" + final

def log(msg):
    """Live logs dikhane ke liye"""
    timestamp = datetime.now(IST).strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)

def sell_all_holdings(pnl_val):
    log(f"🚨 STOP LOSS HIT ({pnl_val:.2f}%)! Saari positions bech raha hoon...")
    holdings = dhan.get_holdings()
    if holdings['status'] == 'success' and holdings.get('data'):
        for stock in holdings['data']:
            qty = int(stock.get('totalQty', 0))
            if qty > 0:
                try:
                    dhan.place_order(
                        tag='ShieldExit', transaction_type=dhan.SELL,
                        exchange_segment=dhan.NSE, product_type=dhan.CNC,
                        order_type=dhan.MARKET, quantity=qty, 
                        security_id=stock.get('securityId'), price=0
                    )
                    log(f"✅ Sold: {stock.get('tradingSymbol')}")
                except Exception as e:
                    log(f"❌ Error selling {stock.get('tradingSymbol')}: {e}")
        return True
    return False

def monitor():
    log("🛡️ SHIELD ACTIVE | Indian Format Enabled | Zero-Price Protection ON")
    
    while True:
        now_ist = datetime.now(IST)
        # Market Close Check (3:15 PM IST)
        if now_ist.hour == 15 and now_ist.minute >= 15:
            log("🛑 Market Closed. Robot so gaya.")
            break
            
        try:
            # 1. Get Funds for Remaining Margin display
            fund_data = dhan.get_fund_limits()
            avail_margin = 0
            if isinstance(fund_data, dict):
                avail_margin = float(fund_data.get('availabelBalance', fund_data.get('data', {}).get('availabelBalance', 0)))

            # 2. Get Holdings
            holdings = dhan.get_holdings()
            if holdings['status'] == 'success' and holdings.get('data'):
                data = holdings['data']
                t_buy, t_curr = 0, 0
                valid_count = 0
                
                print("-" * 60, flush=True)
                for i, s in enumerate(data, 1):
                    name = s.get('tradingSymbol', 'Unknown')
                    q = s.get('totalQty', 0)
                    lp = s.get('lastPrice', 0)
                    bp = s.get('avgCostPrice', 0)
                    
                    # SAFETY LOCK: 0-price glitch protection
                    if lp <= 0 or bp <= 0:
                        print(f"⚠️  {i}. {name:<20} | Price 0 aa rahi hai (Skipping...)", flush=True)
                        continue
                    
                    t_buy += (bp * q)
                    t_curr += (lp * q)
                    valid_count += 1
                    print(f"✅ {i:2}. {name:<20} | Qty: {q:<5} | Value: {format_indian_currency(lp*q)}", flush=True)
                
                if t_buy > 0:
                    pnl = ((t_curr - t_buy) / t_buy) * 100
                    print("-" * 60, flush=True)
                    log(f"📈 TOTAL INVESTMENT : {format_indian_currency(t_buy)}")
                    log(f"💰 CURRENT VALUE    : {format_indian_currency(t_curr)}")
                    log(f"🧧 CASH REMAINING   : {format_indian_currency(avail_margin)}")
                    log(f"📊 OVERALL PnL      : {pnl:.2f}%")
                    print("-" * 60, flush=True)
                    
                    if pnl <= SL_PERCENTAGE:
                        if sell_all_holdings(pnl): break
                else:
                    log("⚠️ Valid holdings ka data nahi mila.")
            else:
                log("⚠️ Portfolio khali hai ya API busy hai.")
                
        except Exception as e:
            log(f"🔥 Error: {str(e)}")
            
        time.sleep(15)

if __name__ == "__main__":
    monitor()
