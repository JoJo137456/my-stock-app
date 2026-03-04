# 載入大樓背景圖
    if os.path.exists('bg.jpg'):
        with open('bg.jpg', 'rb') as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        bg_css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)
        
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
            
            /* 1. 終極覆寫：強制的深灰色實體底框，完全遮蔽大樓背景 */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #595959 !important; /* 參考圖的深灰色 */
                border: none !important;
                border-radius: 5px !important;
                box-shadow: 0px 5px 20px rgba(0, 0, 0, 0.8) !important;
                padding: 40px 50px !important;
            }
            
            /* 2. 終極覆寫：輸入框強制為純白底、無邊框 */
            div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
                background-color: #ffffff !important;
                border: none !important;
                border-radius: 4px !important;
            }
            
            /* 3. 終極覆寫：輸入框內的文字強制為純黑粗體 */
            input, select, div[data-baseweb="select"] span { 
                color: #000000 !important; 
                font-size: 1.1rem !important;
                font-weight: bold !important;
                -webkit-text-fill-color: #000000 !important; 
            }
            
            /* 4. 終極覆寫：Log in 按鈕強制為黃色底、黑字 */
            button[kind="primary"] {
                background-color: #FFC107 !important; /* 參考圖的黃色 */
                color: #000000 !important;
                font-weight: 800 !important;
                font-size: 1.3rem !important;
                border: none !important;
                border-radius: 4px !important;
                padding: 10px !important;
            }
            button[kind="primary"]:hover {
                background-color: #E0A800 !important;
            }
        </style>
        """, unsafe_allow_html=True)
