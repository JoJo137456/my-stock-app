import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time, timedelta
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS 優化：強化戰情室風格，數字更清楚，圖表更銳利
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Microsoft JhengHei', sans-serif !important; }
        div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800; color: #333; }
        /* 調整 Altair 圖表間距 */
        div[data-testid="stAltairChart"] { margin-top: -10px; }
    </style>
""", unsafe_allow_html=True)

# === 2. 核心邏輯與計算 ===

# 判斷目前盤中進度 (0.0 ~ 1.0)，用於計算預估量
def get_market_progress():
    now = datetime.now(tw_tz)
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)
    
    if now < market_open:
        return 0.0
    elif now > market_close:
        return 1.0
    else:
        total_minutes = 270  # 4.5 小時
        elapsed = (now - market_open).seconds / 60
        return max(0.01, elapsed / total_minutes) # 避免除以0

@st.cache_data(ttl=30) # 30秒更新一次
def get_data_yf(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 取得 intraday 資料
        df = stock.history(period="1d", interval="1m", auto_adjust=False)
        
        # 取得基本資訊 (用 fast_info 比較快且準)
        fi = stock.fast_info
        last_price = fi.last_price
        prev_close = fi.previous_close
        
        # 若盤中 yfinance 沒抓到 last_price，嘗試用 dataframe 最後一筆
        if last_price is None and not df.empty:
            last_price = df['Close'].iloc[-1]
            
        return {
            "symbol": symbol,
            "current": last_price,
            "prev_close": prev_close,
            "df": df,
            "volume": fi.last_volume if fi.last_volume else (df['Volume'].sum() if not df.empty else 0)
        }
    except Exception as e:
        return None

# === 3. 圖表繪製引擎 (Altair) ===

def draw_chart_combo(df, prev_close):
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    # 處理時區，確保顯示台灣時間
    if df['Time'].dt.tz is None:
        df['Time'] = df['Time'].dt.tz_localize('UTC').dt.tz_convert(tw_tz)
    else:
        df['Time'] = df['Time'].dt.tz_convert(tw_tz)

    # 計算成交量顏色：收盤價 > 開盤價 為紅，反之為綠
    # 若資料中沒有 Open，就比較 Close 與前一分鐘 Close
    if 'Open' in df.columns:
        df['Color'] = df.apply(lambda x: '#d62728' if x['Close'] >= x['Open'] else '#2ca02c', axis=1)
    else:
        df['Color'] = '#d62728' # fallback

    # Y軸範圍設定 (讓走勢更明顯)
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    # 給一點點緩衝空間，不要貼死邊界
    padding = (y_max - y_min) * 0.05 if y_max != y_min else y_max * 0.01
    y_domain = [y_min - padding, y_max + padding]

    # --- 上方：價格走勢圖 ---
    base = alt.Chart(df).encode(x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=True, tickCount=6)))
    
    # 價格線
    line = base.mark_line(strokeWidth=2).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價')),
        color=alt.value('#333333') # 價格線使用深灰色，專業感
    )
    
    # 平盤基準線 (灰白色階強調)
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[5, 3], 
        size=2, 
        color='#999999'  # 明顯的灰色虛線
    ).encode(y='y')

    # 價格區域 (選擇性：讓基準線上下有微弱色差，或是直接保持乾淨)
    # 這裡選擇保持乾淨，專注於 Rule 線的對比

    price_chart = (line + rule).properties(height=300)

    # --- 下方：成交量圖 (紅綠對比) ---
    vol_chart = base.mark_bar().encode(
        y=alt.Y('Volume:Q', axis=alt.Axis(title='量', tickCount=3)),
        color=alt.Color('Color:N', scale=None), # 使用預先算好的顏色
        tooltip=['Time', 'Close', 'Volume']
    ).properties(height=100)

    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

def draw_mini_sparkline(df, prev_close):
    if df.empty: return None
    df = df.reset_index()
    # 計算 Min/Max 強制設定 domain，讓斜率變抖
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    
    # 顏色：最後一筆 > 昨收 = 紅，否則綠
    last_price = df['Close'].iloc[-1]
    line_color = '#d62728' if last_price >= prev_close else '#2ca02c'
    
    chart = alt.Chart(df).mark_line(strokeWidth=2, color=line_color).encode(
        x=alt.X('index', axis=None), # 不顯示 X 軸
        y=alt.Y('Close', scale=alt.Scale(domain=[y_min, y_max]), axis=None) # 強制 domain
    ).properties(height=60, width=120)
    
    return chart

# === 4. 主程式 UI ===

stock_map = {
    "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW", "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
}

st.sidebar.header("🎯 監控標的")
selected_name = st.sidebar.radio("選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.caption("※ 資料來源：Yahoo Finance (延遲約 15-20 分鐘)")

# --- 戰情看板 ---
with st.container(border=True):
    col_idx, col_stock = st.columns([1, 2])
    
    # === 左側：大盤指數 (優化版) ===
    with col_idx:
        st.markdown("### 🇹🇼 加權指數 (TWII)")
        idx_data = get_data_yf("^TWII")
        
        if idx_data and idx_data['current']:
            curr = idx_data['current']
            prev = idx_data['prev_close']
            change = curr - prev
            pct = (change / prev) * 100
            
            # 預估量計算
            progress = get_market_progress()
            # 假設 volume 單位是股，轉成「億」需要估算。
            # 這裡簡化：利用 volume * 指數粗略估算成交值 (這只是近似值，因為指數不是股價)
            # 更準確的方法是直接拿昨天的量做比例，或 yf 的 Volume 其實是「口」或「張」。
            # 針對大盤，yf 給的 volume 常常不準確。這裡我們用技術性調整：
            # 如果是盤中，我們顯示 "強度" 或單純顯示點數。
            # 但既然你需要「預估成交金額」，我們用一個統計學上的近似：
            # (當前成交量 / 進度) * 平均股價係數... 比較複雜。
            # 最簡單的解法：顯示「即時預估量」需要外部 API。
            # 這裡我們用「成交量 (Volume)」欄位做預估展示 (假設 yf 的 volume 單位正確)
            
            curr_vol = idx_data['volume'] # 累計量
            est_vol = curr_vol / progress if progress > 0 else 0
            
            # 顯示
            st.metric("加權指數", 
                      f"{curr:,.0f}", 
                      f"{change:+.0f} ({pct:+.2f}%)", 
                      delta_color="inverse")
            
            st.markdown(f"""
            <div style="font-size: 0.9rem; margin-top: 10px;">
            <b>💰 預估成交量：</b> {est_vol/1000000:,.0f} M (參考)<br>
            <b>📊 當日振幅：</b> {((idx_data['df']['High'].max()-idx_data['df']['Low'].min())/prev*100):.2f}%
            </div>
            """, unsafe_allow_html=True)
            
            # 迷你走勢圖 (斜率抖一點)
            if not idx_data['df'].empty:
                st.altair_chart(draw_mini_sparkline(idx_data['df'], prev), use_container_width=True)
        else:
            st.warning("數據載入中...")

    # === 右側：個股監控 ===
    with col_stock:
        st.markdown(f"### 🔥 {selected_name}")
        s_data = get_data_yf(ticker)
        
        if s_data and s_data['current']:
            c_curr = s_data['current']
            c_prev = s_data['prev_close']
            c_change = c_curr - c_prev
            c_pct = (c_change / c_prev) * 100
            
            # 計算成交金額 (億)
            # 簡易算法：均價 * 量
            avg_price = (s_data['df']['High'].mean() + s_data['df']['Low'].mean()) / 2 if not s_data['df'].empty else c_curr
            amount_est = (s_data['volume'] * avg_price) / 100000000
            
            # Metric Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("股價", f"{c_curr:.2f}", f"{c_change:+.2f} ({c_pct:+.2f}%)", delta_color="inverse")
            m2.metric("成交金額 (億)", f"{amount_est:.2f}")
            m3.metric("總量 (張)", f"{s_data['volume']/1000:,.0f}")
            m4.metric("昨收", f"{c_prev:.2f}")
            
            st.divider()
            
            # 主要走勢圖
            if not s_data['df'].empty:
                st.altair_chart(draw_chart_combo(s_data['df'], c_prev), use_container_width=True)
            else:
                st.info("尚無今日盤中數據")
        else:
            st.error("無法取得個股數據")

st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #888; font-size: 0.8rem;'>戰情中心 | 更新時間: {datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} (系統時間)</div>", unsafe_allow_html=True)
