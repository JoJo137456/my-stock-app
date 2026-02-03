import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import pytz

# === 1. 系統設定與 CSS 優化 ===
st.set_page_config(page_title="遠東集團戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS: 強制放大字體，模擬財經網站排版
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

# === 2. 數據獲取邏輯 ===

STOCK_LIST = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

@st.cache_data(ttl=60)
def get_group_summary():
    """一次獲取所有股票的當下行情，製作頂部列表"""
    tickers = " ".join(STOCK_LIST.values())
    try:
        data = yf.download(tickers, period="5d", progress=False)
        summary_data = []
        
        for name, symbol in STOCK_LIST.items():
            try:
                # 這裡改用 Ticker 個別抓取以獲得更即時的 FastInfo，並處理錯誤
                t = yf.Ticker(symbol)
                fi = t.fast_info
                # 提取數值，避免直接存物件
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
        df = stock.history(period="1d", interval="1m", auto_adjust=False)
        fi = stock.fast_info
        
        # === 關鍵修正：將 FastInfo 物件轉換為純字典 ===
        # Streamlit 無法快取 FastInfo 物件，必須轉成 dict
        info_dict = {
            "last_price": fi.last_price,
            "previous_close": fi.previous_close,
            "open": fi.open,
            "day_high": fi.day_high,
            "day_low": fi.day_low,
            "last_volume": fi.last_volume
        }
        
        # 處理 df 若為空的情況
        if df.empty and info_dict["last_price"] is not None:
             # 如果盤前沒資料，至少回傳基本資訊
             pass

        return {
            "df": df,
            "info": info_dict
        }
    except Exception as e:
        return None

# === 3. Yahoo 風格圖表繪製 ===

def draw_yahoo_chart(df, prev_close):
    if df.empty: return None
    
    df = df.reset_index()
    time_col = "Date" if "Date" in df.columns else "Datetime"
    if time_col in df.columns: df.rename(columns={time_col: "Time"}, inplace=True)
    
    if df['Time'].dt.tz is None:
        df['Time'] = df['Time'].dt.tz_localize('UTC').dt.tz_convert(tw_tz)
    else:
        df['Time'] = df['Time'].dt.tz_convert(tw_tz)

    # 顏色邏輯
    current_price = df['Close'].iloc[-1]
    is_up = current_price >= prev_close
    main_color = "#FF0000" if is_up else "#009900" # 紅漲綠跌
    
    y_min = min(df['Close'].min(), prev_close)
    y_max = max(df['Close'].max(), prev_close)
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    domain = [y_min - padding, y_max + padding]

    base = alt.Chart(df).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=True, tickCount=6, labelFontSize=14))
    )

    # 1. 漸層背景
    area = base.mark_area(opacity=0.1, color=main_color).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=domain), axis=None)
    )

    # 2. 主線
    line = base.mark_line(strokeWidth=3, color=main_color).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=domain), axis=alt.Axis(title='股價', labelFontSize=14, titleFontSize=16))
    )
    
    # 3. 昨收基準線
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[5, 5], size=2, color='#888888'
    ).encode(y='y')

    return (area + line + rule).properties(height=400)

# === 4. 主程式介面 ===

# --- A. 頂部：集團股價小表 ---
st.subheader("📊 遠東集團即時看板")
df_summary = get_group_summary()

if not df_summary.empty:
    def color_change(val):
        if val > 0: return 'color: red'
        elif val < 0: return 'color: green'
        return 'color: gray'

    st.dataframe(
        df_summary.style.map(color_change, subset=['漲跌', '幅度(%)'])
                  .format({"現價": "{:.2f}", "漲跌": "{:+.2f}", "幅度(%)": "{:+.2f}%", "昨收": "{:.2f}"}),
        hide_index=True,
        use_container_width=True,
        height=250
    )
else:
    st.info("正在連線 Yahoo Finance 取得列表數據... (若盤中無數據請稍後)")

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
    # 修正：現在 detail['info'] 是一個字典，所以用 ['key'] 訪問，而不是 .attr
    if detail and detail['info']['last_price']:
        info = detail['info']
        curr = info['last_price']
        prev = info['previous_close']
        
        # 防止 prev 為 None (如新上市或資料錯誤)
        if prev is None: prev = curr 
        
        diff = curr - prev
        pct = (diff / prev) * 100
        
        # HTML 樣式 (Yahoo 風格)
        color_css = "red" if diff > 0 else "green"
        arrow = "▲" if diff > 0 else "▼"
        if diff == 0: 
            color_css = "gray"
            arrow = "-"
        
        vol_str = f"{info['last_volume']/1000:,.0f}" if info['last_volume'] else "-"
        open_str = f"{info['open']:.2f}" if info['open'] else "-"
        high_str = f"{info['day_high']:.2f}" if info['day_high'] else "-"
        low_str = f"{info['day_low']:.2f}" if info['day_low'] else "-"
        
        st.markdown(f"""
        <div style="display: flex; align-items: baseline; gap: 15px;">
            <h1 style="margin: 0; font-size: 3.5rem;">{curr:.2f}</h1>
            <h3 style="margin: 0; color: {color_css}; font-size: 2rem;">
                {arrow} {abs(diff):.2f} ({pct:+.2f}%)
            </h3>
            <span style="color: gray; font-size: 1.2rem;">成交量: {vol_str} 張</span>
        </div>
        <div style="margin-top: 10px; font-size: 1.2rem; color: #666;">
            開盤: {open_str} | 最高: {high_str} | 最低: {low_str} | 昨收: {prev:.2f}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # 繪圖
        if not detail['df'].empty:
            chart = draw_yahoo_chart(detail['df'], prev)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Yahoo Finance 尚未提供今日盤中走勢 (可能是盤前或剛開盤)")
            
    else:
        st.error("無法取得詳細數據，請稍後重試")

# Footer
st.markdown(f"<div style='text-align: right; color: #ccc; margin-top: 20px;'>資料來源: Yahoo Finance | 更新時間: {datetime.now(tw_tz).strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
