"""
05_advanced_insights.py
Generates advanced visualizations and deeper insights from the parsed UHC data.
Produces PNG charts in reports/charts/ and an extended insights report.
"""
import argparse
import sys
from pathlib import Path
from collections import Counter
import re

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server/CI
import matplotlib.pyplot as plt
import seaborn as sns

# make local utils importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.io_utils import ensure_dir

# --- Style defaults ---
sns.set_theme(style="whitegrid", font_scale=1.1)
ACCENT = "#2196F3"
FIG_DPI = 150
CHART_DIR = "reports/charts"


def load_data(processed_dir: str) -> dict:
    """Load all processed datasets into a dict."""
    def safe_pq(name):
        p = Path(processed_dir) / name
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()

    def safe_csv(name):
        p = Path(processed_dir) / name
        return pd.read_csv(p) if p.exists() else pd.DataFrame()

    return {
        "downloads": safe_csv("download_log.csv"),
        "parse_log": safe_csv("parse_log.csv"),
        "indexes": safe_pq("index_files.parquet"),
        "entities": safe_pq("reporting_entities.parquet"),
        "plans": safe_pq("plans.parquet"),
        "refs": safe_pq("referenced_files.parquet"),
    }


# --- Chart functions ---

def chart_download_status(downloads: pd.DataFrame, output_dir: str):
    """Bar chart of download statuses."""
    fig, ax = plt.subplots(figsize=(8, 5))
    status_counts = downloads["status"].value_counts()
    colors = ["#4CAF50" if s == "downloaded" else "#2196F3" if s == "already_exists"
              else "#F44336" for s in status_counts.index]
    bars = ax.bar(status_counts.index, status_counts.values, color=colors, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, status_counts.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                f"{val:,}", ha="center", va="bottom", fontweight="bold", fontsize=13)
    ax.set_title("Download Status Distribution", fontsize=16, fontweight="bold", pad=15)
    ax.set_ylabel("Number of Files", fontsize=12)
    ax.set_xlabel("")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/01_download_status.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 01_download_status.png")


def chart_entity_distribution(indexes: pd.DataFrame, output_dir: str):
    """Horizontal bar chart of reporting entities."""
    fig, ax = plt.subplots(figsize=(10, 6))
    entity_counts = indexes["reporting_entity_name"].value_counts()
    colors = sns.color_palette("Blues_r", len(entity_counts))
    bars = ax.barh(entity_counts.index[::-1], entity_counts.values[::-1], color=colors[::-1], edgecolor="white")
    for bar, val in zip(bars, entity_counts.values[::-1]):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                f"{val:,}", ha="left", va="center", fontweight="bold", fontsize=11)
    ax.set_title("Index Files per Reporting Entity", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Number of Index Files", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, entity_counts.max() * 1.15)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/02_entity_distribution.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 02_entity_distribution.png")


