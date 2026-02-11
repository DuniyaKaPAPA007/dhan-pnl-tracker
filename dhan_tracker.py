"""
🚀 DHAN P&L TRACKER WITH AUTO-SELL
⚠️ WARNING: Auto-sells ALL stocks when SL hits!
30-second updates | 9:15 AM - 3:15 PM IST
"""

import os
import time
import yfinance as yf
from dhanhq import dhanhq
from datetime import datetime, timedelta

# Credentials from GitHub Secrets
CLIENT_ID = os.getenv('DHAN_CLIENT_ID', '')
ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN', '')
STOP_LOSS_LIMIT = float(os.getenv('STOP_LOSS_LIMIT', '-6.5'))
AUTO_SELL_ENABLED = os.getenv('AUTO_SELL_ENABLED', 'false').lower() == 'true'

# Config
UPDATE_INTERVAL = 30  # seconds
RUN_DURATION = 360  # minutes (6 hours)
MAX_ITERATIONS = (RUN_DURATION * 60) // UPDATE_INTERVAL

# Initialize Dhan
dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# Track if SL already executed (prevent multiple sells)
SL_EXECUTED = False

def format_inr(number):
    """Indian rupee formatting"""
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
    
    return ("+" if number >= 0 else "-") + "₹" + res

def get_live_price(symbol):
    """Fetch live price (Yahoo + Dhan backup)"""
    # Yahoo Finance (primary)
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        pass
    
    # Dhan API (backup)
    try:
        res = dhan.market_quote(symbol=symbol, exchange='NSE')
        if res and res.get('status') == 'success':
            ltp = res.get('data', {}).get('LTP', 0)
            if ltp > 0:
                return float(ltp)
    except:
        pass
    
    return None

def sell_all_holdings():
    """
    🚨 SELL ALL HOLDINGS AT MARKET PRICE
    Returns: (success_count, failed_count, total_value)
    """
    global SL_EXECUTED
    
    print("\n" + "🚨"*40)
    print(f"{'⚠️  EXECUTING STOP LOSS - SELLING ALL POSITIONS ⚠️':^120}")
    print("🚨"*40 + "\n")
    
    try:
        # Get current holdings
        response = dhan.get_holdings()
        
        if response.get('status') != 'success':
            print(f"❌ Failed to fetch holdings: {response.get('remarks')}")
            return 0, 0, 0
        
        holdings = response.get('data', [])
        
        if not holdings:
            print("⚠️ No holdings to sell")
            return 0, 0, 0
        
        success_count = 0
        failed_count = 0
        total_sell_value = 0
        
        print(f"{'Stock':<15} | {'Qty':<6} | {'Price':<10} | {'Status'}")
        print("-"*80)
        
        for stock in holdings:
            stock_name = stock.get('tradingSymbol', '')
            qty = int(stock.get('totalQty', 0))
            
            if qty <= 0:
                continue
            
            # Get current market price
            live_price = get_live_price(stock_name)
            
            if not live_price or live_price <= 0:
                live_price = float(stock.get('lastPrice', 0))
            
            if live_price <= 0:
                print(f"{stock_name:<15} | {qty:<6} | {'N/A':<10} | ❌ SKIPPED (No price)")
                failed_count += 1
                continue
            
            try:
                # Place MARKET SELL order
                order_response = dhan.place_order(
                    security_id=stock.get('securityId', ''),
                    exchange_segment=dhan.NSE,
                    transaction_type=dhan.SELL,
                    quantity=qty,
                    order_type=dhan.MARKET,
                    product_type=dhan.CNC,  # Delivery
                    price=0  # Market order
                )
                
                if order_response and order_response.get('status') == 'success':
                    order_id = order_response.get('data', {}).get('orderId', 'N/A')
                    sell_value = live_price * qty
                    total_sell_value += sell_value
                    
                    print(f"{stock_name:<15} | {qty:<6} | ₹{live_price:<9.2f} | ✅ SOLD (Order: {order_id})")
                    success_count += 1
                else:
                    error_msg = order_response.get('remarks', 'Unknown error')
                    print(f"{stock_name:<15} | {qty:<6} | ₹{live_price:<9.2f} | ❌ FAILED ({error_msg[:30]})")
                    failed_count += 1
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
                
            except Exception as e:
                print(f"{stock_name:<15} | {qty:<6} | ₹{live_price:<9.2f} | ❌ ERROR ({str(e)[:30]})")
                failed_count += 1
        
        # Summary
        print("\n" + "="*80)
        print(f"{'📊 SELL EXECUTION SUMMARY':^80}")
        print("="*80)
        print(f"✅ Successfully sold: {success_count} stocks")
        print(f"❌ Failed to sell: {failed_count} stocks")
        print(f"💰 Total sell value: {format_inr(total_sell_value)}")
        print("="*80 + "\n")
        
        SL_EXECUTED = True
        return success_count, failed_count, total_sell_value
        
    except Exception as e:
        print(f"\n🔥 Critical error in sell_all_holdings: {e}")
        return 0, 0, 0

