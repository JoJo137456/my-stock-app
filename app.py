import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz
import requests

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

# === 3. 新增 Sina API 抓取個股精準數據（成交金額、均價、成交量最準）===
@st.cache_data(ttl=30)
def get_sina_stock_data(code):  # code 如 "1402"
    try:
        url = f"https://hq.sinajs.cn/list=tw{code}"
        response = requests.get(url, timeout=10).text
        if "hq_str_tw" in response:
            data = response.split('"')[1].split(',')
            if len(data) >= 10 and data[8].isdigit():
                current = float(data[3])
                prev_close = float(data[2])
                open_p = float(data[1])
                high = float(data[4])
                low = float(data[5])
                volume_lots = int(data[8])  # 直接為「張」
                turnover_yuan = int(data[9])  # 元
                turnover_亿 = turnover_yuan / 100000000
                avg_price = turnover_yuan / (volume_lots * 1000) if volume_lots > 0 else current
                change_amount = current - prev_close
                change_pct = (change_amount / prev_close) * 100 if prev_close else 0
                amplitude_pct = ((high - low) / prev_close) * 100 if prev_close else 0
                
                return {
                    "current": round(current, 2),
                    "prev_close": round(prev_close, 2),
                    "open": round(open_p, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "change_amount": round(change_amount, 2),
                    "change_pct": round(change_pct, 2),
                    "volume_lots": volume_lots,
                    "turnover_亿": round(turnover_亿, 2),
                    "avg_price": round(avg_price, 2),
                    "amplitude_pct": round(amplitude_pct, 2)
                }
        return None
    except:
        return None

# === 4. 大盤成交金額（TWSE API，盤後仍會保留當日結算值）===
@st.cache_data(ttl=30)
def get_taiex_turnover():
    try:
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('msgArray'):
            tv_str = data['msgArray'][0].get('tv', '0')
            if tv_str != '-' and tv_str:
                turnover = float(tv_str.replace(',', ''))
                return round(turnover, 2)
        return None
    except:
        return None

# === 5. yfinance 只用來抓分鐘線（走勢圖）===
@st.cache_data(ttl=45)
def get_intraday_chart(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1d", interval="1m")
        return df
    except:
        return pd.DataFrame()

# === 6. 指標計算（優先 Sina 精準數據，fallback yfinance）===
def get_metrics(symbol, idx_change_pct=0):
    code = symbol[:-3]  # e.g., "1402"
    sina_data = get_sina_stock_data(code)
    
    if sina_data:
        sina_data["vs_index"] = round(sina_data["change_pct"] - idx_change_pct, 2)
        return sina_data, True  # True 表示用了 Sina
    
    # fallback yfinance（較不準，僅備用）
    df = get_intraday_chart(symbol)
    if df.empty:
        return None, False
    
    info = yf.Ticker(symbol).info
    prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose') or df['Open'].iloc[0]
    current = info.get('regularMarketPrice') or info.get('currentPrice') or df['Close'].iloc[-1]
    change_amount = current - prev_close
    change_pct = (change_amount / prev_close) * 100 if prev_close else 0
    
    return {
        "current": round(current, 2),
        "prev_close": round(prev_close, 2),
        "open": round(df['Open'].iloc[0], 2),
        "high": round(df['High'].max(), 2),
        "low": round(df['Low'].min(), 2),
        "change_amount": round(change_amount, 2),
        "change_pct": round(change_pct, 2),
        "volume_lots": round(df['Volume'].sum() / 1000),
        "turnover_亿": round((df['Close'] * df['Volume']).sum() / 100000000, 2),
        "avg_price": round(((df['Close'] * df['Volume']).sum() / df['Volume'].sum()) if df['Volume'].sum() > 0 else current, 2),
        "amplitude_pct": round(((df['High'].max() - df['Low'].min()) / prev_close) * 100, 2),
        "vs_index": round(change_pct - idx_change_pct, 2)
    }, False

# === 7. 圖表繪製（強制放大波動，讓起伏超明顯）===
def draw_chart(df, color, prev_close, show_volume=True, height_price=280, height_volume=100):
    if df.empty:
        return alt.Chart().mark_text().encode(text="無數據")
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    price_min = df['Close'].min()
    price_max = df['Close'].max()
    actual_range = price_max - price_min
    
    # 強制至少 ±3% 空間（即使波動只有 0.1% 也會拉開，讓線條上下明顯晃動）
    forced_buffer = prev_close * 0.03
    buffer = max(actual_range * 0.4, forced_buffer)
    
    y_min = price_min - buffer
    y_max = price_max + buffer

    area = alt.Chart(df).mark_area(color=color, opacity=0.15).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M')),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[y_min, y_max]), axis=alt.Axis(title='價格'))
    )
    line = alt.Chart(df).mark_line(color=color, strokeWidth=3).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[y_min, y_max])),
        tooltip=['Time:T', 'Close:Q', 'Volume:Q']
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[6, 4], color='gray', opacity=0.8
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

