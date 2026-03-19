# 🚀 插入全新設計的 AI 戰略連動解析區塊 (總經板塊專屬)
if selected_category == "📈 總體經濟與大盤 (宏觀指標)" and option in MACRO_IMPACT:
    impact_data = MACRO_IMPACT[option]
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.04); margin-bottom: 25px;">
        
        <div style="display: flex; align-items: center; margin-bottom: 24px; border-bottom: 2px solid #f1f5f9; padding-bottom: 16px;">
            <div style="background: #1e293b; color: #ffffff; padding: 6px 14px; border-radius: 6px; font-weight: 800; font-size: 14px; margin-right: 12px; letter-spacing: 1px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">AI 戰略洞察</div>
            <div style="font-size: 19px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px;">{option} 連動解析</div>
        </div>
        
        <div style="background: linear-gradient(145deg, #f8fafc, #f1f5f9); border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px 24px; margin-bottom: 24px; position: relative; overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: #64748b;"></div>
            <div style="font-size: 13px; color: #64748b; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; display: flex; align-items: center;">
                <span style="margin-right: 8px; font-size: 16px;">🎯</span> 核心戰略定義
            </div>
            <div style="font-size: 15.5px; color: #334155; line-height: 1.7; font-weight: 600;">
                {impact_data['exp']}
            </div>
        </div>
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            
            <div style="flex: 1; min-width: 300px; background: #ffffff; border: 1px solid #fca5a5; border-radius: 10px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.05); overflow: hidden;">
                <div style="background: #fef2f2; padding: 14px 20px; border-bottom: 1px solid #fee2e2; display: flex; align-items: center;">
                    <div style="background: #ef4444; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: 900; font-size: 16px; margin-right: 12px; box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);">↑</div>
                    <div style="color: #b91c1c; font-weight: 800; font-size: 16px; letter-spacing: 0.5px;">向上突破對集團之衝擊</div>
                </div>
                <div style="padding: 20px; font-size: 15px; color: #334155; line-height: 1.7; font-weight: 600;">
                    {impact_data['up']}
                </div>
            </div>
            
            <div style="flex: 1; min-width: 300px; background: #ffffff; border: 1px solid #86efac; border-radius: 10px; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.05); overflow: hidden;">
                <div style="background: #f0fdf4; padding: 14px 20px; border-bottom: 1px solid #dcfce7; display: flex; align-items: center;">
                    <div style="background: #22c55e; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: 900; font-size: 16px; margin-right: 12px; box-shadow: 0 2px 6px rgba(34, 197, 94, 0.3);">↓</div>
                    <div style="color: #15803d; font-weight: 800; font-size: 16px; letter-spacing: 0.5px;">向下跌破對集團之影響</div>
                </div>
                <div style="padding: 20px; font-size: 15px; color: #334155; line-height: 1.7; font-weight: 600;">
                    {impact_data['down']}
                </div>
            </div>
            
        </div>
    </div>
    """, unsafe_allow_html=True)
