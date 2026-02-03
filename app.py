import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

st.set_page_config(page_title="台灣股票當日走勢", layout="wide")
st.title("台灣股票當日走勢監控")

# 股票清單
stock_dict = {
    "遠東新 (1402)": "1402.TW",
    "亞泥 (1102)": "1102.TW",
    "裕民 (2606)": "2606.TW",
    "宏遠 (1460)": "1460.TW",
    "遠百 (2903)": "2903.TW",
    "遠傳 (4904)": "4904.TW",
    "東聯 (1710)": "1710.TW",
}

# 加權指數
index_ticker = "^TWII"

# 選擇股票
selected_stock_name = st.selectbox("選擇股票", list(stock_dict.keys()))
ticker = stock_dict[selected_stock_name]

# 快取資料，每 300 秒（5 分鐘）更新一次
@st.cache_data(ttl=300)
def get_intraday_data(symbol):
    ticker_obj = yf.Ticker(symbol)
    # 使用 5 分鐘 K 棒，period="1d" 只取當日資料
    df = ticker_obj.history(period="1d", interval="5m")
    return df

data = get_intraday_data(ticker)
index_data = get_intraday_data(index_ticker)

# 檢查是否有資料（非交易日會是空的）
if data.empty or index_data.empty:
    st.error("今日無交易資料（可能是假日、休市或資料尚未更新）")
    st.stop()

# ===== 左側：選定股票大圖 =====
fig_stock = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    subplot_titles=(f"{selected_stock_name} 當日走勢", "成交量"),
    row_heights=[0.7, 0.3]
)

# K 線
fig_stock.add_trace(
    go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name="K線",
        increasing_line_color="red",
        decreasing_line_color="green"
    ),
    row=1, col=1
)

# 成交量
fig_stock.add_trace(
    go.Bar(x=data.index, y=data["Volume"], name="成交量", marker_color="blue"),
    row=2, col=1
)

fig_stock.update_layout(
    xaxis_rangeslider_visible=False,
    height=700,
    title_text=f"{selected_stock_name} 當日走勢",
    showlegend=False
)

# ===== 右側：加權指數小圖 =====
fig_index = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.7, 0.3]
)

fig_index.add_trace(
    go.Candlestick(
        x=index_data.index,
        open=index_data["Open"],
        high=index_data["High"],
        low=index_data["Low"],
        close=index_data["Close"],
        name="加權指數",
        increasing_line_color="red",
        decreasing_line_color="green"
    ),
    row=1, col=1
)

fig_index.add_trace(
    go.Bar(x=index_data.index, y=index_data["Volume"], name="成交量", marker_color="gray"),
    row=2, col=1
)

fig_index.update_layout(
    height=500,
    title_text="台灣加權指數 (^TWII)",
    xaxis_rangeslider_visible=False,
    showlegend=False,
    margin=dict(l=20, r=20, t=50, b=20)
)

# ===== 版面配置 =====
col_left, col_right = st.columns([4, 1])

with col_left:
    st.plotly_chart(fig_stock, use_container_width=True)

    # 股票資訊
    latest = data.iloc[-1]
    open_price = data.iloc[0]["Open"]
    change = latest["Close"] - open_price
    change_pct = (change / open_price) * 100 if open_price != 0 else 0

    st.markdown(f"""
    ### {selected_stock_name}
    **最新價格**：{latest["Close"]:.2f}  
    **漲跌**：{change:+.2f} ({change_pct:+.2f}%)  
    **最高**：{data["High"].max():.2f}　**最低**：{data["Low"].min():.2f}  
    **成交量**：{int(latest["Volume"]):,}
    """)

with col_right:
    st.plotly_chart(fig_index, use_container_width=True)

    # 加權指數資訊
    idx_latest = index_data.iloc[-1]
    idx_open = index_data.iloc[0]["Open"]
    idx_change = idx_latest["Close"] - idx_open
    idx_change_pct = (idx_change / idx_open) * 100 if idx_open != 0 else 0

    st.markdown(f"""
    ### 加權指數
    **最新點數**  
    {idx_latest["Close"]:.2f}  
    
    **漲跌**  
    {idx_change:+.2f}  
    ({idx_change_pct:+.2f}%)
    """)

# 頁腳說明
st.caption(f"資料來源：Yahoo Finance（延遲報價）　更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