def chart_plans_per_index(plans: pd.DataFrame, output_dir: str):
    """Histogram showing how many plans each index file contains."""
    fig, ax = plt.subplots(figsize=(10, 5))
    plans_per = plans.groupby("index_file_id").size()
    ax.hist(plans_per, bins=range(1, plans_per.max() + 2), color=ACCENT, edgecolor="white",
            linewidth=1.2, alpha=0.85, align="left")
    ax.axvline(plans_per.mean(), color="#F44336", linestyle="--", linewidth=2,
               label=f"Mean: {plans_per.mean():.1f}")
    ax.axvline(plans_per.median(), color="#FF9800", linestyle="--", linewidth=2,
               label=f"Median: {plans_per.median():.1f}")
    ax.legend(fontsize=12, frameon=True, fancybox=True, shadow=True)
    ax.set_title("Plans per Index File Distribution", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Number of Plans", fontsize=12)
    ax.set_ylabel("Number of Index Files", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/03_plans_per_index.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 03_plans_per_index.png")


def chart_file_type_pie(refs: pd.DataFrame, output_dir: str):
    """Pie chart of referenced file types (in-network vs allowed-amount)."""
    fig, ax = plt.subplots(figsize=(8, 6))
    type_counts = refs["file_type"].value_counts()
    colors = ["#2196F3", "#FF9800"]
    wedges, texts, autotexts = ax.pie(
        type_counts.values, labels=type_counts.index, autopct="%1.1f%%",
        colors=colors, startangle=90, textprops={"fontsize": 13},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        pctdistance=0.55
    )
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_color("white")
    ax.set_title("Referenced File Types", fontsize=16, fontweight="bold", pad=15)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/04_file_type_pie.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 04_file_type_pie.png")


def chart_url_reuse(refs: pd.DataFrame, output_dir: str):
    """Bar chart showing how many times the top URLs are referenced."""
    fig, ax = plt.subplots(figsize=(12, 7))
    url_counts = refs.groupby("location_url").agg(
        refs=("location_url", "size"),
        distinct_indexes=("index_file_id", "nunique")
    ).sort_values("refs", ascending=False).head(10)

    # shorten URL labels so they fit on the chart
    labels = []
    for url in url_counts.index:
        parts = url.split("/")[-1].replace(".json.gz", "").replace("2026-06-01_", "")
        if len(parts) > 60:
            parts = parts[:57] + "..."
        labels.append(parts)

    y_pos = range(len(labels))
    bars = ax.barh(y_pos, url_counts["refs"].values, color=sns.color_palette("viridis", 10),
                   edgecolor="white", linewidth=1.2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    for bar, val, idx_count in zip(bars, url_counts["refs"].values, url_counts["distinct_indexes"].values):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2,
                f"{val:,} refs ({idx_count} indexes)", ha="left", va="center", fontsize=10)
    ax.set_title("Top 10 Most Referenced In-Network Rate Files", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("Number of References", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.invert_yaxis()
    ax.set_xlim(0, url_counts["refs"].max() * 1.35)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/05_url_reuse.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 05_url_reuse.png")


def chart_network_types(refs: pd.DataFrame, output_dir: str):
    """Analyze and chart the network types extracted from referenced file URLs."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # try to extract network names from the URL path
    network_names = []
    for url in refs[refs["file_type"] == "in_network"]["location_url"].dropna():
        match = re.search(r"Third-Party-Administrator_(.+?)_\d+_in-network", url)
        if match:
            network_names.append(match.group(1).replace("-", " "))

    if not network_names:
        # fallback: use the description column if URL parsing didn't work
        for desc in refs[refs["file_type"] == "in_network"]["description"].dropna():
            network_names.append(desc)

    network_counts = Counter(network_names)
    top_networks = pd.Series(dict(network_counts.most_common(12)))

    colors = sns.color_palette("Set2", len(top_networks))
    bars = ax.barh(top_networks.index[::-1], top_networks.values[::-1],
                   color=colors[::-1], edgecolor="white", linewidth=1.2)
    for bar, val in zip(bars, top_networks.values[::-1]):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                f"{val:,}", ha="left", va="center", fontweight="bold", fontsize=11)
    ax.set_title("Top 12 Insurance Network Types (from In-Network File URLs)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Number of Referenced Files", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, top_networks.max() * 1.15)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/06_network_types.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 06_network_types.png")
    return network_counts


def chart_refs_per_index(refs: pd.DataFrame, output_dir: str):
    """Histogram of referenced files per index file."""
    fig, ax = plt.subplots(figsize=(10, 5))
    refs_per = refs.groupby("index_file_id").size()
    ax.hist(refs_per, bins=30, color="#9C27B0", edgecolor="white", linewidth=1.2, alpha=0.85)
    ax.axvline(refs_per.mean(), color="#F44336", linestyle="--", linewidth=2,
               label=f"Mean: {refs_per.mean():.1f}")
    ax.axvline(refs_per.median(), color="#FF9800", linestyle="--", linewidth=2,
               label=f"Median: {refs_per.median():.1f}")
    ax.legend(fontsize=12, frameon=True, fancybox=True, shadow=True)
    ax.set_title("Referenced Files per Index File", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Number of Referenced Files", fontsize=12)
    ax.set_ylabel("Number of Index Files", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/07_refs_per_index.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 07_refs_per_index.png")


def chart_entity_plan_heatmap(indexes: pd.DataFrame, plans: pd.DataFrame, output_dir: str):
    """Grouped bar chart: total vs distinct plans per reporting entity."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # link entity names to plans via index_file_id
    entity_map = indexes[["index_file_id", "reporting_entity_name"]].drop_duplicates()
    plans_with_entity = plans.merge(entity_map, on="index_file_id", how="left")

    entity_plan_counts = plans_with_entity.groupby("reporting_entity_name").agg(
        total_plans=("plan_key", "count"),
        distinct_plans=("plan_name", "nunique"),
        index_files=("index_file_id", "nunique"),
    ).sort_values("total_plans", ascending=False)

    entity_plan_counts["avg_plans_per_index"] = (
        entity_plan_counts["total_plans"] / entity_plan_counts["index_files"]
    ).round(2)

    # grouped bars: total plans vs distinct plan names
    x = range(len(entity_plan_counts))
    width = 0.35
    bars1 = ax.bar([i - width/2 for i in x], entity_plan_counts["total_plans"],
                   width, label="Total Plan Rows", color="#2196F3", edgecolor="white")
    bars2 = ax.bar([i + width/2 for i in x], entity_plan_counts["distinct_plans"],
                   width, label="Distinct Plan Names", color="#FF9800", edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(entity_plan_counts.index, rotation=30, ha="right", fontsize=9)
    ax.set_title("Plans by Reporting Entity", fontsize=16, fontweight="bold", pad=15)
    ax.set_ylabel("Count", fontsize=12)
    ax.legend(fontsize=11, frameon=True, fancybox=True, shadow=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # value labels on top of each bar
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f"{int(bar.get_height()):,}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f"{int(bar.get_height()):,}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig.savefig(f"{output_dir}/08_entity_plan_breakdown.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 08_entity_plan_breakdown.png")
    return entity_plan_counts


def chart_file_size_distribution(downloads: pd.DataFrame, output_dir: str):
    """Distribution of downloaded file sizes."""
    fig, ax = plt.subplots(figsize=(10, 5))
    sizes = downloads[downloads["status"].isin(["downloaded", "already_exists"])]["bytes_written"]
    sizes_kb = sizes / 1024

    ax.hist(sizes_kb, bins=40, color="#00BCD4", edgecolor="white", linewidth=1.2, alpha=0.85)
    ax.axvline(sizes_kb.mean(), color="#F44336", linestyle="--", linewidth=2,
               label=f"Mean: {sizes_kb.mean():.1f} KB")
    ax.axvline(sizes_kb.median(), color="#FF9800", linestyle="--", linewidth=2,
               label=f"Median: {sizes_kb.median():.1f} KB")
    ax.legend(fontsize=12, frameon=True, fancybox=True, shadow=True)
    ax.set_title("Index File Size Distribution", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("File Size (KB)", fontsize=12)
    ax.set_ylabel("Number of Files", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/09_file_size_dist.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 09_file_size_dist.png")


def chart_pipeline_summary(downloads: pd.DataFrame, indexes: pd.DataFrame,
                           plans: pd.DataFrame, refs: pd.DataFrame, output_dir: str):
    """Summary infographic-style chart showing pipeline numbers."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    fig.suptitle("Pipeline Summary — Key Metrics", fontsize=18, fontweight="bold", y=1.02)

    metrics = [
        ("Index Files\nParsed", len(indexes), "#4CAF50"),
        ("Plans\nExtracted", len(plans), "#2196F3"),
        ("Referenced\nFiles", len(refs), "#FF9800"),
        ("Distinct\nURLs", refs["location_url"].nunique() if not refs.empty else 0, "#9C27B0"),
    ]

    for ax, (label, value, color) in zip(axes, metrics):
        ax.text(0.5, 0.55, f"{value:,}", transform=ax.transAxes, fontsize=36,
                fontweight="bold", ha="center", va="center", color=color)
        ax.text(0.5, 0.15, label, transform=ax.transAxes, fontsize=13,
                ha="center", va="center", color="#555555")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        # subtle background circle for visual emphasis
        circle = plt.Circle((0.5, 0.55), 0.3, transform=ax.transAxes,
                           color=color, alpha=0.08, zorder=0)
        ax.add_patch(circle)

    fig.tight_layout()
    fig.savefig(f"{output_dir}/00_pipeline_summary.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 00_pipeline_summary.png")


def chart_url_sharing_network(refs: pd.DataFrame, indexes: pd.DataFrame, output_dir: str):
    """Show how many index files share each distinct URL (data centralization)."""
    fig, ax = plt.subplots(figsize=(10, 5))

    url_index_counts = refs.groupby("location_url")["index_file_id"].nunique()
    ax.hist(url_index_counts, bins=50, color="#E91E63", edgecolor="white", linewidth=1.2, alpha=0.85)
    ax.set_title("URL Sharing: How Many Index Files Reference Each Distinct URL",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Number of Distinct Index Files Sharing the URL", fontsize=12)
    ax.set_ylabel("Number of Distinct URLs", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # callout for the most shared URL
    ax.annotate(
        f"Most shared URL:\n{url_index_counts.max()} index files",
        xy=(url_index_counts.max(), 1), xytext=(url_index_counts.max() * 0.7, ax.get_ylim()[1] * 0.7),
        fontsize=11, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#333"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF9C4", edgecolor="#F44336")
    )

    fig.tight_layout()
    fig.savefig(f"{output_dir}/10_url_sharing.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] 10_url_sharing.png")


def generate_extended_insights(data: dict, output_dir: str):
    """Generate extended text insights for the presentation."""
    indexes = data["indexes"]
    plans = data["plans"]
    refs = data["refs"]
    downloads = data["downloads"]

    lines = [
        "# Extended Insights — Deep Analysis",
        "",
    ]

    # Insight A: how centralized is the data?
    url_index_counts = refs.groupby("location_url")["index_file_id"].nunique()
    top_url = url_index_counts.idxmax()
    top_url_count = url_index_counts.max()
    total_urls = refs["location_url"].nunique()
    urls_shared_10_plus = (url_index_counts >= 10).sum()

    lines += [
        "## Insight A: Massive Data Centralization",
        "",
        f"- Only **{total_urls}** distinct in-network/allowed-amount URLs serve **{len(refs):,}** references.",
        f"- The most referenced URL appears in **{top_url_count}** distinct index files.",
        f"- **{urls_shared_10_plus}** URLs are shared by 10+ index files.",
        f"- This means UHC uses a **hub-and-spoke model**: a small set of rate files are shared across hundreds of employer plans.",
        "",
        "**Business Implication:** Most employers on UHC get the same negotiated rates. "
        "The transparency data reveals that plan-level rate customization is rare — "
        "the same in-network rate tables serve hundreds of different employer plans.",
        "",
    ]

    # Insight B: which entities dominate?
    entity_counts = indexes["reporting_entity_name"].value_counts()
    top_entity_pct = entity_counts.iloc[0] / len(indexes) * 100

    lines += [
        "## Insight B: Entity Concentration",
        "",
        f"- **{entity_counts.iloc[0]:,}** of {len(indexes):,} index files ({top_entity_pct:.1f}%) "
        f"belong to **{entity_counts.index[0]}**.",
        f"- The remaining {len(entity_counts) - 1} entities account for only {100 - top_entity_pct:.1f}% of files.",
        f"- All entities are classified as **Third-Party Administrators** (TPAs).",
        "",
        "**Business Implication:** UHC operates primarily through TPA arrangements. "
        "United-HealthCare-Services-Inc administers the vast majority of plans, "
        "with Oxford Health Plans and UMR as secondary administrators.",
        "",
    ]

    # Insight C: what networks show up most?
    network_names = []
    for url in refs[refs["file_type"] == "in_network"]["location_url"].dropna():
        match = re.search(r"Third-Party-Administrator_(.+?)_\d+_in-network", url)
        if match:
            network_names.append(match.group(1).replace("-", " "))

    if network_names:
        network_counter = Counter(network_names)
        top_5 = network_counter.most_common(5)
        lines += [
            "## Insight C: Network Portfolio Analysis",
            "",
            "The top 5 insurance networks by reference count:",
            "",
        ]
        for name, count in top_5:
            lines.append(f"1. **{name}**: {count:,} references")
        lines += [
            "",
            "**Business Implication:** Networks like OHPH-ST, Choice Plus, and Core "
            "dominate the landscape. Health plan sponsors choosing UHC most commonly "
            "access these network tiers.",
            "",
        ]

    # Insight D: single-plan vs multi-plan employers
    plans_per_idx = plans.groupby("index_file_id").size()
    single_plan = (plans_per_idx == 1).sum()
    multi_plan = (plans_per_idx > 1).sum()
    single_pct = single_plan / len(plans_per_idx) * 100

    lines += [
        "## Insight D: Plan Complexity per Employer",
        "",
        f"- **{single_plan:,}** index files ({single_pct:.1f}%) have exactly **1 plan** (single-plan employers).",
        f"- **{multi_plan:,}** index files ({100-single_pct:.1f}%) have **multiple plans** (multi-plan employers).",
        f"- Maximum plans in a single index: **{plans_per_idx.max()}**.",
        "",
        "**Business Implication:** Most employers in this sample offer a single health plan. "
        "Larger employers with multiple plan options are the minority but have more complex "
        "transparency reporting requirements.",
        "",
    ]

    # Insight E: file sizes
    if not downloads.empty:
        sizes = downloads[downloads["status"].isin(["downloaded", "already_exists"])]["bytes_written"]
        lines += [
            "## Insight E: Index File Size Analysis",
            "",
            f"- **Mean file size:** {sizes.mean()/1024:.1f} KB",
            f"- **Median file size:** {sizes.median()/1024:.1f} KB",
            f"- **Smallest:** {sizes.min():,} bytes | **Largest:** {sizes.max():,} bytes ({sizes.max()/1024:.1f} KB)",
            f"- **Total data volume:** {sizes.sum()/1024/1024:.1f} MB for 1,000 index files",
            "",
            "**Business Implication:** Index files are lightweight metadata files (2-3 KB average). "
            "The actual rate data they reference (in-network rate files) can be **gigabytes** each. "
            "The index files serve as a compact table of contents for the massive underlying data.",
            "",
        ]

    # write the extended report
    Path(f"{output_dir}/extended_insights.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] extended_insights.md")


def main():
    parser = argparse.ArgumentParser(
        description="Generate advanced visualizations and extended insights."
    )
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--output-dir", default=CHART_DIR)
    args = parser.parse_args()

    ensure_dir(args.output_dir)
    ensure_dir("reports")

    print("Loading data...")
    data = load_data(args.processed_dir)

    print("\nGenerating charts:")
    chart_pipeline_summary(data["downloads"], data["indexes"], data["plans"], data["refs"], args.output_dir)
    chart_download_status(data["downloads"], args.output_dir)
    chart_entity_distribution(data["indexes"], args.output_dir)
    chart_plans_per_index(data["plans"], args.output_dir)
    chart_file_type_pie(data["refs"], args.output_dir)
    chart_url_reuse(data["refs"], args.output_dir)
    chart_network_types(data["refs"], args.output_dir)
    chart_refs_per_index(data["refs"], args.output_dir)
    chart_entity_plan_heatmap(data["indexes"], data["plans"], args.output_dir)
    chart_file_size_distribution(data["downloads"], args.output_dir)
    chart_url_sharing_network(data["refs"], data["indexes"], args.output_dir)

    print("\nGenerating extended insights:")
    generate_extended_insights(data, "reports")

    print(f"\nAll charts saved to {args.output_dir}/")
    print("Extended insights saved to reports/extended_insights.md")


if __name__ == "__main__":
    main()
