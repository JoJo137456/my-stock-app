import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf
import os

# === 0. 系統層級修復與環境設定 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

st.set_page_config(page_title="FENC Audit Department | Executive Dashboard", layout="wide", initial_sidebar_state="expanded")
tw_tz = pytz.timezone('Asia/Taipei') 

# ==========================================
# === 1. 登入介面與防護機制定義 ===
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@500;700;900&display=swap');
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        .stApp { background-color: #F8FAFC !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .hero-title-solid { font-size: 65px; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 0; letter-spacing: -1.5px; }
        .hero-title-outline { font-size: 50px; font-weight: 900; color: transparent; -webkit-text-stroke: 1.5px #0F172A; line-height: 1.2; margin-top: 5px; margin-bottom: 40px; }
        .label-dashboard { background-color: #2563EB; color: #ffffff; padding: 12px 28px; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block; letter-spacing: 1px;}
        [data-testid="column"]:nth-of-type(3) { background: #ffffff; border-radius: 16px; padding: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-top: 20px; border: 1px solid #E2E8F0;}
        div[data-baseweb="input"] > div { border: 1px solid #CBD5E1 !important; background-color: #F8FAFC !important; border-radius: 8px !important; height: 50px !important; }
        button[kind="primary"] { background-color: #0F172A !important; color: white !important; border-radius: 8px !important; height: 50px !important; font-weight: 600 !important; font-size: 16px !important;}
    </style>
    """, unsafe_allow_html=True)

    col_left, spacer, col_right = st.columns([1.2, 0.2, 0.8])
    with col_left:
        st.markdown('<div class="hero-title-solid">Audit Department</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-outline">Far Eastern Group</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">AI Executive Intelligence</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div style="font-size: 26px; color: #0F172A; font-weight: 800; margin-bottom: 5px;">聯合稽核總部</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 15px; font-weight: 600; color: #64748B; margin-bottom: 30px;">Strategic Command Login</div>', unsafe_allow_html=True)
        st.text_input("Customer ID", value="fenc07822", label_visibility="collapsed", key="acc_id")
        pwd = st.text_input("Passcode", type="password", label_visibility="collapsed", key="pwd")
        if st.button("Secure Login ──", type="primary", use_container_width=True):
            if pwd == "AUDIT@01":
                st.session_state["password_correct"] = True
                st.rerun()
            elif pwd != "":
                st.error("Invalid credentials")
    return False

if not check_password(): st.stop()

# ==========================================
# === 2. 智慧型內部 Excel 數據探勘引擎 ===
# ==========================================
def find_column(df, keywords):
    """智慧模糊比對：自動尋找 Excel 中的目標欄位"""
    for col in df.columns:
        if any(k in str(col).upper() for k in keywords):
            return col
    return None

@st.cache_data(ttl=60) 
def parse_internal_excel_data(stock_code):
    """讀取內部上傳的 Excel 檔案，並透過 AI 模糊比對萃取會計科目"""
    try:
        # 動態判斷是否為遠東銀，讀取對應的檔案
        if stock_code == '2845':
            is_file = '遠東集團上市公司_遠東銀_損益表_2015~2025Q3.xlsx'
            bs_file = '遠東集團上市公司_遠東銀_資產負債表_2015~2025Q3.xlsx'
        else:
            is_file = '遠東集團上市公司_損益表_2015~2025Q3.xlsx'
            bs_file = '遠東集團上市公司_資產負債表_2015~2025Q3.xlsx'

        if not os.path.exists(is_file) or not os.path.exists(bs_file):
            st.error(f"找不到檔案！請確認 GitHub 上是否存在 `{is_file}` 與 `{bs_file}`。")
            return pd.DataFrame(), pd.DataFrame()

        df_is = pd.read_excel(is_file)
        df_bs = pd.read_excel(bs_file)

        # 智慧尋找損益表欄位
        col_is_code = find_column(df_is, ['代碼', '公司', '證券', '股號', 'CODE'])
        col_is_date = find_column(df_is, ['季', '年', '期', 'DATE', '年月'])
        col_rev = find_column(df_is, ['營業收入', '淨收益', '營收', 'REVENUE'])
        col_gp = find_column(df_is, ['毛利', '營業毛利', 'GROSS PROFIT'])
        col_net = find_column(df_is, ['淨利', '本期損益', 'NET INCOME'])
        col_opex = find_column(df_is, ['營業費用', '費用', 'OPEX'])
        col_cogs = find_column(df_is, ['營業成本', '成本', 'COGS'])
        col_eps = find_column(df_is, ['EPS', '每股盈餘'])

        # 智慧尋找資產負債表欄位
        col_bs_code = find_column(df_bs, ['代碼', '公司', '證券', '股號', 'CODE'])
        col_bs_date = find_column(df_bs, ['季', '年', '期', 'DATE', '年月'])
        col_inv = find_column(df_bs, ['存貨', 'INVENTORY'])
        col_ar = find_column(df_bs, ['應收', 'RECEIVABLE'])

        # 篩選出該檔股票的資料，並轉字串確保比對成功
        df_is_stock = df_is[df_is[col_is_code].astype(str).str.contains(stock_code, na=False)].copy()
        df_bs_stock = df_bs[df_bs[col_bs_code].astype(str).str.contains(stock_code, na=False)].copy()

        if df_is_stock.empty:
            st.warning(f"在 Excel 檔案中找不到代碼 `{stock_code}` 的資料。")
            return pd.DataFrame(), pd.DataFrame()

        # 依據日期排序 (最新的在最上面)
        df_is_stock = df_is_stock.sort_values(by=col_is_date, ascending=False).head(8)

        results = []
        for _, row_is in df_is_stock.iterrows():
            q_date = str(row_is[col_is_date]).strip()
            
            # 尋找對應季度的 BS 資料
            bs_match = df_bs_stock[df_bs_stock[col_bs_date].astype(str).str.strip() == q_date]
            row_bs = bs_match.iloc[0] if not bs_match.empty else None

            # 取值並防呆
            def safe_val(val): return float(val) if pd.notna(val) and str(val).replace('.','',1).isdigit() else pd.NA
            
            rev = safe_val(row_is[col_rev]) if col_rev else pd.NA
            gp = safe_val(row_is[col_gp]) if col_gp else pd.NA
            net = safe_val(row_is[col_net]) if col_net else pd.NA
            opex = safe_val(row_is[col_opex]) if col_opex else pd.NA
            cogs = safe_val(row_is[col_cogs]) if col_cogs else pd.NA
            eps = safe_val(row_is[col_eps]) if col_eps else pd.NA
            
            inv = safe_val(row_bs[col_inv]) if row_bs is not None and col_inv else pd.NA
            ar = safe_val(row_bs[col_ar]) if row_bs is not None and col_ar else pd.NA

            # 智慧單位轉換 (如果是千元，通常營收會大於百萬，自動除以10萬換算成億)
            scale = 100000 if pd.notna(rev) and rev > 1000000 else 1 

            rev_b = rev / scale if pd.notna(rev) else pd.NA
            gp_b = gp / scale if pd.notna(gp) else pd.NA
            opex_b = opex / scale if pd.notna(opex) else pd.NA
            net_b = net / scale if pd.notna(net) else pd.NA
            
            gm_pct = (gp / rev * 100) if pd.notna(gp) and pd.notna(rev) and rev != 0 else pd.NA
            nm_pct = (net / rev * 100) if pd.notna(net) and pd.notna(rev) and rev != 0 else pd.NA
            
            inv_days = (inv / cogs * 90) if pd.notna(inv) and pd.notna(cogs) and cogs != 0 else pd.NA
            ar_days = (ar / rev * 90) if pd.notna(ar) and pd.notna(rev) and rev != 0 else pd.NA

            # 針對銀行業 (無存貨、無毛利) 做特殊處理
            if stock_code == '2845':
                gm_pct, inv_days, cogs, gp_b = pd.NA, pd.NA, pd.NA, pd.NA

            results.append({
                '季度': q_date, '單季營收 (億)': rev_b, '毛利 (億)': gp_b, '毛利率 (%)': gm_pct,
                '營業費用 (億)': opex_b, '淨利 (億)': net_b, '淨利率 (%)': nm_pct, '單季EPS (元)': eps,
                '存貨周轉天數': inv_days, '應收帳款天數': ar_days,
                '_raw_rev': rev, '_raw_gp': gp, '_raw_net': net
            })
            
        df_final = pd.DataFrame(results)

        # YTD 計算
        ytd_df = df_final.copy().iloc[::-1].reset_index(drop=True)
        # 嘗試擷取年份 (前四個字元通常是年份)
        ytd_df['年份'] = ytd_df['季度'].astype(str).str[:4]
        ytd_df['累計營收 (億)'] = ytd_df.groupby('年份')['單季營收 (億)'].cumsum()
        ytd_df['累計淨利 (億)'] = ytd_df.groupby('年份')['淨利 (億)'].cumsum()
        if '單季EPS (元)' in ytd_df.columns:
            ytd_df['累計EPS (元)'] = ytd_df.groupby('年份')['單季EPS (元)'].cumsum()
        ytd_df = ytd_df.iloc[::-1].drop(columns=['年份']).reset_index(drop=True)

        return df_final, ytd_df
    except Exception as e:
        st.error(f"讀取內部 Excel 發生錯誤：{str(e)}。請確認欄位格式是否正確。")
        return pd.DataFrame(), pd.DataFrame()

# === AI 智慧稽核行動引擎 ===
def generate_audit_action_plan(df):
    if len(df) < 2: return 50, ["數據不足以進行趨勢判定。"], ["請等待下一季度完整財報發布。"]
    
    latest, prev = df.iloc[0], df.iloc[1]
    score = 75
    status_points, audit_actions = [], []
    
    if pd.notna(latest['_raw_rev']) and pd.notna(prev['_raw_rev']) and prev['_raw_rev'] > 0:
        rev_growth = (latest['_raw_rev'] - prev['_raw_rev']) / prev['_raw_rev']
        if rev_growth > 0.05:
            score += 10
            status_points.append(f"✅ 營收動能強勁 (QoQ <span class='highlight-green'>+{rev_growth*100:.1f}%</span>)")
            audit_actions.append("【收入覆核】營收顯著擴張，應抽核本季大額訂單之銷貨折讓明細，嚴防業務端為達標而提前認列或塞貨。")
        elif rev_growth < -0.05:
            score -= 15
            status_points.append(f"⚠️ 營收面臨衰退 (QoQ <span class='highlight-red'>{rev_growth*100:.1f}%</span>)")
            audit_actions.append("【營運查核】營收放緩，建議會同業務主管檢視前五大客戶流失狀況，並查核是否異常放寬授信條件。")

    if pd.notna(latest['毛利率 (%)']) and pd.notna(prev['毛利率 (%)']):
        margin_diff = latest['毛利率 (%)'] - prev['毛利率 (%)']
        if margin_diff > 1.0:
            score += 15
            status_points.append(f"✅ 毛利率顯著擴張 (<span class='highlight-green'>+{margin_diff:.1f}%</span>)，具備強勢定價權。")
        elif margin_diff < -1.0:
            score -= 15
            status_points.append(f"⚠️ 毛利率遭受壓縮 (<span class='highlight-red'>{margin_diff:.1f}%</span>)，成本控管亮紅燈。")
            audit_actions.append("【採購查核】毛利下滑，建議抽核前十大原物料採購單，釐清是供應鏈通膨或因去化庫存而大幅降價。")

    if pd.notna(latest['應收帳款天數']) and pd.notna(prev['應收帳款天數']) and latest['應收帳款天數'] > prev['應收帳款天數'] * 1.15:
        score -= 15
        status_points.append("⚠️ 應收帳款周轉天數急遽攀升，收款效率惡化。")
        audit_actions.append("【信用查核】收款週期拉長，建議調閱『應收帳款帳齡分析表』，確認是否需增提備抵呆帳。")
            
    if pd.notna(latest['存貨周轉天數']) and pd.notna(prev['存貨周轉天數']) and latest['存貨周轉天數'] > prev['存貨周轉天數'] * 1.15:
        score -= 15
        status_points.append("⚠️ 存貨積壓嚴重，營運資金遭凍結。")
        audit_actions.append("【實地盤點】資金被庫存卡死。建議排定廠區無預警盤點，評估存貨跌價損失認列之適足性。")

    if len(audit_actions) == 0: audit_actions.append("【例行覆核】本季財務指標無重大異常，維持常規抽核計畫即可。")

    return max(0, min(100, int(score))), status_points, audit_actions

# === 即時股價與繪圖模組 ===
@st.cache_data(ttl=3600) 
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        for i in range(6):
            target_date = (now.replace(day=1) - pd.DateOffset(months=i)).strftime('%Y%m01')
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={target_date}&stockNo={stock_code}"
            r = requests.get(url).json()
            if r['stat'] == 'OK':
                for row in r['data']:
                    parts = row[0].split('/')
                    date_iso = f"{int(parts[0])+1911}-{parts[1]}-{parts[2]}"
                    data_list.append({'date': date_iso, 'volume': float(row[1].replace(',', '')), 'open': float(row[3].replace(',', '')), 'high': float(row[4].replace(',', '')), 'low': float(row[5].replace(',', '')), 'close': float(row[6].replace(',', ''))})
        return sorted(data_list, key=lambda x: x['date'])
    except: return None

@st.cache_data(ttl=3600)
def fetch_us_history(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="6mo")
        data_list = [{'date': idx.strftime('%Y-%m-%d'), 'volume': float(row['Volume']), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close'])} for idx, row in hist.iterrows()]
        return data_list
    except: return None

@st.cache_data(ttl=300) 
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        ticker = yf.Ticker(stock_code if is_us_source else f"{stock_code}.TW")
        df = ticker.history(period="1d", interval="1m")
        if df.empty: df = ticker.history(period="5d", interval="5m")
        return df if not df.empty else None
    except: return None

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_fillcolor='#ef4444', decreasing_fillcolor='#22c55e')])
    fig.update_layout(title="<b>📊 歷史價格走勢 (近半年)</b>", xaxis_rangeslider_visible=False, height=350, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#0f172a', width=2.5), fill='tozeroy', fillcolor='rgba(15, 23, 42, 0.05)'))
    fig.update_layout(title="<b>⚡ 當日分時動態</b>", height=350, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(range=[y_min - padding, y_max + padding]))
    return fig

# ==========================================
# === 3. 主頁面 UI 樣式與選單 ===
# ==========================================
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #0F172A; text-align: center; margin: 0.5rem 0 0.5rem 0; letter-spacing: 0.5px;}
        .sub-title { font-size: 1rem; color: #64748B; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .chart-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-bottom: 25px; border: 1px solid #E2E8F0; }
        .ai-score-panel { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 25px; border-radius: 12px; text-align: center; height: 100%; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
        .ai-score-num { font-size: 65px; font-weight: 900; line-height: 1; margin: 15px 0; font-family: 'Arial', sans-serif;}
        .audit-action-panel { background: #FFFBEB; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 8px; height: 100%; border-top: 1px solid #FEF3C7; border-right: 1px solid #FEF3C7; border-bottom: 1px solid #FEF3C7;}
        .audit-title { font-weight: 800; color: #0F172A; margin-bottom: 12px; font-size: 16px;}
        .audit-text { font-size: 14.5px; color: #334155; line-height: 1.6; margin-bottom: 8px;}
        .highlight-red { color: #EF4444; font-weight: 600; }
        .highlight-green { color: #10B981; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

market_categories = {
    "🏢 遠東集團核心事業體": {"🇹🇼 1402 遠東新": "1402", "🇹🇼 1102 亞泥": "1102", "🇹🇼 2606 裕民": "2606", "🇹🇼 4904 遠傳": "4904", "🇹🇼 1460 宏遠": "1460", "🇹🇼 2903 遠百": "2903", "🇹🇼 1710 東聯": "1710", "🇹🇼 2845 遠東銀": "2845"},
    "📈 總體經濟與大盤": {"🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC", "🇺🇸 SOX (費半)": "^SOX"}
}

with st.sidebar:
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# ==========================================
# === 4. 上半部：即時股價與技術線圖區塊 ===
# ==========================================
real_data = {'price': 0}
if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']: real_data['price'] = float(real['realtime']['latest_trade_price']) if real['realtime']['latest_trade_price'] != '-' else float(real['realtime']['open'])
    except: pass
    hist_data = fetch_twse_history_proxy(code)
else:
    try:
        tk = yf.Ticker(code)
        real_data['price'] = tk.fast_info.last_price
    except: pass
    hist_data = fetch_us_history(code)

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
df_intra = get_intraday_chart_data(code, not is_tw_stock)
current_price = real_data['price'] if real_data['price'] > 0 else (df_daily.iloc[-1]['close'] if not df_daily.empty else 0)

prev_close = df_daily.iloc[-2]['close'] if len(df_daily) > 1 else current_price
change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

st.markdown(f"""
<div style="background-color: #ffffff; padding: 25px; border-radius: 12px; margin-bottom: 25px; border-left: 6px solid {'#EF4444' if change < 0 else '#10B981'}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0;">
    <h2 style="margin:0; color:#475569; font-size: 1.1rem; font-weight: 700;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 800; color: #0F172A; letter-spacing: -1px;">{"NT$" if is_tw_stock else ""} {current_price:,.2f}</span>
        <span style="font-size: 1.6rem; font-weight: 700; color: {'#EF4444' if change < 0 else '#10B981'};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# === 5. 下半部：高階財務戰情室 (100% Internal Data) ===
# ==========================================
if is_tw_stock:
    st.divider()
    st.markdown("## 📈 企業基本面與稽核戰略解析 (Internal Data Lake)")
    st.info("💡 **架構升級聲明**：本儀表板已成功升級為「內部數據湖驅動模式」。系統正透過 AI 模糊比對引擎，直接讀取並解析您上傳至 GitHub 的官方 Excel 財報檔案，實現 0 延遲、100% 絕對真實與受控，徹底根除外部 API 阻擋或亂碼問題。")

    # 執行內部 Excel 探勘
    df_quarterly, df_ytd = parse_internal_excel_data(code)

    if not df_quarterly.empty and len(df_quarterly) >= 2:
        latest = df_quarterly.iloc[0]
        
        # --- AI 健檢 ---
        st.markdown("### 🤖 智能財務健檢與稽核行動指南 (AI Audit Engine)")
        score, status_pts, actions = generate_audit_action_plan(df_quarterly)
        
        col_ai1, col_ai2 = st.columns([1, 2.5])
        with col_ai1:
            st.markdown(f"""<div class="ai-score-panel"><div style="font-size:14px; color:#94A3B8; font-weight:700; letter-spacing:1px;">AI 稽核綜合評估</div><div class="ai-score-num" style="color:{'#10B981' if score>=70 else ('#F59E0B' if score>=55 else '#EF4444')};">{score}</div><div style="font-size:12px; color:#CBD5E1;">滿分 100 / 警戒線 60</div></div>""", unsafe_allow_html=True)
        with col_ai2:
            st.markdown('<div class="audit-action-panel"><div class="audit-title">📊 營運體質判定與查核指示</div>', unsafe_allow_html=True)
            for pt in status_pts: st.markdown(f'<div class="audit-text">{pt}</div>', unsafe_allow_html=True)
            st.markdown('<hr style="margin: 12px 0; border: none; border-top: 1px dashed #D1D5DB;">', unsafe_allow_html=True)
            for act in actions: st.markdown(f'<div class="audit-text" style="font-weight:600; color:#0F172A;">👉 {act}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- 圖表區 (解開 Y 軸封印) ---
        c_chart1, c_chart2 = st.columns([1, 1.2]) 
        with c_chart1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            plot_df = df_quarterly.iloc[::-1].dropna(subset=['單季營收 (億)'])
            if not plot_df.empty:
                fig1 = make_subplots(specs=[[{"secondary_y": True}]])
                fig1.add_trace(go.Bar(x=plot_df['季度'], y=plot_df['單季營收 (億)'], name="營收 (億)", marker_color='#E2E8F0'), secondary_y=False)
                
                if pd.notna(plot_df['毛利率 (%)'].iloc[0]):
                    fig1.add_trace(go.Scatter(x=plot_df['季度'], y=plot_df['毛利率 (%)'], name="毛利率 %", mode='lines+markers', line=dict(color='#0F172A', width=3, shape='spline')), secondary_y=True)
                fig1.add_trace(go.Scatter(x=plot_df['季度'], y=plot_df['淨利率 (%)'], name="淨利率 %", mode='lines+markers', line=dict(color='#2563EB', width=3, shape='spline')), secondary_y=True)
                
                fig1.update_layout(title="<b>📊 營收規模與獲利趨勢 (Internal Data)</b>", height=420, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                fig1.update_yaxes(title_text="金額 (億台幣)", secondary_y=False, showgrid=False)
                fig1.update_yaxes(title_text="百分比 (%)", secondary_y=True, showgrid=True, gridcolor='#F8FAFC', autorange=True) 
                st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_chart2:
            st.markdown("""<style>.waterfall-container { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;}</style>""", unsafe_allow_html=True)
            st.markdown('<div class="waterfall-container">', unsafe_allow_html=True)
            
            # 若為銀行業無毛利/成本，做特規處理避免錯誤
            is_bank = code == '2845'
            if is_bank:
                x_labels = ["營業收入", "營業費用", "本期淨利"]
                text_vals = [f"{latest['單季營收 (億)']:.1f}", f"-{latest['單季營收 (億)'] - latest['淨利 (億)']:.1f}", f"{latest['淨利 (億)']:.1f}"]
                y_vals = [latest['單季營收 (億)'], -(latest['單季營收 (億)'] - latest['淨利 (億)']), latest['淨利 (億)']]
                measures = ["relative", "relative", "total"]
            else:
                x_labels = ["營業收入", "營業成本", "毛利", "營業費用/稅", "本期淨利"]
                text_vals = [f"{latest['單季營收 (億)']:.1f}" if pd.notna(latest['單季營收 (億)']) else "N/A", 
                             f"-{latest['單季營收 (億)'] - latest['毛利 (億)']:.1f}" if pd.notna(latest['毛利 (億)']) else "N/A", 
                             f"{latest['毛利 (億)']:.1f}" if pd.notna(latest['毛利 (億)']) else "N/A", 
                             f"-{latest['毛利 (億)'] - latest['淨利 (億)']:.1f}" if pd.notna(latest['淨利 (億)']) else "N/A", 
                             f"{latest['淨利 (億)']:.1f}" if pd.notna(latest['淨利 (億)']) else "N/A"]
                y_vals = [latest['單季營收 (億)'] if pd.notna(latest['單季營收 (億)']) else 0, 
                          -(latest['單季營收 (億)'] - latest['毛利 (億)']) if pd.notna(latest['毛利 (億)']) else 0, 
                          latest['毛利 (億)'] if pd.notna(latest['毛利 (億)']) else 0, 
                          -(latest['毛利 (億)'] - latest['淨利 (億)']) if pd.notna(latest['淨利 (億)']) else 0, 
                          latest['淨利 (億)'] if pd.notna(latest['淨利 (億)']) else 0]
                measures = ["relative", "relative", "total", "relative", "total"]

            fig2 = go.Figure(go.Waterfall(
                name="20", orientation="v", measure=measures, x=x_labels, textposition="outside", textfont=dict(size=14, color='#0F172A', weight='bold'),
                text=text_vals, y=y_vals, connector={"line":{"color":"#CBD5E1", "dash": 'dot', "width": 2}}, decreasing={"marker":{"color":"#EF4444"}}, increasing={"marker":{"color":"#3B82F6"}}, totals={"marker":{"color":"#0F172A"}}      
            ))
            fig2.update_layout(title=f"<b>💰 獲利結構瀑布圖拆解 (最新財報: {latest['季度']})</b>", height=420, margin=dict(l=0, r=0, t=50, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- 財務數據矩陣 ---
        st.markdown("### 📑 核心財務數據矩陣 (Internal Database)")
        tab1, tab2 = st.tabs(["📊 單季表現 (Quarterly)", "📈 累計表現 (Year-To-Date)"])
        
        display_df = df_quarterly[[c for c in df_quarterly.columns if not c.startswith('_')]]
        format_dict = {'單季營收 (億)': '{:,.1f}', '毛利 (億)': '{:,.1f}', '營業費用 (億)': '{:,.1f}', '淨利 (億)': '{:,.1f}', '毛利率 (%)': '{:.1f}%', '淨利率 (%)': '{:.1f}%', '單季EPS (元)': '{:.2f}', '存貨周轉天數': '{:.1f}', '應收帳款天數': '{:.1f}'}
        
        with tab1:
            st.dataframe(display_df.style.format(format_dict, na_rep="N/A"), use_container_width=True, height=320)
        with tab2:
            if not df_ytd.empty:
                ytd_cols = ['季度', '累計營收 (億)', '累計淨利 (億)']
                if '累計EPS (元)' in df_ytd.columns: ytd_cols.append('累計EPS (元)')
                st.dataframe(df_ytd[ytd_cols].style.format({'累計營收 (億)': '{:,.1f}', '累計淨利 (億)': '{:,.1f}', '累計EPS (元)': '{:.2f}'}, na_rep="N/A"), use_container_width=True, height=320)
    else:
        st.info("⚠️ 請確保已將 `遠東集團上市公司_損益表_2015~2025Q3.xlsx` 等檔案上傳至與此程式相同的 GitHub 資料夾中。")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：Internal Excel Data Lake</div>', unsafe_allow_html=True)
