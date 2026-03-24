import akshare as ak
import pandas as pd
import requests
import os

def get_data_and_notify():
    # 1. 获取数据（逻辑同 Streamlit）
    df = ak.stock_a_ttm_lyr()
    rename_map = {'averagePETTM': 'pe', 'averagePeTtm': 'pe', '平均市盈率': 'pe'}
    df.rename(columns=rename_map, inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    latest = df.iloc[-1]
    cur_pe = latest['pe']
    win_rate = (1 - df['pe'].rank(pct=True).iloc[-1]) * 100
    t90 = df['pe'].quantile(0.10)
    
    # 2. 组装消息
    status = "🔴【极度低估】千载难逢！" if win_rate >= 90 else ("🟢【底部区域】建议布局" if cur_pe <= t90 else "⚪【估值正常】保持定投")
    
    title = f"A股估值提醒：{status}"
    content = f"""
### 📊 A股全市场估值日报
- **当前日期**：{latest['date'].strftime('%Y-%m-%d')}
- **当前 PE**：{cur_pe:.2f}
- **理论胜率**：{win_rate:.1f}%
- **90%胜率线**：{t90:.2f}

**建议**：{status}
[点击查看详细图表](https://你的新短链接.streamlit.app/)
    """

    # 3. 发送微信 (使用 Server酱)
    send_key = os.getenv("SC_KEY")
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    requests.post(url, data={"title": title, "desp": content})

if __name__ == "__main__":
    get_data_and_notify()