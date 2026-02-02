import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz
import requests  # 新增：用來抓大盤成交金額

# 台灣時區
tw_tz = pytz.timezone('Asia/Taipei')
today_str = datetime.now(tw_tz).strftime('%Y-%m-%d')

# === 1. 頁面設定 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")

# CSS 美化
st.markdown("""
    <style>
        html, body, [class*="css"] {font-family: 'Microsoft JhengHei', sans-serif !important;}
        div[data-testid="stMetricValue"] {font-size: 1.8rem !important; font-weight: 700;}
        .stDataFrame {font-size: 1.1rem;}
    </style>
""", unsafe_allow_html=True)

# === 2. 股票清單 ===
stock_map = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

# === 新增：抓取大盤成交金額（TWSE 即時 API）===
@st.cache_data(ttl=30)
def get_taiex_turnover():
    try:
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('msgArray') and len(data['msgArray']) > 0:
                tv_str = data['msgArray'][0].get('tv', '0')
                if tv_str and tv_str != '-':
                    turnover = float(tv_str.replace(',', ''))
                    return round(turnover, 2)  # 直接為「億」單位
        return None
    except Exception:
        return None

# === 3. 資料抓取 ===
@st.cache_data(ttl=45)
def get_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        df_intraday = stock.history(period="1d", interval="1m")
        info = stock.info
        return df_intraday, info
    except Exception as e:
        st.error(f"抓取 {symbol} 失敗: {e}")
        return pd.DataFrame(), {}

# === 4. 指標計算 ===
def calculate_metrics(df, info, idx_change_pct=0):
    if df.empty and not info:
        return None

    prev_close = (info.get('regularMarketPreviousClose') or 
                  info.get('previousClose') or 
                  df['Open'].iloc[0] if not df.empty else 0)

    current_price = (info.get('regularMarketPrice') or 
                     info.get('currentPrice') or 
                     df['Close'].iloc[-1] if not df.empty else prev_close)

    open_price = (info.get('regularMarketOpen') or 
                  df['Open'].iloc[0] if not df.empty else current_price)

    high = info.get('regularMarketDayHigh') or df['High'].max() if not df.empty else current_price
    low = info.get('regularMarketDayLow') or df['Low'].min() if not df.empty else current_price

    change_amount = current_price - prev_close
    change_pct = (change_amount / prev_close) * 100 if prev_close else 0

    total_volume_shares = (info.get('regularMarketVolume') or 
                           info.get('volume') or 
                           df['Volume'].sum() if not df.empty else 0)

    # VWAP 與成交金額（已優化避免偏低）
    if not df.empty and df['Volume'].sum() > 1000:
        turnover_est = (df['Close'] * df['Volume']).sum()
        avg_price = turnover_est / df['Volume'].sum()
        turnover_亿 = turnover_est / 100000000
    else:
        est_avg = (open_price + high + low + current_price) / 4
        avg_price = est_avg
        turnover_亿 = est_avg * total_volume_shares / 100000000

    amplitude_pct = ((high - low) / prev_close) * 100 if prev_close else 0
    vs_index = change_pct - idx_change_pct

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change_amount": change_amount,
        "change_pct": change_pct,
        "high": high,
        "low": low,
        "open": open_price,
        "volume_lots": round(total_volume_shares / 1000),
        "turnover_亿": round(turnover_亿, 2),
        "avg_price": round(avg_price, 2),
        "amplitude_pct": round(amplitude_pct, 2),
        "vs_index": round(vs_index, 2)
    }

# === 5. 圖表繪製 ===
def draw_chart(df, color, prev_close, show_volume=True, height_price=280, height_volume=100):
    if df.empty:
        return alt.Chart().mark_text().encode(text="無數據")
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    price_min = df['Close'].min()
    price_max = df['Close'].max()
    price_range = price_max - price_min
    min_buffer = prev_close * 0.015  # 至少 ±1.5%
    buffer = max(price_range * 0.2, min_buffer)
    
    y_min = price_min - buffer
    y_max = price_max + buffer

    area = alt.Chart(df).mark_area(color=color, opacity=0.15).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M')),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[y_min, y_max]), axis=alt.Axis(title='價格'))
    )
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2.5).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[y_min, y_max])),
        tooltip=['Time:T', 'Close:Q', 'Volume:Q']
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[6, 4], color='gray', opacity=0.7
    ).encode(y='y')

    price_chart = (area + line + rule).properties(height=height_price)

    if show_volume and df['Volume'].sum() > 0:
        volume_chart = alt.Chart(df).mark_bar(color='#888888', opacity=0.7).encode(
            x='Time:T',
            y='Volume:Q',
            tooltip='Volume:Q'
        ).properties(height=height_volume)
        return alt.vconcat(price_chart, volume_chart).resolve_scale(x='shared')
    return price_chart