def check_portfolio(iteration, total_iterations):
    """Check P&L and execute SL if needed"""
    global SL_EXECUTED
    
    now = datetime.now()
    progress = (iteration / total_iterations) * 100
    
    print("\n" + "="*100)
    print(f"⏰ {now.strftime('%d-%b %H:%M:%S')} | Update #{iteration}/{total_iterations} ({progress:.1f}%)")
    print("="*100)
    
    try:
        # Get holdings
        response = dhan.get_holdings()
        
        if response.get('status') != 'success':
            print(f"❌ API Error: {response.get('remarks', 'Unknown')}")
            return False
        
        holdings = response.get('data', [])
        
        if not holdings:
            print("⚠️ No holdings found")
            return False
        
        auto_sell_status = "🟢 ENABLED" if AUTO_SELL_ENABLED else "🔴 DISABLED"
        print(f"📊 Tracking {len(holdings)} stocks | SL: {STOP_LOSS_LIMIT}% | Auto-Sell: {auto_sell_status}")
        
        if SL_EXECUTED:
            print("⚠️ STOP LOSS ALREADY EXECUTED - Monitoring only")
        
        print()
        
        total_invested = 0
        total_current = 0
        
        # Table header
        print(f"{'Stock':<12} | {'Qty':<5} | {'Buy':<9} | {'Live':<9} | {'P&L':<14} | {'%':<8}")
        print("-"*100)
        
        for stock in holdings:
            name = stock.get('tradingSymbol', 'UNK')[:12]
            qty = int(stock.get('totalQty', 0))
            buy_price = float(stock.get('avgCostPrice', 0))
            
            if qty == 0:
                continue
            
            # Get live price
            live_price = get_live_price(stock.get('tradingSymbol', ''))
            if not live_price:
                live_price = float(stock.get('lastPrice', 0))
            
            if live_price <= 0:
                print(f"{name:<12} | {qty:<5} | {buy_price:<9.2f} | {'⏳ WAIT':<9} | {'---':<14} |")
                continue
            
            # Calculate
            invested = buy_price * qty
            current = live_price * qty
            pnl = current - invested
            pnl_pct = (pnl / invested) * 100
            
            total_invested += invested
            total_current += current
            
            # Display
            emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"{name:<12} | {qty:<5} | {buy_price:<9.2f} | {live_price:<9.2f} | {format_inr(pnl):<14} | {emoji} {pnl_pct:+6.2f}%")
        
        # Portfolio Summary
        if total_invested > 0:
            net_pnl = total_current - total_invested
            net_pct = (net_pnl / total_invested) * 100
            
            print("\n" + "="*100)
            print(f"{'🎯 PORTFOLIO SUMMARY':^100}")
            print("="*100)
            print(f"💰 Investment: {format_inr(total_invested):<20} | 📈 Current: {format_inr(total_current)}")
            
            emoji = "🟢" if net_pnl >= 0 else "🔴"
            print(f"{emoji} NET P&L  : {format_inr(net_pnl):<20} | Return: {net_pnl_pct:+.2f}%")
            print("="*100)
            
            # 🚨 STOP LOSS CHECK 🚨
            if net_pct <= STOP_LOSS_LIMIT and not SL_EXECUTED:
                print("\n" + "🚨"*50)
                print(f"{'⚠️  STOP LOSS TRIGGERED! ⚠️':^100}")
                print(f"{'Loss: ' + str(round(net_pct, 2)) + '% | Limit: ' + str(STOP_LOSS_LIMIT) + '%':^100}")
                print("🚨"*50)
                
                if AUTO_SELL_ENABLED:
                    print(f"\n{'🔴 AUTO-SELL IS ENABLED - EXECUTING SELL ORDERS...':^100}\n")
                    
                    # Execute sell
                    success, failed, value = sell_all_holdings()
                    
                    if success > 0:
                        print("\n✅ STOP LOSS EXECUTED SUCCESSFULLY!")
                        print(f"💰 Sold {success} positions worth {format_inr(value)}")
                        
                        # Exit the program after selling
                        print("\n🛑 Exiting tracker after SL execution...")
                        return "EXIT"
                    else:
                        print("\n❌ SELL EXECUTION FAILED - Check manually!")
                else:
                    print(f"\n⚠️ AUTO-SELL IS DISABLED - MANUAL ACTION REQUIRED!")
                    print("💡 Enable auto-sell by setting AUTO_SELL_ENABLED=true in GitHub Secrets\n")
            
            return True
        else:
            print("\n⚠️ No valid position data")
            return False
    
    except Exception as e:
        print(f"🔥 Error: {e}")
        return False

