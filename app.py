# 記得在最上面新增這行 import
import requests 

# === 修改後的 get_data 函式 (已戴上人類面具) ===
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        # 1. 製作面具：設定 User-Agent，偽裝成一般的 Chrome 瀏覽器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 2. 建立連線 Session 並戴上面具
        session = requests.Session()
        session.headers.update(headers)

        # 3. 將這個偽裝好的 session 傳給 yfinance
        ticker = yf.Ticker(symbol, session=session)
        
        # --- 以下邏輯不變，但加上更多保護 ---
        
        # 嘗試取得即時資訊
        try:
            info = ticker.info
            current = info.get('currentPrice') or info.get('regularMarketPrice')
            prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        except:
            current = None
            prev_close = None
        
        # 嘗試取得 K 線圖 (優先抓 1 天 5 分鐘)
        df = ticker.history(period="1d", interval="5m")
        
        # 如果抓不到 (可能盤前或盤後)，改抓 5 天的 60 分鐘線
        if df.empty:
            df = ticker.history(period="5d", interval="60m")
            if not df.empty:
                # 只留最後一天的資料
                last_day = df.index[-1].date()
                df = df[df.index.date == last_day]

        # 補救措施：如果還是沒有當前價格，用 K 線最後一筆
        if current is None and not df.empty:
            current = df['Close'].iloc[-1]
            
        # 如果真的完全抓不到，回傳 None
        if current is None:
            return None

        # 計算其他數據
        volume = df['Volume'].sum() if not df.empty else 0
        if not df.empty:
            open_price = df['Open'].iloc[0]
            high = df['High'].max()
            low = df['Low'].min()
            typical = (df['High'] + df['Low'] + df['Close']) / 3
            if volume > 0:
                vwap = (typical * df['Volume']).sum() / volume
            else:
                vwap = df['Close'].mean()
        else:
            open_price = high = low = vwap = current

        return {
            "df": df,
            "current": current,
            "prev_close": prev_close or current,
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "vwap": vwap,
            "currency": info.get('currency', 'TWD')
        }
            
    except Exception as e:
        print(f"❌ {symbol} 讀取失敗: {e}") # 這會印在你的後台，方便除錯
        return None