# === 6. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption("✅ 系統連線正常\n👤 開發者：李宗念")

# === 7. 頂部 HUD（新增大盤成交金額）===
with st.container(border=True):
    col_title, col_date, col_idx = st.columns([2, 1, 2])
    
    with col_title:
        st.title("🏢 遠東集團戰情中心")
    
    with col_date:
        st.markdown(f"#### 📅 今日日期\n**{today_str}**")
    
    idx_df, idx_info = get_data("^TWII")
    idx_metrics = calculate_metrics(idx_df, idx_info) if not idx_df.empty else None
    taiex_turnover = get_taiex_turnover()  # 新增大盤成交金額
    
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
            # 新增：大盤成交金額
            if taiex_turnover is not None:
                st.metric("大盤成交金額", f"{taiex_turnover:,.2f} 億")
            else:
                st.caption("大盤成交金額：暫無數據（非交易時間或連線問題）")
            
            if not idx_df.empty:
                st.altair_chart(
                    draw_chart(idx_df, idx_color, idx_metrics['prev_close'], show_volume=False, height_price=90),
                    use_container_width=True
                )

# === 8. 集團總覽（維持不變）===
st.subheader("📋 遠東集團股票總覽")
all_data = []
idx_change_pct = idx_metrics['change_pct'] if idx_metrics else 0

for name, sym in stock_map.items():
    df, info = get_data(sym)
    m = calculate_metrics(df, info, idx_change_pct)
    if m:
        all_data.append({
            "股票": name,
            "股價": m['current'],
            "漲跌%": m['change_pct'],
            "漲跌": m['change_amount'],
            "均價": m['avg_price'],
            "成交量(張)": m['volume_lots'],
            "成交金額(億)": m['turnover_亿'],
            "振幅%": m['amplitude_pct'],
            "較大盤": m['vs_index']
        })

if all_data:
    df_all = pd.DataFrame(all_data).sort_values("漲跌%", ascending=False)
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
        .applymap(lambda v: 'color: red' if v > 0 else 'color: green' if v < 0 else '', 
                  subset=["漲跌", "漲跌%", "較大盤", "振幅%"])
    st.dataframe(styled, use_container_width=True)

# === 9. 個股詳細（維持不變）===
df_stock, stock_info = get_data(ticker)
if df_stock.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    metrics = calculate_metrics(df_stock, stock_info, idx_change_pct)
    if metrics:
        chart_color = '#d62728' if metrics['change_amount'] >= 0 else '#2ca02c'
        
        with st.container(border=True):
            st.markdown(f"#### 📊 {selected_name} 詳細數據")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("💰 目前股價", f"{metrics['current']:.2f}",
                     f"{metrics['change_amount']:+.2f} ({metrics['change_pct']:+.2f}%)", delta_color="inverse")
            c2.metric("📊 當日均價", f"{metrics['avg_price']:.2f}")
            c3.metric("📦 總成交量", f"{metrics['volume_lots']:,.0f} 張")
            c4.metric("💎 成交金額", f"{metrics['turnover_亿']:.2f} 億")
            c5.metric("📏 當日振幅", f"{metrics['amplitude_pct']:.2f}%")
            
            st.divider()
            c6, c7, c8, c9, c10 = st.columns(5)
            c6.metric("🔔 開盤價", f"{metrics['open']:.2f}")
            c7.metric("🔺 最高價", f"{metrics['high']:.2f}")
            c8.metric("🔻 最低價", f"{metrics['low']:.2f}")
            c9.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")
            c10.metric("🆚 較大盤", f"{metrics['vs_index']:+.2f}%", delta_color="inverse")
        
        st.subheader("📈 今日即時走勢 (1分K)")
        chart = draw_chart(df_stock, chart_color, metrics['prev_close'], show_volume=True)
        st.altair_chart(chart, use_container_width=True)

# === 頁尾 ===
st.divider()
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: #888888; font-size: 0.9em;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    最後更新：{current_time} (數據每45秒自動更新)
</div>
""", unsafe_allow_html=True)
