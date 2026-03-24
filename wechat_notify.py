import akshare as ak
import pandas as pd
import requests
import os

def get_data_and_notify():
    try:
        # 1. 获取数据
        df = ak.stock_a_ttm_lyr()
        rename_map = {'averagePETTM': 'pe', 'averagePeTtm': 'pe', '平均市盈率': 'pe'}
        df.rename(columns=rename_map, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        latest = df.iloc[-1]
        cur_pe = latest['pe']
        avg_pe = df['pe'].mean()
        win_rate = (1 - df['pe'].rank(pct=True).iloc[-1]) * 100
        t90 = df['pe'].quantile(0.10)
        
        # 2. 核心逻辑判断
        years_diff = cur_pe - avg_pe
        if win_rate >= 90:
            status = "🚨【最高指令】千载难逢！"
            note = "当前处于历史极致底部，请保持贪婪！"
        elif cur_pe <= t90:
            status = "🟢【底部区域】建议布局"
            note = "安全边际极高，适合长线布局。"
        elif win_rate <= 20:
            status = "🚫【风险区域】谨慎追高"
            note = "市场情绪过热，建议分批落袋。"
        else:
            status = "⚖️【价值均衡】定投节奏"
            note = "估值适中，不建议大幅调仓。"

        # 3. 组装消息
        title = f"{status} A股估值日报"
        content = f"""
### 📊 专家级一眼洞察
- **当前胜率**：{win_rate:.1f}%
- **当前 PE**：{cur_pe:.2f}
- **回本年数**：比历史平均{'多等' if years_diff > 0 else '节省'} {abs(years_diff):.1f} 年

---
**💡 专家建议**：{note}

**📅 数据日期**：{latest['date'].strftime('%Y-%m-%d')}
[点击查看实时大盘详情](https://bftmgzc.streamlit.app/)
        """

        # 4. 发送微信 (Server酱)
        send_key = os.getenv("SC_KEY")
        if send_key:
            url = f"https://sctapi.ftqq.com/{send_key}.send"
            res = requests.post(url, data={"title": title, "desp": content})
            print(f"发送状态: {res.text}")
        else:
            print("未找到 SC_KEY，请在 Settings-Secrets 中配置")

    except Exception as e:
        print(f"运行出错: {e}")

if __name__ == "__main__":
    get_data_and_notify()
