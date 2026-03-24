import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 页面配置与美化
st.set_page_config(page_title="A股全维度估值决策系统", page_icon="⚖️", layout="wide")

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
        t20_pe = df['pe'].quantile(0.80) # 20% 胜率线
        avg_pe = df['pe'].mean()
        min_pe = df['pe'].min()

        # 筑底逻辑
        df['is_below_90'] = df['pe'] <= t90_pe
        df['group'] = (df['is_below_90'] != df['is_below_90'].shift()).cumsum()
        df['consecutive_days'] = df.groupby('group')['is_below_90'].transform(lambda x: x.cumsum() if x.iloc[0] else 0)

        # --- 模拟 FED 模型：假设无风险利率 (以10年国债收益率 2.3% 为例) ---
        risk_free_rate = 0.023 
        df['earning_yield'] = 1 / df['pe']
        df['risk_premium'] = (df['earning_yield'] - risk_free_rate) * 100

        return df, t90_pe, t20_pe, avg_pe, min_pe
    except Exception as e:
        st.error(f"数据引擎故障: {e}")
        return None, 0, 0, 0, 0

# 3. 可视化组件：估值时钟 (Gauge)
def draw_valuation_clock(win_rate):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = win_rate,
        title = {'text': "市场情绪时钟 (胜率 %)"},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#31333F"},
            'steps': [
                {'range': [0, 20], 'color': "#eeeeee"}, # 风险区
                {'range': [20, 80], 'color': "#d1e7ff"}, # 均衡区
                {'range': [80, 100], 'color': "#ffdad9"} # 机会区
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': win_rate
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=20))
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
        
        # --- 第一部分：三秒钟看懂现状 ---
        st.subheader("💡 核心洞察：一分钟决策点")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.plotly_chart(draw_valuation_clock(cur_win), use_container_width=True)
        
        with c2:
            # 生活化类比文案
            if cur_win >= 80:
                st.success(f"🛒 **超市打折日**：现在买入就像超市清仓，PE仅为 {cur_pe:.2f}。历史上只有 {100-cur_win:.1f}% 的时间比现在更便宜。建议：分批买入，耐心持股。")
            elif cur_win <= 20:
                st.error(f"🚫 **高价博傻期**：现在的估值是“情绪”堆出来的。PE 高达 {cur_pe:.2f}。建议：分阶段落袋为安，不宜追高。")
            else:
                st.info(f"⚖️ **价值均衡区**：目前既不便宜也不贵。PE 为 {cur_pe:.2f}。建议：保持原有定投节奏。")
            
            # 回本天数与压力测试
            years_to_avg = cur_pe - avg_pe
            risk_to_bottom = (cur_pe - min_pe) / cur_pe * 100
            
            col_a, col_b = st.columns(2)
            col_a.metric("回本年数差", f"{years_to_avg:+.1f} 年", help="相比历史平均PE，你回本需要多等或少等的时间")
            col_b.metric("极限下行风险", f"-{risk_to_bottom:.1f}%", help="如果回到历史最低 PE，可能面临的极端回撤")

        # --- 第二部分：FED 风险溢价模型 ---
        st.markdown("---")
        st.subheader("🏦 FED 风险溢价模型 (股市 vs 债市)")
        st.write(f"当前股息收益率 (1/PE) 减去 10年期国债利率得到的溢价为 **{cur_premium:.2f}%**。")
        
        fig_fed = px.area(df, x='date', y='risk_premium', title="股权风险溢价 (越高代表股市性价比越高)",
                          color_discrete_sequence=['#FF4B4B' if cur_premium > 5 else '#0068C9'])
        fig_fed.add_hline(y=df['risk_premium'].mean(), line_dash="dash", annotation_text="平均溢价水平")
        st.plotly_chart(fig_fed, use_container_width=True)

        # --- 第三部分：深度热力图 ---
        tab1, tab2 = st.tabs(["🔥 估值情绪热力图", "📂 历史筑底档案"])
        
        with tab1:
            # 情绪 Heatmap
            fig_main = px.line(df, x='date', y='pe', title="A股历史 PE 走势与情绪绑定")
            fig_main.add_trace(go.Scatter(
                x=df['date'], y=df['pe'], mode='markers',
                marker=dict(size=4, color=df['win_rate'], colorscale='RdYlBu_r', showscale=True),
                name="情绪热力"
            ))
            # 标记区间
            fig_main.add_hrect(y0=df['pe'].min(), y1=t90, fillcolor="red", opacity=0.1, annotation_text="低估捡钱区")
            fig_main.add_hrect(y0=t20, y1=df['pe'].max(), fillcolor="gray", opacity=0.1, annotation_text="博傻风险区")
            
            st.plotly_chart(fig_main, use_container_width=True)

        with tab2:
            # 筑底历史
            summary = df[df['is_below_90']].groupby('group').agg({
                'date': ['min', 'max'],
                'consecutive_days': 'max',
                'pe': 'mean'
            }).reset_index()
            summary.columns = ['ID', '进入日期', '离开日期', '磨底天数', '期间平均PE']
            st.dataframe(summary.sort_values('磨底天数', ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
