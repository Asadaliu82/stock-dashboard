import json
import datetime
import yfinance as yf
import requests
import os
from xml.etree import ElementTree as ET

STOCK_MAP = {
    "2330": {"name": "台積電", "symbol": "2330.TW", "category": "core"},
    "2454": {"name": "聯發科", "symbol": "2454.TW", "category": "core"},
    "6213": {"name": "聯茂",   "symbol": "6213.TWO", "category": "ai"},
    "3605": {"name": "宏致",   "symbol": "3605.TW", "category": "ai"},
    "6530": {"name": "創威",   "symbol": "6530.TWO", "category": "ai"},
    "6168": {"name": "宏齊",   "symbol": "6168.TW", "category": "ai"},
    "00713": {"name": "元大台灣高息低波", "symbol": "00713.TW", "category": "high_yield"},
    "00712": {"name": "復華富時不動產",   "symbol": "00712.TW", "category": "high_yield"},
    "00933B": {"name": "國泰10Y+金融債", "symbol": "00933B.TWO", "category": "high_yield"}
}

def fetch_google_news(stock_name):
    news_list = []
    try:
        url = f"https://news.google.com/rss/search?q={stock_name}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        resp = requests.get(url, timeout=5)
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item')[:3]:
            news_list.append({
                "title": item.find('title').text,
                "time": "最新",
                "url": item.find('link').text
            })
    except Exception as e:
        print(f"新聞抓取失敗 ({stock_name}): {e}")
    return news_list

def send_telegram_msg(msg):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
            print("✅ Telegram 戰情摘要發送成功！")
        except Exception as e:
            print(f"Telegram 發送失敗: {e}")

def main():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    portfolio_data = {
        "updated_at": today_str,
        "stocks": {}
    }

    summary_lines = [f"📱 *【持股戰情室盤後日報 - {datetime.date.today()}】*"]

    for code, info in STOCK_MAP.items():
        ticker = yf.Ticker(info["symbol"])
        df = ticker.history(period="60d")

        if df.empty:
            continue

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        price = round(float(latest['Close']), 2)
        prev_price = round(float(prev['Close']), 2)
        change = round(price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2)
        df['MA20'] = df['Close'].rolling(window=20).mean()

        history = []
        for idx, row in df.tail(10).iterrows():
            history.append({
                "date": idx.strftime("%m/%d"),
                "price": round(float(row['Close']), 2),
                "ma20": round(float(row['MA20']), 2) if not list(df['MA20'].isna())[-1] else round(float(row['Close']), 2)
            })

        news = fetch_google_news(info['name'])

        portfolio_data["stocks"][code] = {
            "name": info["name"],
            "category": info["category"],
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "history": history,
            "news": news
        }

        sign = "+" if change >= 0 else ""
        summary_lines.append(f"• *{info['name']} ({code})*: ${price} ({sign}{change_pct}%)")

    # 寫入 JSON 檔
    with open("portfolio_data.json", "w", encoding="utf-8") as f:
        json.dump(portfolio_data, f, ensure_ascii=False, indent=2)

    # 發送 Telegram 通報
    summary_msg = "\n".join(summary_lines)
    send_telegram_msg(summary_msg)

if __name__ == "__main__":
    main()