"""抓取 Hugging Face 模型页（https://huggingface.co/models，默认按热度排序）上的模型卡片，
整理成表格，统计模型类型，并画出类型分布、下载量 / 点赞数排行和类型词云。

用法：python crawler.py [输出目录]      默认输出到 ./data/<年-月>/ 和 ./charts/
"""
import os
import re
import sys
from datetime import date

import matplotlib
matplotlib.use("Agg")  # 只存图，不弹窗，服务器上也能跑
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from bs4 import BeautifulSoup
from wordcloud import WordCloud

URL = "https://huggingface.co/models"
NUMBER = re.compile(r"^[\d.,]+[kKmMbB]?$")
SIZE = re.compile(r"^[\d.]+[BMT]$")  # 参数量，比如 9B、0.6B（不是每张卡片都有）


def fetch_html(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def clean_text(text):
    """卡片上的一行说明按 “•” 拆成几段，去掉空白。"""
    parts = re.split(r"\s*•\s*", " ".join(text.split()))
    return [p.strip() for p in parts if p.strip()]


def parse_meta(parts):
    """按内容而不是位置认字段：类型、参数量（可选）、更新时间、下载量、点赞数。
    以前按位置取，卡片上多出 “9B” 这类参数量时整行会错位。"""
    meta = {"Model Type": None, "Size": None, "Updated Time": None, "Downloads": None, "Likes": None}
    numbers = []
    for p in parts:
        if p.startswith("Updated"):
            meta["Updated Time"] = p
        elif SIZE.match(p) and meta["Updated Time"] is None:
            meta["Size"] = p
        elif NUMBER.match(p):
            numbers.append(p)
        elif meta["Model Type"] is None and meta["Updated Time"] is None:
            meta["Model Type"] = p
    if len(numbers) >= 2:
        meta["Downloads"], meta["Likes"] = numbers[-2], numbers[-1]
    elif len(numbers) == 1:
        meta["Likes"] = numbers[0]
    return meta


def extract_article_info(html):
    soup = BeautifulSoup(html, "html.parser")
    data = []
    for article in soup.find_all("article"):
        header = article.find("header")
        if not header or not header.get("title"):
            continue
        row = {"Code name": header.get("title")}
        line = article.find("div", class_=re.compile("text-gray-400"))
        if line:
            row.update(parse_meta(clean_text(line.text)))
        time_tag = article.find("time")
        if time_tag and time_tag.get("datetime"):
            row["Upload Time"] = time_tag.get("datetime").replace("T", " ")[:19]
        data.append(row)
    return data


def convert_to_int(value):
    if pd.isna(value):
        return 0
    value = str(value).lower().replace(",", "")
    for unit, times in (("k", 1_000), ("m", 1_000_000), ("b", 1_000_000_000)):
        if value.endswith(unit):
            return int(float(value[:-1]) * times)
    return int(float(value))


def analyze_and_visualize_data(df, data_dir, chart_dir):
    df["Downloads"] = df["Downloads"].apply(convert_to_int)
    df["Likes"] = df["Likes"].apply(convert_to_int)
    print(df.head())

    counts = df["Model Type"].value_counts().reset_index()
    counts.columns = ["Model Type", "Count"]
    counts.to_csv(os.path.join(data_dir, "model_type_counts.csv"), index=False)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=counts, x="Count", y="Model Type", color="#4c72b0")
    plt.title("Model types on the trending page")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, "model_types.png"), dpi=120)
    plt.close()

    for column in ("Downloads", "Likes"):
        top = df.nlargest(10, column).copy()
        top["Code name"] = top["Code name"].str.slice(0, 42)  # 有的模型名很长，会把图挤坏
        plt.figure(figsize=(11, 6))
        sns.barplot(data=top, x=column, y="Code name", color="#55a868")
        plt.title(f"Top 10 trending models by {column.lower()}")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(os.path.join(chart_dir, f"top_{column.lower()}.png"), dpi=120)
        plt.close()

    text = df["Model Type"].dropna().str.cat(sep=" ")
    if text:
        cloud = WordCloud(width=800, height=400, background_color="white").generate(text)
        cloud.to_file(os.path.join(chart_dir, "model_types_wordcloud.png"))


def main():
    month = date.today().strftime("%Y-%m")
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", month)
    chart_dir = os.path.join("charts", month)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(chart_dir, exist_ok=True)
    html = fetch_html(URL)
    if not html:
        return
    df = pd.DataFrame(extract_article_info(html))
    if df.empty:
        print("页面上没有找到模型卡片：Hugging Face 可能改了页面结构。")
        return
    df.to_csv(os.path.join(data_dir, "hf_models_data.csv"), index=False)
    analyze_and_visualize_data(df, data_dir, chart_dir)
    print(f"{len(df)} models -> {data_dir}, charts -> {chart_dir}")


if __name__ == "__main__":
    main()
