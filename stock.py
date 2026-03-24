import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 页面基础配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="A股估值决策系统 2.0-专业版",
    page_icon="📈",
    layout="wide"
)

# 自定义 CSS：增加动态颜色和卡片样式
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #f0f2f6; box-shadow: 2px 2px 5px rgba(0,0,0,0.03); }
    [data-testid="stMetricDelta"] svg { display: none; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 核心数据引擎
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_processed_data():
    try:
        # 获取 A 股 TTM PE 数据
        df = ak.stock_a_ttm_lyr()
        rename_map = {'averagePETTM': 'pe', 'averagePeTtm': 'pe', '平均市盈率': 'pe'}
        df.rename(columns=rename_map, inplace=True)
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 计算百分位与胜率
        df['percentile'] = df['pe'].rank(pct=True) * 100
        df['win_rate'] = 100 - df['percentile']
        
        # 统计学边界定义
        threshold_90_win = df['pe'].quantile(0.10) # 90%胜率线
        threshold_20_win = df['pe'].quantile(0.80) # 20%胜率线 (高风险线)
        
        # 筑底逻辑计算
        df['is_below_90'] = df['pe'] <= threshold_90_win
        df['group'] = (df['is_below_90'] != df['is_below_90'].shift()).cumsum()
        df['consecutive_days'] = df.groupby('group')['is_below_90'].transform(lambda x: x.cumsum() if x.iloc[0] else 0)
        
        return df, threshold_90_win, threshold_20_win
    except Exception as e:
        st.error(f"数据获取失败，请检查网络或接口: {e}")
        return None, 0, 0

# -----------------------------------------------------------------------------
# 3. 绘图组件
# -----------------------------------------------------------------------------
def plot_main_chart(df, t90, t20):
    fig = px.line(df, x='date', y='pe', title="A股全市场 PE 走势与胜率监控",
                  color_discrete_sequence=['#444444'])
    
    # 胜率散点
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['pe'], mode='markers',
        marker=dict(size=3.5, color=df['win_rate'], colorscale='RdYlBu_r', showscale=True),
        name="胜率分布"
    ))

    # 绘制高低区间背景
    fig.add_hrect(y0=df['pe'].min()*0.9, y1=t90, fillcolor="red", opacity=0.1, line_width=0, annotation_text="底部机会区")
    fig.add_hrect(y0=t20, y1=df['pe'].max()*1.1, fillcolor="gray", opacity=0.1, line_width=0, annotation_text="高位风险区")
    
    # 辅助线
    fig.add_hline(y=t90, line_dash="dash", line_color="red", annotation_text="90%胜率线")
    fig.add_hline(y=t20, line_dash="dash", line_color="#333", annotation_text="20%胜率线")

    fig.update_layout(hovermode="x unified", plot_bgcolor='white', margin=dict(l=10, r=10, t=50, b=10))
    return fig

# -----------------------------------------------------------------------------
# 4. 主程序逻辑
# -----------------------------------------------------------------------------
def main():
    st.title("🔥 A股估值决策系统 2.0")
    
    df, t90, t20 = get_processed_data()
    
    if df is not None:
        latest = df.iloc[-1]
        cur_pe = latest['pe']
        cur_win = latest['win_rate']
        cur_date = latest['date'].strftime('%Y-%m-%d')
        
        # --- 核心判断逻辑 ---
        is_opportunity = cur_pe <= t90
        is_danger = cur_win < 20
        
        # 第一行：核心指标看板
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("当前市场 PE", f"{cur_pe:.2f}")
        
        # 胜率卡片：低于20%显示红色警告
        win_label = f"{cur_win:.1f}%"
        delta_val = "⚠️ 风险极高" if is_danger else f"{cur_win-50:.1f}% vs 基准"
        m2.metric("理论胜率", win_label, delta_val, delta_color="inverse" if is_danger else "normal")
        
        # 状态卡片：识别是否进入90%胜率区
        status_text = "🔴 已进入90%胜率区" if is_opportunity else "⚪ 未进入机会区"
        if is_danger: status_text = "💀 高位风险区"
        m3.metric("最新识别状态", status_text)
        
        m4.metric("更新日期", cur_date)

        # 决策通知栏
        if is_opportunity:
            st.error(f"🚀 **识别到黄金坑**：当前日期 ({cur_date}) 已跌破 90% 胜率线 (PE ≤ {t90:.2f})，历史大底部特征明显。")
        elif is_danger:
            st.warning(f"🔔 **高位警报**：当前胜率 ({cur_win:.1f}%) 已低于 20%。市场估值处于历史高位，请注意回撤风险。")
        else:
            st.info("📊 **估值平稳**：当前处于中位区间，建议保持常规资产配置策略。")

        # 展示图表和表格
        tab1, tab2 = st.tabs(["📊 动态热力全景", "📂 历史机会复盘"])
        
        with tab1:
            st.plotly_chart(plot_main_chart(df, t90, t20), use_container_width=True)

        with tab2:
            st.subheader("历史 90% 胜率线下持续记录")
            summary = df[df['is_below_90']].groupby('group').agg({
                'date': ['min', 'max'],
                'consecutive_days': 'max',
                'pe': 'mean'
            }).reset_index()
            summary.columns = ['ID', '起始日期', '结束日期', '筑底天数', '平均PE']
            st.dataframe(summary.sort_values('筑底天数', ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
