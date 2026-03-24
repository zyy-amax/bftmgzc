import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 页面配置：沉浸式设计
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="A股估值决策引擎",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式：优化指标卡片和间距
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stExpander"] { border: none !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 深度数据计算层
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
        
        # 百分位计算
        df['percentile'] = df['pe'].rank(pct=True) * 100
        df['win_rate'] = 100 - df['percentile']
        
        # 统计学边界
        threshold_90 = df['pe'].quantile(0.10)
        threshold_80 = df['pe'].quantile(0.20)
        
        # 筑底逻辑计算
        df['is_below_90'] = df['pe'] <= threshold_90
        df['group'] = (df['is_below_90'] != df['is_below_90'].shift()).cumsum()
        df['consecutive_days'] = df.groupby('group')['is_below_90'].transform(lambda x: x.cumsum() if x.iloc[0] else 0)
        
        max_duration = df[df['is_below_90']]['consecutive_days'].max() if any(df['is_below_90']) else 100
        
        return df, threshold_90, threshold_80, max_duration
    except Exception as e:
        st.error(f"数据处理引擎故障: {e}")
        return None, 0, 0, 0

# -----------------------------------------------------------------------------
# 3. 核心视图组件
# -----------------------------------------------------------------------------
def plot_main_chart(df, t90, t80):
    """绘制高颜值交互热力图"""
    fig = px.line(df, x='date', y='pe', title="A股全市场估值历史全景 (PE-TTM)",
                  color_discrete_sequence=['#454545'])
    
    # 添加热力散点
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['pe'],
        mode='markers',
        marker=dict(
            size=4,
            color=df['win_rate'],
            colorscale='RdYlBu_r',
            showscale=True,
            colorbar=dict(title="胜率 %", thickness=15)
        ),
        name="胜率分布"
    ))

    # 强化视觉：绘制“黄金坑”区域
    fig.add_hrect(y0=df['pe'].min()*0.8, y1=t90, fillcolor="#FF4B4B", opacity=0.15, line_width=0)
    
    # 辅助线设置
    fig.add_hline(y=t90, line_dash="dash", line_color="#FF4B4B", annotation_text="90% 胜率线", annotation_font_color="#FF4B4B")
    fig.add_hline(y=t80, line_dash="dot", line_color="#FFA500", annotation_text="80% 胜率线")

    # 布局优化
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1年", step="year", stepmode="backward"),
                    dict(count=5, label="5年", step="year", stepmode="backward"),
                    dict(step="all", label="全部")
                ])
            ),
            rangeslider=dict(visible=False),
            type="date"
        )
    )
    return fig

# -----------------------------------------------------------------------------
# 4. 主程序逻辑
# -----------------------------------------------------------------------------
def main():
    st.title("🔥 A股估值决策系统 2.0")
    st.caption("基于全市场中位数 PE 及历史筑底时长统计模型")

    df, t90, t80, max_dur = get_processed_data()
    
    if df is not None:
        latest = df.iloc[-1]
        cur_pe = latest['pe']
        cur_win = latest['win_rate']
        cur_dur = latest['consecutive_days'] if latest['is_below_90'] else 0
        
        # --- 头部看板 ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("市场当前 PE", f"{cur_pe:.2f}")
        with col2:
            st.metric("历史胜率", f"{cur_win:.1f}%", f"{cur_win-50:.1f}%", delta_color="normal")
        with col3:
            status = "极度低估" if latest['is_below_90'] else "估值合理"
            st.metric("当前状态", status)
        with col4:
            st.metric("数据日期", latest['date'].strftime('%Y-%m-%d'))

        # --- 核心交互区 ---
        tab1, tab2 = st.tabs(["📊 估值热力全景", "📂 历史底部复盘"])
        
        with tab1:
            # 决策建议
            if cur_pe <= t90:
                st.error(f"🚨 **抄底信号激活**：当前已在 90% 胜率线下持续 {int(cur_dur)} 天。")
            elif cur_pe <= t80:
                st.warning("⚠️ **配置区间**：市场进入 80% 胜率区域，建议分批入场。")
            else:
                st.info("ℹ️ **观望区间**：当前估值尚在中位，保持定投节奏。")
            
            # 主图表
            st.plotly_chart(plot_main_chart(df, t90, t80), use_container_width=True)

        with tab2:
            st.subheader("历史「黄金坑」区间统计")
            summary = df[df['is_below_90']].groupby('group').agg({
                'date': ['min', 'max'],
                'consecutive_days': 'max',
                'pe': 'mean'
            }).reset_index()
            summary.columns = ['ID', '起始日期', '结束日期', '筑底天数', '平均PE']
            summary = summary.sort_values('筑底天数', ascending=False)
            
            st.dataframe(
                summary.style.background_gradient(subset=['筑底天数'], cmap='Reds'),
                use_container_width=True,
                hide_index=True
            )

        # --- 侧边栏：深度参数 ---
        with st.sidebar:
            st.header("⚙️ 统计参数")
            st.write(f"90% 胜率 PE 阈值: **{t90:.2f}**")
            st.write(f"80% 胜率 PE 阈值: **{t80:.2f}**")
            st.divider()
            st.markdown("""
            **模型说明：**
            1. 胜率指历史 PE 低于当前值的概率。
            2. 红色区域代表历史极其罕见的低估区间。
            3. 筑底天数参考了 A 股历史上最长磨底时间。
            """)

if __name__ == "__main__":
    main()
