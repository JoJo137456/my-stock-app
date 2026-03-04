    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

        /* 全局字體與背景 */
        .stApp {
            background-color: #F0F8FF !important;
            font-family: 'Inter', 'Noto Sans TC', system-ui, -apple-system, sans-serif !important;
        }

        /* 隱藏預設元素 */
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
       
        /* 左下角巨大圓弧色塊 */
        .stApp::before {
            content: '';
            position: fixed;
            bottom: -30vh;
            left: -15vw;
            width: 65vw;
            height: 65vw;
            background-color: #D6EAF8;
            border-radius: 50%;
            z-index: 0;
        }
        .main .block-container {
            z-index: 1;
            padding-top: 10vh !important;
        }

        /* 左側文字排版 */
        .hero-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            font-weight: 700;
            color: #1A1B20;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            letter-spacing: 1.2px;
        }
        .hero-subtitle::before {
            content: '';
            display: inline-block;
            width: 40px;
            height: 2px;
            background-color: #1A1B20;
            margin-right: 15px;
        }

        .hero-title-solid {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 80px;
            font-weight: 900;
            color: #1A1B20;
            line-height: 1.1;
            margin-bottom: 0;
            letter-spacing: -2.5px;
        }
       
        /* Far Eastern Group 改成實心文字 + 較柔和的深藍色 */
        .hero-title-outline {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 55px;
            font-weight: 800;
            color: #1E40AF;               /* 深藍色實心，不再是黑色描邊 */
            line-height: 1.2;
            margin-top: 5px;
            margin-bottom: 50px;
            letter-spacing: 0.5px;
        }
       
        .label-dashboard {
            background-color: #1A1B20;
            color: #ffffff;
            padding: 14px 32px;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 14px;
            display: inline-block;
            cursor: default;
            letter-spacing: 1.6px;
        }

        /* 右側白底登入卡片 */
        [data-testid="column"]:nth-of-type(3) {
            background: #ffffff;
            border-radius: 20px;
            padding: 40px 35px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.04);
            margin-top: 20px;
            border: 1px solid #E2E8F0;
        }
       
        .login-dept {
            font-family: 'Noto Sans TC', sans-serif;
            font-size: 28px;
            font-weight: 900;
            color: #1A1B20;
            letter-spacing: 1.2px;
            margin-bottom: 2px;
        }

        .login-title {
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            font-weight: 600;
            color: #64748B;
            margin-bottom: 30px;
        }

        .login-label {
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            font-weight: 600;
            color: #64748B;
            margin-bottom: 8px;
        }
       
        /* 輸入框 */
        div[data-baseweb="input"] > div {
            border: 1px solid #CBD5E1 !important;
            background-color: #ffffff !important;
            border-radius: 10px !important;
            height: 52px !important;
        }
        div[data-baseweb="input"] input {
            font-family: 'Inter', monospace;
            font-variant-numeric: tabular-nums;
            color: #0F172A !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        div[data-baseweb="input"]:focus-within > div {
            border-color: #1E40AF !important;
            box-shadow: 0 0 0 3px rgba(30,64,175,0.15) !important;
        }

        .terms-text {
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            color: #64748B;
            margin: 20px 0;
            font-weight: 500;
        }
        .terms-text a { color: #1E40AF; text-decoration: underline; }

        /* Login 按鈕改成深藍色主題 */
        button[kind="primary"] {
            background-color: #1E40AF !important;           /* 深藍主色 */
            color: white !important;
            border-radius: 10px !important;
            height: 52px !important;
            font-family: 'Inter', sans-serif;
            font-weight: 700 !important;
            font-size: 16px !important;
            letter-spacing: 0.6px;
            border: none !important;
        }
        button[kind="primary"]:hover {
            background-color: #1E3A8A !important;           /* hover 更深一點 */
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(30,64,175,0.25) !important;
        }
       
        .it-contact {
            font-family: 'Inter', sans-serif;
            margin-top: 25px;
            text-align: center;
            font-size: 12.5px;
            color: #64748B;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)
