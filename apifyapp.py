# apifyapp.py
import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from apify_client import ApifyClient
import matplotlib.pyplot as plt
from typing import Optional
from collections import Counter
import numpy as np

# Try importing WordCloud; if unavailable we'll show an install hint
try:
    from wordcloud import WordCloud, STOPWORDS
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

# -----------------------------
# Config / env
# -----------------------------
load_dotenv()
st.set_page_config(page_title="Instagram Hashtag Analyzer", layout="wide")

APIFY_TOKEN = os.getenv("APIFY_TOKEN") or st.secrets.get("APIFY_TOKEN")

# -----------------------------
# Helper Class
# -----------------------------
class InstagramAnalyzer:
    def __init__(self, apify_token: str):
        if not apify_token:
            raise ValueError("APIFY_TOKEN not found. Set it in .env (local) or Streamlit Secrets (Cloud).")
        self.client = ApifyClient(apify_token)

    def run_hashtag_actor(self, hashtag: str, results_limit: int = 50) -> pd.DataFrame:
        actor_id = "apify/instagram-hashtag-scraper"
        run_input = {"hashtags": [hashtag], "resultsLimit": results_limit}
        run = self.client.actor(actor_id).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError("Actor ran but no dataset was produced.")
        dataset = self.client.dataset(dataset_id)
        items = list(dataset.list_items().items)
        df = pd.DataFrame(items)
        return df

    @staticmethod
    def load_csv(file) -> pd.DataFrame:
        return pd.read_csv(file)

    @staticmethod
    def candidate_image_url(row: pd.Series) -> Optional[str]:
        possible_keys = [
            "imageUrl", "displayUrl", "image_urls", "imageUrls", "imageUrlList",
            "thumbnailUrl", "thumbnail_urls", "picture"
        ]
        for k in possible_keys:
            if k in row.index and pd.notna(row[k]) and str(row[k]).strip() != "":
                val = row[k]
                if isinstance(val, list) and len(val) > 0:
                    return val[0]
                return str(val)
        return None

    @staticmethod
    def safe_int(val) -> int:
        try:
            return int(val)
        except Exception:
            try:
                return int(float(val))
            except Exception:
                return 0

    @staticmethod
    def engagement_rate(row: pd.Series) -> Optional[float]:
        follower_keys = ["followers", "followerCount", "follower_count", "ownerFollowerCount", "owner_followers"]
        followers = None
        for k in follower_keys:
            if k in row.index and pd.notna(row[k]):
                try:
                    followers = int(row[k])
                    break
                except Exception:
                    continue
        if followers and followers > 0:
            likes = InstagramAnalyzer.safe_int(row.get("likeCount", 0))
            comments = InstagramAnalyzer.safe_int(row.get("commentCount", 0))
            return (likes + comments) / followers
        return None

    @staticmethod
    def plot_post_engagement(row: pd.Series):
        likes = InstagramAnalyzer.safe_int(row.get("likeCount", 0))
        comments = InstagramAnalyzer.safe_int(row.get("commentCount", 0))
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.bar(["Likes", "Comments"], [likes, comments])
        ax.set_title("Post Engagement")
        ax.set_ylabel("Count")
        ax.grid(axis="y", linestyle="--", linewidth=0.4)
        st.pyplot(fig)

    @staticmethod
    def plot_top_posts(df: pd.DataFrame, metric: str = "likeCount", top_n: int = 10):
        if metric not in df.columns:
            st.info(f"Metric '{metric}' not found in dataset.")
            return
        df["_metric_"] = df[metric].apply(InstagramAnalyzer.safe_int)
        top = df.nlargest(top_n, "_metric_")[["_metric_"]].copy()
        labels = []
        for idx in top.index:
            row = df.loc[idx]
            uname = row.get("username") or row.get("owner_username") or ""
            pid = str(row.get("id") or row.get("postId") or "")[:10]
            labels.append(f"{uname}\n{pid}")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(range(len(top)), top["_metric_"])
        ax.set_xticks(range(len(top)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title(f"Top {top_n} posts by {metric}")
        ax.set_ylabel(metric)
        ax.grid(axis="y", linestyle="--", linewidth=0.4)
        st.pyplot(fig)

    @staticmethod
    def plot_time_series(df: pd.DataFrame):
        # Try find a timestamp-like column
        ts_keys = ["timestamp", "created_time", "created_at", "datetime", "date"]
        found = None
        for k in ts_keys:
            if k in df.columns:
                found = k
                break
        if not found:
            st.info("No timestamp column found to plot time series.")
            return

        # Parse datetimes
        try:
            df["_ts_"] = pd.to_datetime(df[found], errors="coerce")
        except Exception:
            st.info("Could not parse timestamps for time series.")
            return

        df_time = df.dropna(subset=["_ts_"]).copy()
        if df_time.empty:
            st.info("No valid timestamps to plot.")
            return

        # Aggregate daily sums for likes and comments if present
        df_time["date"] = df_time["_ts_"].dt.date
        agg = {"likeCount": "sum", "commentCount": "sum"}
        to_agg = {k: v for k, v in agg.items() if k in df_time.columns}
        if not to_agg:
            st.info("No like/comment columns available for time series.")
            return
        daily = df_time.groupby("date").agg(to_agg).reset_index()
        daily = daily.sort_values("date")
        # plot with matplotlib
        fig, ax = plt.subplots(figsize=(10, 4))
        for col in to_agg.keys():
            ax.plot(daily["date"].astype(str), daily[col], marker="o", label=col)
        ax.set_title("Time series of engagement (daily totals)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Count")
        ax.legend()
        ax.grid(axis="y", linestyle="--", linewidth=0.4)
        plt.xticks(rotation=45)
        st.pyplot(fig)

    @staticmethod
    def plot_wordcloud_from_captions(df: pd.DataFrame, max_words: int = 100):
        if not WORDCLOUD_AVAILABLE:
            st.info("WordCloud package not installed. Install with `pip install wordcloud` to enable word cloud.")
            return
        text = " ".join([str(x) for x in df.get("caption", []).dropna().astype(str).values])
        if not text.strip():
            st.info("No caption text available for word cloud.")
            return
        stopwords = set(STOPWORDS)
        wc = WordCloud(width=800, height=400, max_words=max_words, stopwords=stopwords).generate(text)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.title("📸 Insta Hashtag Analyzer — Drilldown + Word Cloud + Time Series")
    st.markdown("Use the sidebar to scrape a hashtag via Apify or upload a CSV. Select a post to see post-level metrics, word cloud of captions, and time series of engagement.")

    st.sidebar.header("Data source")
    source = st.sidebar.radio("Choose data source", ("Scrape hashtag (Apify)", "Upload CSV"))

    analyzer = None
    df = None

    if source == "Scrape hashtag (Apify)":
        hashtag = st.sidebar.text_input("Hashtag (without #)", value="")
        results_limit = st.sidebar.slider("Max posts to fetch", min_value=10, max_value=200, value=50, step=10)
        if st.sidebar.button("Run scrape"):
            try:
                if not APIFY_TOKEN:
                    st.error("APIFY_TOKEN not set. Add it to .env (local) or Streamlit Secrets (Cloud).")
                    st.stop()
                analyzer = InstagramAnalyzer(APIFY_TOKEN)
                with st.spinner("Running Apify actor and fetching data..."):
                    df = analyzer.run_hashtag_actor(hashtag=hashtag, results_limit=results_limit)
                st.success(f"Scrape complete — {len(df)} items fetched.")
                csv = df.to_csv(index=False)
                st.sidebar.download_button("Download scraped CSV", data=csv, file_name=f"{hashtag}_posts.csv")
            except Exception as e:
                st.error(f"Error running actor: {e}")
    else:
        uploaded_file = st.sidebar.file_uploader("Upload CSV (exported from this app or Apify)", type=["csv"])
        if uploaded_file is not None:
            try:
                df = InstagramAnalyzer.load_csv(uploaded_file)
                st.success(f"Loaded CSV — {len(df)} rows.")
            except Exception as e:
                st.error(f"Could not load CSV: {e}")

    if df is None:
        st.info("No data loaded yet. Scrape a hashtag or upload a CSV to begin.")
        return

    df = df.reset_index(drop=True)
    display_cols = ["id", "username", "caption", "timestamp", "likeCount", "commentCount"]
    available_display_cols = [c for c in display_cols if c in df.columns]

    st.subheader("Dataset preview (top rows)")
    st.dataframe(df[available_display_cols].head(50))

    st.subheader("Select a post to analyze")
    def make_label(idx, row):
        uname = row.get("username") or row.get("owner_username") or "unknown_user"
        pid = str(row.get("id") or row.get("postId") or idx)
        cap = str(row.get("caption") or "")
        cap_short = (cap[:80] + "...") if len(cap) > 80 else cap
        tl = row.get("timestamp") or ""
        return f"{idx} | {uname} | {cap_short} | {tl}"

    options = [make_label(i, df.loc[i]) for i in df.index]
    selected = st.selectbox("Choose post", options=options, index=0)
    selected_idx = int(selected.split(" | ", 1)[0])
    post_row = df.loc[selected_idx]

    st.markdown("### Post preview")
    image_url = InstagramAnalyzer.candidate_image_url(post_row)
    if image_url:
        st.image(image_url, use_column_width=True)
    else:
        st.info("No image preview available for this post.")

    st.markdown("**Caption**")
    st.write(post_row.get("caption", ""))

    st.markdown("**Metadata**")
    metadata = {
        "Post ID": post_row.get("id") or post_row.get("postId"),
        "Username": post_row.get("username") or post_row.get("owner_username"),
        "Timestamp": post_row.get("timestamp"),
        "Likes": post_row.get("likeCount"),
        "Comments": post_row.get("commentCount")
    }
    st.json({k: v for k, v in metadata.items() if v is not None})

    st.markdown("### Engagement visualizations")
    InstagramAnalyzer.plot_post_engagement(post_row)
    erate = InstagramAnalyzer.engagement_rate(post_row)
    if erate is not None:
        st.write(f"Engagement rate (likes+comments / followers): **{erate:.4%}**")
    else:
        st.info("Follower count not available — engagement rate can't be computed.")

    st.markdown("### Word cloud (captions)")
    if WORDCLOUD_AVAILABLE:
        InstagramAnalyzer.plot_wordcloud_from_captions(df)
    else:
        st.info("To see a word cloud, install the `wordcloud` package: `pip install wordcloud`")

    st.markdown("### Time series of engagement (if timestamps exist)")
    InstagramAnalyzer.plot_time_series(df)

    st.markdown("### Top posts comparison")
    metric_options = [c for c in ["likeCount", "commentCount"] if c in df.columns]
    if metric_options:
        metric = st.selectbox("Metric for ranking", options=metric_options, index=0)
        top_n = st.slider("Top N posts to show", min_value=3, max_value=20, value=8)
        InstagramAnalyzer.plot_top_posts(df, metric=metric, top_n=top_n)
    else:
        st.info("No like/comment columns available for top-post comparison.")

    csv_all = df.to_csv(index=False)
    st.download_button("Download full dataset CSV", data=csv_all, file_name="instagram_posts_full.csv")


if __name__ == "__main__":
    main()