# === 8. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption("✅ 系統連線正常\n👤 開發者：李宗念")

# === 9. 頂部 HUD ===
with st.container(border=True):
    col_title, col_date, col_idx = st.columns([2, 1, 2])
    
    with col_title:
        st.title("🏢 遠東集團戰情中心")
    
    with col_date:
        st.markdown(f"#### 📅 今日日期\n**{today_str}**")
    
    # 大盤
    idx_df = get_intraday_chart("^TWII")
    idx_metrics, _ = get_metrics("^TWII")  # 大盤用 yfinance（價格準）
    taiex_turnover = get_taiex_turnover()
    
    with col_idx:
        st.markdown("##### 🇹🇼 台灣加權指數")
        if idx_metrics:
            idx_color = '#d62728' if idx_metrics['change_amount'] > 0 else '#2ca02c'
            st.metric(
                "加權指數",
                f"{idx_metrics['current']:,.0f}",
                f"{idx_metrics['change_amount']:+.0f} ({idx_metrics['change_pct']:+.2f}%)",
                delta_color="inverse"
            )
            if taiex_turnover:
                st.metric("💎 大盤成交金額", f"{taiex_turnover:,.2f} 億")
            else:
                st.caption("大盤成交金額：暫無（非交易時段）")
            
            if not idx_df.empty:
                st.altair_chart(
                    draw_chart(idx_df, idx_color, idx_metrics['prev_close'], show_volume=False, height_price=100),
                    use_container_width=True
                )

# === 10. 集團總覽 ===
st.subheader("📋 遠東集團股票總覽")
all_data = []
idx_change_pct = idx_metrics['change_pct'] if idx_metrics else 0

for name, sym in stock_map.items():
    metrics, used_sina = get_metrics(sym, idx_change_pct)
    if metrics:
        metrics["股票"] = name
        metrics["來源"] = "Sina（精準）" if used_sina else "yfinance（備用）"
        all_data.append(metrics)

if all_data:
    df_all = pd.DataFrame(all_data)[["股票", "current", "change_amount", "change_pct", "avg_price", "volume_lots", "turnover_亿", "amplitude_pct", "vs_index"]]
    df_all.columns = ["股票", "股價", "漲跌", "漲跌%", "均價", "成交量(張)", "成交金額(億)", "振幅%", "較大盤"]
    df_all = df_all.sort_values("漲跌%", ascending=False)
    
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

# === 11. 個股詳細 ===
df_chart = get_intraday_chart(ticker)
metrics, used_sina = get_metrics(ticker, idx_change_pct)

if not metrics:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    chart_color = '#d62728' if metrics['change_amount'] > 0 else '#2ca02c'
    
    with st.container(border=True):
        st.markdown(f"#### 📊 {selected_name} 詳細數據 {'(Sina 精準來源)' if used_sina else '(yfinance 備用)'}")
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
    
    st.subheader("📈 今日即時走勢 (1分K) + 成交量")
    if not df_chart.empty:
        # 用 Sina 的 current 調整最後一點（盤後更準）
        df_chart['Close'] = df_chart['Close'].copy()
        df_chart.loc[df_chart.index[-1], 'Close'] = metrics['current']
        chart = draw_chart(df_chart, chart_color, metrics['prev_close'], show_volume=True)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("走勢圖暫無數據（yfinance 連線問題）")

# === 頁尾 ===
st.divider()
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: #888888; font-size: 0.9em;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    最後更新：{current_time} (數據每30秒自動更新)
</div>
""", unsafe_allow_html=True)
