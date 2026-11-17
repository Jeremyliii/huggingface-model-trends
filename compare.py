"""对比两次抓取的模型类型分布：python compare.py data/2024-07 data/2026-11 → charts/compare.png"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def shares(folder):
    counts = pd.read_csv(os.path.join(folder, "model_type_counts.csv")).set_index("Model Type")["Count"]
    return counts / counts.sum() * 100


def main():
    old, new = sys.argv[1], sys.argv[2]
    table = pd.DataFrame({os.path.basename(old.rstrip("/")): shares(old), os.path.basename(new.rstrip("/")): shares(new)}).fillna(0)
    table = table.loc[table.max(axis=1).sort_values().index]
    ax = table.plot.barh(figsize=(10, 7), color=["#b0b0b0", "#4c72b0"], width=.8)
    ax.set_xlabel("Share of models on the trending page (%)")
    ax.set_ylabel("")
    ax.set_title("What is trending on Hugging Face: model types, then and now")
    plt.tight_layout()
    os.makedirs("charts", exist_ok=True)
    plt.savefig(os.path.join("charts", "compare.png"), dpi=120)
    print(table.round(1).iloc[::-1].to_string())


if __name__ == "__main__":
    main()
