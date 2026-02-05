import twstock
import time

def analyze_stock(stock_code):
    print(f"⚔️  正在偵察代號 {stock_code} 的市場情資...")
    
    try:
        # 1. 建立股票物件
        stock = twstock.Stock(stock_code)
        
        # 2. 獲取最近 31 天的收盤價 (用來計算月均價)
        # twstock 會自動抓取最近的資料
        prices = stock.price[-31:] 
        
        if not prices:
            print("❌ 無法獲取數據，請檢查代號是否正確。")
            return

        # 3. 提取關鍵數據
        latest_price = prices[-1]  # 最新收盤價
        latest_date = stock.date[-1] # 最新日期
        start_date = stock.date[-31] # 31天前的日期
        
        # 4. 計算簡單估值 (月均價)
        avg_price = sum(prices) / len(prices)
        
        # 5. 判斷乖離率 (現在價格 vs 平均價格)
        gap = ((latest_price - avg_price) / avg_price) * 100
        
        # 6. 顯示戰情報告
        print("\n" + "="*40)
        print(f"📊 【戰情報告】 股票代號: {stock_code}")
        print(f"📅 資料日期: {latest_date.strftime('%Y-%m-%d')}")
        print("-" * 40)
        print(f"💰 最新收盤價: {latest_price} 元")
        print(f"⚖️ 近31日均價: {avg_price:.2f} 元 (月線成本)")
        print("-" * 40)
        
        # 簡單的策略判斷
        if gap > 5:
            print(f"⚠️ 狀態: 過熱 (高於均價 {gap:.1f}%) -> 敵軍士氣正旺，追高請小心")
        elif gap < -5:
            print(f"💎 狀態: 超跌 (低於均價 {abs(gap):.1f}%) -> 地板上有黃金，可考慮布局")
        else:
            print(f"⚖️ 狀態: 盤整 (差距 {gap:.1f}%) -> 雙方對峙中，價格合理")
            
        print("="*40 + "\n")

    except Exception as e:
        print(f"❌ 發生預期外的錯誤: {e}")

# --- 主程式開始 ---
if __name__ == '__main__':
    # 你可以在這裡改成你想查的股票，例如 '2330'(台積電), '0050', '2603'(長榮)
    target_stock = '2330' 
    analyze_stock(target_stock)
    
    # 防止視窗執行完馬上關閉 (如果你是用點兩下執行)
    input("按 Enter 鍵結束偵察...")
