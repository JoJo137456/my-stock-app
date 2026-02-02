import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 設定網頁標題
st.title('📈 我的專屬股價儀表板')

# 2. 側邊欄輸入股票代號
st.sidebar.header('設定參數')
ticker_symbol = st.sidebar.text_input("輸入股票代號 (例如 2330.TW, 1587.TW)", "2330.TW")

# 3. 抓取數據 (使用 yfinance)
@st.cache_data # 快取數據，避免重複下載浪費時間
def get_data(symbol):
    stock = yf.Ticker(symbol)
    # 抓取歷史數據
    history = stock.history(period="1y")
    return history, stock.info

try:
    df, info = get_data(ticker_symbol)
    
    # 4. 顯示基本資訊
    st.subheader(f"{info.get('longName', ticker_symbol)} - 股價走勢")
    st.metric("目前股價", f"{info.get('currentPrice', 'N/A')} TWD")

    # 5. 畫出股價圖 (Line Chart)
    st.line_chart(df['Close'])

    # 6. 顯示數據表格
    if st.checkbox('顯示詳細數據'):
        st.write(df)

except Exception as e:
    st.error(f"找不到股票代號或發生錯誤: {e}")

# 提示：在終端機輸入 `streamlit run app.py` 來啟動網頁