def main():
    """Main execution loop"""
    if not CLIENT_ID or not ACCESS_TOKEN:
        print("❌ Missing credentials!")
        return
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=RUN_DURATION)
    
    print("\n" + "🚀"*50)
    print(f"{'DHAN P&L TRACKER - AUTO-SELL MODE':^100}")
    print("🚀"*50)
    print(f"\n⏱️  Start: {start_time.strftime('%H:%M:%S')}")
    print(f"⏱️  End:   {end_time.strftime('%H:%M:%S')} (approx)")
    print(f"📊 Updates: Every {UPDATE_INTERVAL} seconds")
    print(f"🎯 Stop Loss: {STOP_LOSS_LIMIT}%")
    
    if AUTO_SELL_ENABLED:
        print(f"🔴 AUTO-SELL: ENABLED ⚠️")
        print(f"⚠️  ALL POSITIONS WILL BE SOLD IF SL HITS!")
    else:
        print(f"🟡 AUTO-SELL: DISABLED (Alert only)")
    
    print(f"📈 Total Updates: ~{MAX_ITERATIONS}")
    print("="*100)
    
    iteration = 0
    failed_count = 0
    
    while iteration < MAX_ITERATIONS:
        iteration += 1
        
        try:
            result = check_portfolio(iteration, MAX_ITERATIONS)
            
            # Exit if SL executed
            if result == "EXIT":
                print("\n✅ Program terminated after SL execution")
                break
            
            if result:
                failed_count = 0
            else:
                failed_count += 1
                
                if failed_count >= 10:
                    print("\n❌ Too many failures. Exiting.")
                    break
            
            # Sleep unless last iteration
            if iteration < MAX_ITERATIONS:
                print(f"\n⏳ Next update in {UPDATE_INTERVAL}s...")
                time.sleep(UPDATE_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n\n⛔ Stopped by user")
            break
        except Exception as e:
            print(f"\n🔥 Error: {e}")
            failed_count += 1
            if failed_count >= 5:
                break
            time.sleep(UPDATE_INTERVAL)
    
    # Summary
    print("\n" + "="*100)
    print(f"{'✅ TRACKING COMPLETED':^100}")
    print("="*100)
    print(f"Total Updates: {iteration}")
    print(f"Duration: {datetime.now() - start_time}")
    
    if SL_EXECUTED:
        print(f"🚨 Stop Loss was executed during this session")
    
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
