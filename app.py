import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import pytz

# === 1. 系統設定與 CSS 優化 (字體放大專區) ===
st.set_page_config(page_title="遠東集團戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS: 強制放大字體，去除多餘邊距，模擬財經網站排版
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Microsoft JhengHei', sans-serif !important; }
        
        /* 放大 Metric (股價大數字) */
        div[data-testid="stMetricValue"] { font-size: 3rem !important; font-weight: 700; }
        div[data-testid="stMetricDelta"] { font-size: 1.2rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 1.2rem !important; color: #555; }
        
        /* 調整表格字體 */
        div[data-testid="stDataFrame"] { font-size: 1.1rem !important; }
        
        /* 讓圖表更貼近邊界 */
        .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# === 2. 數據獲取邏輯 (Yahoo Finance) ===

STOCK_LIST = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

@st.cache_data(ttl=60)  # 60秒更新一次列表
def get_group_summary():
    """一次獲取所有股票的當下行情，製作頂部列表"""
    tickers = " ".join(STOCK_LIST.values())
    try:
        # 下載最後一天的數據 (包含 Open, Close 等)
        data = yf.download(tickers, period="5d", progress=False)
        
        # 整理成 DataFrame
        summary_data = []
        # yfinance download 的格式在多股時是 MultiIndex，需處理
        df_close = data['Close']
        
        for name, symbol in STOCK_LIST.items():
            try:
                # 取得最新價與昨收 (若盤中無法取得最新，這是一個 fallback)
                # 更精準的方式是用 Ticker.fast_info，但 download 比較適合批量
                # 這裡為了準確度，我們混合使用
                ticker_obj = yf.Ticker(symbol)
                fi = ticker_obj.fast_info
                
                curr = fi.last_price
                prev = fi.previous_close
                if curr and prev:
                    change = curr - prev
                    pct = (change / prev) * 100
                    summary_data.append({
                        "代號": symbol.replace(".TW", ""),
                        "名稱": name.split(" ")[1],
                        "現價": round(curr, 2),
                        "漲跌": round(change, 2),
                        "幅度(%)": round(pct, 2),
                        "昨收": round(prev, 2)
                    })
            except:
                continue
                
        return pd.DataFrame(summary_data)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_stock_detail(symbol):
    """獲取單檔股票的詳細分時走勢"""
    try:
        stock = yf.Ticker(symbol)
        # 抓取今天 (1d) 的 1分鐘 (1m) 走勢
        df = stock.history(period="1d", interval="1m", auto_adjust=False)
        fi = stock.fast_info
        
        return {
            "df": df,
            "info": fi
        }
    except:
        return None

# === 3. Yahoo 風格圖表繪製 ===

def draw_yahoo_chart(df, prev_close):
    if df.empty: return None
    
    # 資料處理
    df = df.reset_index()
    # 統一欄位名稱
    time_col = "Date" if "Date" in df.columns else "Datetime"
    if time_col in df.columns: df.rename(columns={time_col: "Time"}, inplace=True)
    
    # 時區轉換 (UTC -> TW)
    if df['Time'].dt.tz is None:
        df['Time'] = df['Time'].dt.tz_localize('UTC').dt.tz_convert(tw_tz)
    else:
        df['Time'] = df['Time'].dt.tz_convert(tw_tz)

    # 決定顏色：現在價格 > 昨收 = 紅，反之 = 綠 (Yahoo 邏輯)
    current_price = df['Close'].iloc[-1]
    is_up = current_price >= prev_close
    main_color = "#FF0000" if is_up else "#009900" # 鮮紅 或 鮮綠
    
    # 建立漸層填充 (像 Yahoo 那樣淡淡的底色)
    # 這裡我們用一個簡單的 Area chart，透明度調低
    
    # Y軸範圍：自動抓取並留白，避免貼底
    y_min = min(df['Close'].min(), prev_close)
    y_max = max(df['Close'].max(), prev_close)
    padding = (y_max - y_min) * 0.1
    domain = [y_min - padding, y_max + padding]

    base = alt.Chart(df).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=True, tickCount=6, labelFontSize=14))
    )

    # 1. 漸層背景 (Area)
    area = base.mark_area(opacity=0.1, color=main_color).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=domain), axis=None)
    )

    # 2. 主線 (Line)
    line = base.mark_line(strokeWidth=3, color=main_color).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=domain), axis=alt.Axis(title='股價', labelFontSize=14, titleFontSize=16))
    )
    
    # 3. 昨收基準線 (Dotted Rule) - 0% 基準
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[5, 5], 
        size=2, 
        color='#888888' # 深灰色
    ).encode(y='y')

    # 組合
    chart = (area + line + rule).properties(height=400)
    return chart

# === 4. 主程式介面 ===

# --- A. 頂部：集團股價小表 ---
st.subheader("📊 遠東集團即時看板")
df_summary = get_group_summary()

if not df_summary.empty:
    # 使用 dataframe 顯示，並設定高度使其不佔太多空間
    # 透過 style highlight 漲跌
    def color_change(val):
        if val > 0: return 'color: red'
        elif val < 0: return 'color: green'
        return 'color: gray'

    st.dataframe(
        df_summary.style.map(color_change, subset=['漲跌', '幅度(%)'])
                  .format({"現價": "{:.2f}", "漲跌": "{:+.2f}", "幅度(%)": "{:+.2f}%", "昨收": "{:.2f}"}),
        hide_index=True,
        use_container_width=True,
        height=250 # 固定高度
    )
else:
    st.warning("正在連線 Yahoo Finance 取得列表數據...")

st.markdown("---")

# --- B. 下方：詳細個股切換 ---
col_select, col_chart = st.columns([1, 4])

with col_select:
    st.markdown("### 🎯 選擇個股")
    selected_name = st.radio("監控標的", list(STOCK_LIST.keys()), label_visibility="collapsed")
    ticker = STOCK_LIST[selected_name]

# 獲取詳細資料
detail = get_stock_detail(ticker)

with col_chart:
    if detail and detail['info'].last_price:
        fi = detail['info']
        curr = fi.last_price
        prev = fi.previous_close
        diff = curr - prev
        pct = (diff / prev) * 100
        
        # 1. 顯示大標題數據 (Yahoo 風格)
        # 利用 HTML 自訂樣式，因為 st.metric 限制較多
        color_css = "red" if diff > 0 else "green"
        arrow = "▲" if diff > 0 else "▼"
        
        st.markdown(f"""
        <div style="display: flex; align-items: baseline; gap: 15px;">
            <h1 style="margin: 0; font-size: 3.5rem;">{curr:.2f}</h1>
            <h3 style="margin: 0; color: {color_css}; font-size: 2rem;">
                {arrow} {abs(diff):.2f} ({pct:+.2f}%)
            </h3>
            <span style="color: gray; font-size: 1.2rem;">成交量: {fi.last_volume/1000:,.0f} 張</span>
        </div>
        <div style="margin-top: 10px; font-size: 1.2rem; color: #666;">
            開盤: {fi.open:.2f} | 最高: {fi.day_high:.2f} | 最低: {fi.day_low:.2f} | 昨收: {prev:.2f}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. 繪製圖表
        if not detail['df'].empty:
            chart = draw_yahoo_chart(detail['df'], prev)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Yahoo Finance 尚未提供今日盤中走勢 (可能是盤前或剛開盤)")
            
    else:
        st.error("無法取得詳細數據，請稍後重試")

# Footer
st.markdown(f"<div style='text-align: right; color: #ccc; margin-top: 20px;'>資料來源: Yahoo Finance | 更新時間: {datetime.now(tw_tz).strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
