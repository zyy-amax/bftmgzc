import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 页面基础配置
st.set_page_config(page_title="A股全维度估值决策系统", page_icon="⚖️", layout="wide")

# 自定义 CSS 提升质感
st.markdown("""
    <style>
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #f0f2f6; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    .stAlert { border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# 2. 增强型数据引擎
@st.cache_data(ttl=3600)
def get_advanced_data():
    try:
        # 获取 PE 数据
        df = ak.stock_a_ttm_lyr()
        rename_map = {'averagePETTM': 'pe', 'averagePeTtm': 'pe', '平均市盈率': 'pe'}
        df.rename(columns=rename_map, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # 计算百分位与胜率
        df['percentile'] = df['pe'].rank(pct=True) * 100
        df['win_rate'] = 100 - df['percentile']
        
        # 统计学边界
        t90_pe = df['pe'].quantile(0.10) # 90% 胜率线
        t20_pe = df['pe'].quantile(0.80) # 20% 胜率线 (风险线)
        avg_pe = df['pe'].mean()
        min_pe = df['pe'].min()

        # 筑底逻辑
        df['is_below_90'] = df['pe'] <= t90_pe
        df['group'] = (df['is_below_90'] != df['is_below_90'].shift()).cumsum()
        df['consecutive_days'] = df.groupby('group')['is_below_90'].transform(lambda x: x.cumsum() if x.iloc[0] else 0)

        # FED 模型风险溢价 (假设国债利率 2.3%)
        risk_free_rate = 0.023 
        df['risk_premium'] = (1 / df['pe'] - risk_free_rate) * 100

        return df, t90_pe, t20_pe, avg_pe, min_pe
    except Exception as e:
        st.error(f"数据获取异常: {e}")
        return None, 0, 0, 0, 0

# 3. 情绪仪表盘
def draw_valuation_clock(win_rate):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = win_rate,
        title = {'text': "市场情绪时钟 (胜率 %)", 'font': {'size': 18}},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#31333F"},
            'steps': [
                {'range': [0, 20], 'color': "#eeeeee"},   # 风险
                {'range': [20, 80], 'color': "#d1e7ff"},  # 均衡
                {'range': [80, 100], 'color': "#ffdad9"}  # 机会
            ]
        }
    ))
    fig.update_layout(height=280, margin=dict(l=30, r=30, t=50, b=20))
    return fig

# 4. 主程序
def main():
    st.title("⚖️ A股全维度估值决策系统 2.0")
    
    df, t90, t20, avg_pe, min_pe = get_advanced_data()
    
    if df is not None:
        latest = df.iloc[-1]
        cur_pe = latest['pe']
        cur_win = latest['win_rate']
        cur_premium = latest['risk_premium']
        
        # --- 专家级一眼洞察 (核心强化部分) ---
        st.subheader("💡 专家级一眼洞察")
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"📅 **数据切片**：如果你现在买入，理论胜率高达 **{cur_win:.1f}%**。意味着在过去 20 年里，只有 **{100-cur_win:.1f}%** 的时间比现在更贵。")
            with c2:
                # 极端机会提醒逻辑
                if cur_win >= 90:
                    st.error("💎 **【最高指令】千载难逢的机会**：PE 已跌破历史 10% 分位！这是极少数人才能等到的黄金坑，请保持极度贪婪，分批重仓。")
                elif cur_pe < t90:
                    st.success("🎯 **操作指引**：历史级的底部区域。安全边际极高，适合分批买入并长期躺平。")
                elif cur_win < 20:
                    st.error("🚫 **操作指引**：市场情绪严重过热。现在的收益纯靠博弈，估值极贵，小心成为最后的接盘侠。")
                else:
                    st.warning("⚖️ **操作指引**：估值处于均衡水位。建议保持原有定投节奏，不宜激进加仓。")

        # --- 可视化看板 ---
        col_left, col_right = st.columns([1, 2])
        with col_left:
            st.plotly_chart(draw_valuation_clock(cur_win), use_container_width=True)
        with col_right:
            # 压力测试与类比
            years_diff = cur_pe - avg_pe
            risk_bottom = (cur_pe - min_pe) / cur_pe * 100
            
            st.markdown(f"""
            **生活化类比**：现在的 A 股就像是一个回本期为 **{cur_pe:.1f}年** 的生意。
            * 相比历史平均，你{'**节省**了' if years_diff < 0 else '**多等**了'} **{abs(years_diff):.1f}** 年的回本时间。
            * **极限下行压力**：即便回到历史最黑暗时刻，预计回撤空间也仅剩 **{risk_bottom:.1f}%**。
            """)
            st.metric("风险溢价 (FED模型)", f"{cur_premium:.2f}%", help="相比存款，股市多给你的收益率")

        # --- 深度数据图表 ---
        tab1, tab2 = st.tabs(["🔥 情绪热力全景", "📂 历史档案"])
        with tab1:
            fig = px.line(df, x='date', y='pe', title="PE 历史走势与胜率热力分布")
            fig.add_trace(go.Scatter(
                x=df['date'], y=df['pe'], mode='markers',
                marker=dict(size=4, color=df['win_rate'], colorscale='RdYlBu_r', showscale=True),
                name="胜率"
            ))
            fig.add_hrect(y0=df['pe'].min(), y1=t90, fillcolor="red", opacity=0.1, annotation_text="捡钱区")
            fig.add_hrect(y0=t20, y1=df['pe'].max(), fillcolor="gray", opacity=0.1, annotation_text="博傻区")
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            summary = df[df['is_below_90']].groupby('group').agg({
                'date': ['min', 'max'], 'consecutive_days': 'max', 'pe': 'mean'
            }).reset_index()
            summary.columns = ['ID', '起始', '结束', '天数', '平均PE']
            st.dataframe(summary.sort_values('天数', ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
