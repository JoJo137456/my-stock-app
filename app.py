import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz

# 設定台灣時區
tw_tz = pytz.timezone('Asia/Taipei')

# === 1. 網頁基本設定 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")

# === CSS 優化：微軟正黑體 + 字體放大 ===
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700;
        }
        .stDataFrame {font-size: 1.1rem;}
    </style>
""", unsafe_allow_html=True)

# === 2. 定義關注清單 ===
stock_map = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

# === 3. 數據核心函數 ===
@st.cache_data(ttl=60)  # 每60秒更新一次
def get_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        df_intraday = stock.history(period="1d", interval="1m")
        info = stock.info
        return df_intraday, info
    except Exception as e:
        st.error(f"抓取 {symbol} 失敗: {e}")
        return pd.DataFrame(), {}

def calculate_metrics(df, info, idx_change_pct=0):
    if df.empty:
        return None

    # --- 優先使用 regularMarket 系列（收盤後最準）---
    prev_close = (info.get('regularMarketPreviousClose') or 
                  info.get('previousClose') or 
                  df['Open'].iloc[0] if len(df) > 0 else 0)

    current_price = (info.get('regularMarketPrice') or 
                     info.get('currentPrice') or 
                     df['Close'].iloc[-1] if len(df) > 0 else prev_close)

    change_amount = current_price - prev_close
    change_pct = (change_amount / prev_close) * 100 if prev_close else 0

    high = info.get('regularMarketDayHigh') or df['High'].max()
    low = info.get('regularMarketDayLow') or df['Low'].min()
    open_price = info.get('regularMarketOpen') or df['Open'].iloc[0]

    # 成交量（優先 regularMarketVolume）
    total_volume_shares = (info.get('regularMarketVolume') or 
                           info.get('volume') or 
                           df['Volume'].sum())

    # 成交金額估算（分鐘線最接近實際）
    turnover_est = (df['Close'] * df['Volume']).sum()

    # VWAP
    avg_price = turnover_est / total_volume_shares if total_volume_shares > 0 else current_price

    # 振幅
    amplitude_pct = ((high - low) / prev_close) * 100 if prev_close else 0

    # 較大盤
    vs_index = change_pct - idx_change_pct

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change_amount": change_amount,
        "change_pct": change_pct,
        "high": high,
        "low": low,
        "open": open_price,
        "volume_lots": total_volume_shares / 1000,
        "turnover_亿": turnover_est / 100000000,
        "avg_price": avg_price,
        "amplitude_pct": amplitude_pct,
        "vs_index": vs_index
    }

def draw_chart(df, color, prev_close, show_volume=True, height_price=280, height_volume=100):
    if df.empty:
        return alt.Chart().mark_text().encode(text=alt.Text("無數據"))
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # === Y軸範圍優化：保證小波動也看得見 ===
    price_min = df['Close'].min()
    price_max = df['Close'].max()
    price_range = price_max - price_min
    min_buffer_pct = prev_close * 0.008  # 至少 ±0.8% 空間
    buffer = max(price_range * 0.1, min_buffer_pct)
    
    y_min = price_min - buffer
    y_max = price_max + buffer

    # 價格面積 + 線圖
    area = alt.Chart(df).mark_area(color=color, opacity=0.15).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False)),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[y_min, y_max]), axis=alt.Axis(title='價格', grid=True))
    )

    line = alt.Chart(df).mark_line(color=color, strokeWidth=2.5).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[y_min, y_max])),
        tooltip=[alt.Tooltip('Time:T', format='%H:%M'), 
                 alt.Tooltip('Close:Q', title='價格', format='.2f'),
                 alt.Tooltip('Volume:Q', title='成交量', format=',')]
    )

    # 昨收基準線
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[6, 4], color='gray', strokeWidth=1.5, opacity=0.7
    ).encode(y='y')

    price_chart = (area + line + rule).properties(height=height_price)

    if show_volume:
        volume_chart = alt.Chart(df).mark_bar(color='#888888', opacity=0.7).encode(
            x='Time:T',
            y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量 (股)')),
            tooltip=alt.Tooltip('Volume:Q', format=',')
        ).properties(height=height_volume)

        return alt.vconcat(price_chart, volume_chart).resolve_scale(x='shared')
    else:
        return price_chart

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常\n👤 開發者：李宗念")

# === 5. 大盤與集團總覽 ===
with st.container(border=True):
    col_title, col_idx = st.columns([3, 2])
    
    with col_title:
        st.title("🏢 遠東集團戰情中心")
    
    # 大盤數據
    idx_df, idx_info = get_data("^TWII")
    idx_metrics = calculate_metrics(idx_df, idx_info) if not idx_df.empty else None
    
    with col_idx:
        st.markdown("##### 🇹🇼 台灣加權指數")
        if idx_metrics:
            idx_color = '#d62728' if idx_metrics['change_amount'] >= 0 else '#2ca02c'
            st.metric(
                "加權指數",
                f"{idx_metrics['current']:,.0f}",
                f"{idx_metrics['change_amount']:+.0f} ({idx_metrics['change_pct']:+.2f}%)",
                delta_color="inverse"
            )
            if not idx_df.empty:
                st.altair_chart(
                    draw_chart(idx_df, idx_color, idx_metrics['prev_close'], show_volume=False, height_price=80),
                    use_container_width=True
                )

# === 6. 集團股票總覽表 ===
st.subheader("📋 遠東集團股票總覽")
all_data = []
idx_change_pct = idx_metrics['change_pct'] if idx_metrics else 0

for name, sym in stock_map.items():
    df, info = get_data(sym)
    if not df.empty:
        m = calculate_metrics(df, info, idx_change_pct)
        if m:
            all_data.append({
                "股票": name,
                "股價": round(m['current'], 2),
                "漲跌": m['change_amount'],
                "漲跌%": m['change_pct'],
                "均價": round(m['avg_price'], 2),
                "成交量(張)": round(m['volume_lots']),
                "成交金額(億)": round(m['turnover_亿'], 2),
                "振幅%": round(m['amplitude_pct'], 2),
                "較大盤": m['vs_index']
            })

if all_data:
    df_all = pd.DataFrame(all_data)
    df_all = df_all.sort_values("漲跌%", ascending=False)
    
    def color_red_green(val, is_pct=False):
        if isinstance(val, (int, float)):
            color = 'red' if val > 0 else 'green' if val < 0 else 'black'
            suffix = '%' if is_pct else ''
            return f'color: {color}'
        return ''
    
    styled = df_all.style\
        .format({
            "股價": "{:.2f}",
            "漲跌": "{:+.2f}",
            "漲跌%": "{:+.2f}%",
            "均價": "{:.2f}",
            "成交量(張)": "{:,}",
            "成交金額(億)": "{:.2f}",
            "振幅%": "{:.2f}%",
            "較大盤": "{:+.2f}%"
        })\
        .applymap(lambda v: color_red_green(v, is_pct=True), subset=["漲跌%", "較大盤", "振幅%"])\
        .applymap(lambda v: color_red_green(v), subset=["漲跌"])
    
    st.dataframe(styled, use_container_width=True)
else:
    st.warning("目前無法取得任何股票數據")

# === 7. 選定股票詳細區塊 ===
df_stock, stock_info = get_data(ticker)
if df_stock.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    metrics = calculate_metrics(df_stock, stock_info, idx_change_pct)
    if metrics:
        chart_color = '#d62728' if metrics['change_amount'] >= 0 else '#2ca02c'
        
        with st.container(border=True):
            st.markdown(f"#### 📊 {selected_name} 詳細數據")
            
            # 第一排
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("💰 目前股價", f"{metrics['current']:.2f}", 
                     f"{metrics['change_amount']:+.2f} ({metrics['change_pct']:+.2f}%)", delta_color="inverse")
            c2.metric("📊 當日均價 (VWAP)", f"{metrics['avg_price']:.2f}")
            c3.metric("📦 總成交量", f"{metrics['volume_lots']:,.0f} 張")
            c4.metric("💎 成交金額", f"{metrics['turnover_亿']:.2f} 億")
            c5.metric("📏 當日振幅", f"{metrics['amplitude_pct']:.2f}%")
            
            st.divider()
            
            # 第二排
            c6, c7, c8, c9, c10 = st.columns(5)
            c6.metric("🔔 開盤價", f"{metrics['open']:.2f}")
            c7.metric("🔺 最高價", f"{metrics['high']:.2f}")
            c8.metric("🔻 最低價", f"{metrics['low']:.2f}")
            c9.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")
            c10.metric("🆚 較大盤", f"{metrics['vs_index']:+.2f}%", delta_color="inverse")
        
        # 走勢圖（含成交量）
        st.subheader("📈 今日即時走勢 (1分K) + 成交量")
        chart = draw_chart(df_stock, chart_color, metrics['prev_close'], show_volume=True)
        st.altair_chart(chart, use_container_width=True)

# === 頁尾 ===
st.divider()
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: #888888; font-size: 0.9em;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    最後更新：{current_time} (數據每60秒自動更新)
</div>
""", unsafe_allow_html=True)
