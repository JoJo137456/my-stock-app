# =====================================
# 🔐 NEW CORPORATE LOGIN SYSTEM
# =====================================

def check_password():

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # 隱藏 sidebar/header
    st.markdown("""
    <style>
    [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display:none !important;}

    .login-wrapper {
        height: 100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        background: radial-gradient(circle at 30% 30%, #0f172a, #000000 70%);
    }

    .login-card {
        background: rgba(20, 25, 35, 0.85);
        backdrop-filter: blur(20px);
        padding: 60px 55px;
        border-radius: 20px;
        width: 420px;
        box-shadow:
            0 0 40px rgba(0,120,255,0.15),
            0 20px 60px rgba(0,0,0,0.8);
        border: 1px solid rgba(255,255,255,0.08);
    }

    .login-title {
        font-size: 38px;
        font-weight: 800;
        text-align:center;
        color:#ffffff;
        margin-bottom:10px;
        letter-spacing:2px;
    }

    .login-subtitle {
        text-align:center;
        color:#9ca3af;
        font-size:15px;
        margin-bottom:40px;
    }

    .footer-text {
        text-align:center;
        margin-top:35px;
        font-size:13px;
        color:#6b7280;
    }

    .footer-text a {
        color:#60a5fa;
        text-decoration:none;
    }

    .footer-text a:hover {
        text-decoration:underline;
    }

    div[data-baseweb="input"] input {
        background-color: rgba(255,255,255,0.05) !important;
        border-radius:10px !important;
        height:45px !important;
    }

    button[kind="primary"] {
        background: linear-gradient(90deg,#2563eb,#3b82f6) !important;
        border-radius:10px !important;
        height:50px !important;
        font-weight:600 !important;
    }

    button[kind="primary"]:hover {
        background: linear-gradient(90deg,#3b82f6,#60a5fa) !important;
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown('<div class="login-title">AUDIT HQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Far Eastern New Century — Secure Access</div>', unsafe_allow_html=True)

    with st.form("login_form"):

        st.text_input("Organization", value="Far Eastern New Century (FENC)", disabled=True)
        username = st.text_input("Account ID", value="Audit_HQ_Admin")
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if password == "AUDIT@01":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Access denied. Invalid credentials.")

    st.markdown("""
    <div class="footer-text">
        <a href="#">Forgot Password</a> •
        <a href="#">IT Support (ext. 6855)</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    return False


if not check_password():
    st.stop()
