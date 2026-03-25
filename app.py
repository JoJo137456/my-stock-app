# === 8. 財務健檢與同業對標分析（已改為動態外部競爭對手） ===
if is_tw_stock:
    st.divider()
    fin_df = st.session_state.get('fin_data', None)
 
    if fin_df is not None and not fin_df.empty:
        # === 動態取得外部競爭對手 ===
        peer_codes = external_peers.get(str(code), [])
        all_ids = [str(code)] + peer_codes
        # 建立顯示用的peer_dict
        peer_dict = {pid: company_name_dict.get(pid, pid) for pid in all_ids}
 
        latest_data = {}
        data_date_str = "最新期數"
        for pid in all_ids:
            c_df = fin_df[fin_df['stock_id'] == pid].sort_values('date', ascending=False)
            if not c_df.empty:
                latest_data[pid] = c_df.iloc[0]
 
        if str(code) in latest_data:
            latest_date_val = latest_data[str(code)].get('date')
            if pd.notna(latest_date_val):
                data_date_str = latest_date_val.strftime('%Y-%m')
 
        st.markdown(f"## 📊 財務健檢與同業對標分析 <span style='font-size: 1rem; color: #64748b; font-weight: 500;'>（資料期數：{data_date_str}）</span>", unsafe_allow_html=True)
        current_company_name = peer_dict.get(str(code), f"公司 {code}")
        st.markdown(f"### 🔍 目前分析主體：**{current_company_name} ({code})**")
 
        # 指標定義（不變）
        indicators_dict = {
            'inv_ar_to_equity': {'name': '存貨及應收帳款/淨值', 'better': 'lower'},
            'ar_turnover_times': {'name': '應收帳款週轉次數', 'better': 'higher'},
            'total_assets_turnover': {'name': '總資產週轉次數', 'better': 'higher'},
            'ar_days': {'name': '平均收帳天數', 'better': 'lower'},
            'inv_turnover_times': {'name': '存貨週轉率', 'better': 'higher'},
            'inv_days': {'name': '平均售貨天數', 'better': 'lower'},
            'fixed_assets_turnover': {'name': '固定資產週轉次數', 'better': 'higher'},
            'equity_turnover': {'name': '淨值週轉率', 'better': 'higher'},
            'ap_days': {'name': '應付帳款付現天數', 'better': 'lower'},
            'net_operating_cycle': {'name': '淨營業週期', 'better': 'lower'}
        }
 
        # 計算業界平均（只含有資料的peer）
        industry_avg = {}
        for key in indicators_dict.keys():
            vals = [latest_data[pid].get(key) for pid in latest_data if pd.notna(latest_data[pid].get(key))]
            industry_avg[key] = np.mean(vals) if vals else np.nan
 
        # 計算綜合評分
        scores = {}
        for pid, data in latest_data.items():
            score = 0
            for key, info in indicators_dict.items():
                val = data.get(key)
                avg = industry_avg.get(key)
                if pd.notna(val) and pd.notna(avg):
                    if info['better'] == 'higher' and val >= avg:
                        score += 10
                    elif info['better'] == 'lower' and val <= avg:
                        score += 10
            scores[pid] = score
 
        # --- 區塊 1：綜合評分看板 ---
        st.markdown("#### 🏆 經營能力綜合評分比較 (滿分 100 分)")
        cols = st.columns(len(latest_data))
        for i, (pid, score) in enumerate(scores.items()):
            comp_name = peer_dict.get(pid, pid)
            is_current = (pid == str(code))
            highlight_class = "highlight-card" if is_current else ""
            color = "#22c55e" if score >= 60 else "#ef4444"
            with cols[i]:
                st.markdown(f"""
                <div class="score-card {highlight_class}">
                    <div class="score-card-title">{comp_name} ({pid})</div>
                    <div class="score-card-value" style="color: {color};">{score}</div>
                </div>
                """, unsafe_allow_html=True)
 
        st.markdown("<br>", unsafe_allow_html=True)
 
        # --- 區塊 2：數據表 ---
        st.markdown("#### 📝 最新關鍵指標明細 (原始數據)")
        table_data = {"指標": [info['name'] for info in indicators_dict.values()]}
        for pid in all_ids:
            if pid in latest_data:
                c_data = latest_data[pid]
                col_name = f"{peer_dict[pid]} ({pid})"
                table_data[col_name] = [
                    round(c_data.get(k, np.nan), 2) if pd.notna(c_data.get(k)) else "-"
                    for k in indicators_dict.keys()
                ]
        metrics_df = pd.DataFrame(table_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
 
        # --- 區塊 3：X-Y 軸矩陣 ---
        st.markdown("#### 🎯 營運雙核心矩陣 (存貨週轉率 vs 應收帳款週轉次數)")
        x_metric = 'inv_turnover_times'
        y_metric = 'ar_turnover_times'
        fig_xy = go.Figure()
        for pid in all_ids:
            if pid in latest_data:
                data = latest_data[pid]
                x_val = data.get(x_metric, np.nan)
                y_val = data.get(y_metric, np.nan)
                if pd.notna(x_val) and pd.notna(y_val):
                    is_target = (pid == str(code))
                    fig_xy.add_trace(go.Scatter(
                        x=[x_val], y=[y_val],
                        mode='markers+text',
                        name=peer_dict[pid],
                        text=[peer_dict[pid]],
                        textposition="top center",
                        textfont=dict(size=14, color="#1e293b" if not is_target else "#ef4444", weight="bold" if is_target else "normal"),
                        marker=dict(size=24 if is_target else 18, color='#ef4444' if is_target else '#94a3b8', line=dict(width=2, color='white'), opacity=0.9),
                        hovertemplate=f"<b>{peer_dict[pid]}</b><br>存貨週轉率: %{{x:.2f}}<br>應收帳款週轉: %{{y:.2f}}<extra></extra>"
                    ))
        fig_xy.update_layout(height=500, plot_bgcolor='#f8fafc', paper_bgcolor='#ffffff', margin=dict(l=40,r=40,t=40,b=40),
                              xaxis=dict(title="存貨週轉率 (次) ➔ 越高越好", gridcolor="white", zerolinecolor="#cbd5e1", zerolinewidth=2),
                              yaxis=dict(title="應收帳款週轉次數 (次) ➔ 越高越好", gridcolor="white", zerolinecolor="#cbd5e1", zerolinewidth=2),
                              showlegend=False)
        st.plotly_chart(fig_xy, use_container_width=True)
        st.caption("右上角象限代表「存貨去化快」且「帳款回收快」，為最佳營運狀態。")
 
        # --- 區塊 4：8季趨勢圖 ---
        st.markdown("#### 📈 歷年營運效率趨勢對標 (近 8 季)")
        trend_metric = st.selectbox("請選擇要深入剖析的戰略指標", options=list(indicators_dict.keys()), format_func=lambda x: indicators_dict[x]['name'], index=4)
 
        fenc_df = fin_df[fin_df['stock_id'] == str(code)].sort_values('date', ascending=True).dropna(subset=['date', trend_metric])
        fenc_df['pct_change'] = fenc_df[trend_metric].pct_change() * 100
 
        peer_df = fin_df[fin_df['stock_id'].isin(peer_codes)].dropna(subset=['date', trend_metric])
        peer_avg_df = peer_df.groupby('date')[trend_metric].mean().reset_index().rename(columns={trend_metric: 'peer_avg'})
 
        merged_df = pd.merge(fenc_df[['date', trend_metric, 'pct_change']], peer_avg_df, on='date', how='inner').tail(8)
 
        if not merged_df.empty:
            x_labels = merged_df['date'].dt.strftime('%Y-%m')
            text_annotations = []
            for _, row in merged_df.iterrows():
                val = row[trend_metric]
                pct = row['pct_change']
                if pd.isna(pct):
                    text_annotations.append(f"{val:.2f}")
                elif pct > 0:
                    text_annotations.append(f"{val:.2f}<br>▲ {pct:.1f}%")
                elif pct < 0:
                    text_annotations.append(f"{val:.2f}<br>▼ {abs(pct):.1f}%")
                else:
                    text_annotations.append(f"{val:.2f}<br>持平")
 
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(x=x_labels, y=merged_df[trend_metric], name=current_company_name, marker_color='#ef4444', text=text_annotations, textposition='outside'))
            fig_trend.add_trace(go.Bar(x=x_labels, y=merged_df['peer_avg'], name='外部同業平均', marker_color='#cbd5e1', text=[f"{v:.2f}" for v in merged_df['peer_avg']], textposition='outside'))
            fig_trend.update_layout(barmode='group', height=500, plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
                                    xaxis=dict(title="時間期數"), yaxis=dict(title=indicators_dict[trend_metric]['name']),
                                    legend=dict(orientation="h", y=1.05, x=0.5))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("資料筆數不足以繪製歷史趨勢，請確認上傳的財報包含足夠的歷史期數。")
 
    else:
        st.info("請先上傳財務資料以啟用分析功能")
