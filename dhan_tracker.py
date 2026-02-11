"""
🚀 DHAN P&L TRACKER FOR GITHUB ACTIONS
Fully automated - runs during market hours
"""

import os
import time
import yfinance as yf
from dhanhq import dhanhq
from datetime import datetime

# Get credentials from environment variables (GitHub Secrets)
CLIENT_ID = os.getenv('DHAN_CLIENT_ID', '')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN', '')
STOP_LOSS_LIMIT = float(os.getenv('STOP_LOSS_LIMIT', '-6.5'))

# Initialize Dhan
dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

def format_inr(number):
    """Format in Indian rupee style"""
    abs_num = abs(int(number))
    s = str(abs_num)
    
    if len(s) <= 3: 
        res = s
    else:
        last_three = s[-3:]
        others = s[:-3]
        temp = ""
        while len(others) > 2:
            temp = "," + others[-2:] + temp
            others = others[:-2]
        res = others + temp + "," + last_three
    
    sign = "+" if number >= 0 else "-"
    return sign + "₹" + res

def get_live_price(symbol):
    """Get live price - try multiple sources"""
    # Try Yahoo Finance first
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        data = ticker.history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    
    # Try Dhan API
    try:
        response = dhan.market_quote(symbol=symbol, exchange='NSE')
        if response and response.get('status') == 'success':
            ltp = response.get('data', {}).get('LTP', 0)
            if ltp > 0:
                return float(ltp)
    except:
        pass
    
    return None

def check_portfolio():
    """Main function to check P&L"""
    print("\n" + "="*80)
    print(f"⏰ TIME: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}")
    print("="*80)
    
    try:
        # Get holdings
        response = dhan.get_holdings()
        
        if response.get('status') != 'success':
            print(f"❌ API Error: {response.get('remarks', 'Unknown')}")
            return
        
        holdings = response.get('data', [])
        
        if not holdings:
            print("⚠️ No holdings found")
            return
        
        print(f"✅ Found {len(holdings)} stocks\n")
        
        total_invested = 0
        total_current = 0
        
        print(f"{'Stock':<15} | {'Qty':<6} | {'Buy':<10} | {'Live':<10} | {'P&L':<15} | {'%'}")
        print("-"*80)
        
        for stock in holdings:
            name = stock.get('tradingSymbol', 'UNKNOWN')
            qty = int(stock.get('totalQty', 0))
            buy_price = float(stock.get('avgCostPrice', 0))
            
            if qty == 0:
                continue
            
            # Get live price
            live_price = get_live_price(name)
            
            if not live_price:
                live_price = float(stock.get('lastPrice', 0))
            
            if live_price <= 0:
                print(f"{name:<15} | {qty:<6} | {buy_price:<10.2f} | WAITING...")
                continue
            
            # Calculate
            invested = buy_price * qty
            current = live_price * qty
            pnl = current - invested
            pnl_pct = (pnl / invested) * 100
            
            total_invested += invested
            total_current += current
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"{name:<15} | {qty:<6} | {buy_price:<10.2f} | {live_price:<10.2f} | {format_inr(pnl):<15} | {emoji} {pnl_pct:+.2f}%")
        
        # Summary
        if total_invested > 0:
            net_pnl = total_current - total_invested
            net_pct = (net_pnl / total_invested) * 100
            
            print("\n" + "="*80)
            print("🎯 PORTFOLIO SUMMARY")
            print("="*80)
            print(f"💰 Investment  : {format_inr(total_invested)}")
            print(f"📈 Current     : {format_inr(total_current)}")
            
            emoji = "🟢" if net_pnl >= 0 else "🔴"
            print(f"{emoji} NET P&L     : {format_inr(net_pnl)} ({net_pct:+.2f}%)")
            print("="*80)
            
            # Stop loss check
            if net_pct <= STOP_LOSS_LIMIT:
                print("\n" + "🚨"*30)
                print(f"STOP LOSS HIT! Loss: {net_pct:.2f}% | Limit: {STOP_LOSS_LIMIT}%")
                print("🚨"*30)
    
    except Exception as e:
        print(f"🔥 Error: {e}")

if __name__ == "__main__":
    if not CLIENT_ID or not ACCESS_TOKEN:
        print("❌ Credentials not found in environment variables")
        exit(1)
    
    print("\n🚀 DHAN P&L TRACKER STARTED")
    print(f"📊 Stop Loss: {STOP_LOSS_LIMIT}%")
    
    # Run for market hours (6.5 hours = 390 minutes with 30 sec updates)
    max_runs = 780  # 390 minutes * 2 (30 sec each)
    
    for i in range(max_runs):
        check_portfolio()
        if i < max_runs - 1:
            print(f"\n⏳ Next update in 30 seconds... ({i+1}/{max_runs})")
            time.sleep(30)
    
    print("\n✅ Tracker completed for today!")
