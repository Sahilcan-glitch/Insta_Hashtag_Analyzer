import os
from dotenv import load_dotenv
import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import numpy as np
import plotly.express as px

# -----------------------------
# Load .env and get API token
# -----------------------------
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN not found. Please set it in the .env file.")

# Initialize Apify client
client = ApifyClient(APIFY_TOKEN)

# -----------------------------
# Streamlit app
# -----------------------------
st.set_page_config(page_title="Instagram Hashtag Analyzer", layout="wide")
st.title("📸 Instagram Hashtag Analyzer")


# Helper: Render Reach & Impressions pie charts by content type
def render_reach_impressions_pies(df_in: pd.DataFrame, type_col: str = "productType") -> None:
    if df_in is None or df_in.empty:
        return
    work = df_in.copy()
    # Ensure numeric columns exist and are numeric
    for col in ["likesCount", "commentsCount", "videoViewCount", "playsCount", "impressions", "reach"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0)
        else:
            work[col] = 0
    work["views_count"] = work[["videoViewCount", "playsCount"]].max(axis=1)
    # Prefer provided impressions/reach; fallback to interactions + views
    work["impressions_proxy"] = work[["impressions", "reach"]].max(axis=1)
    work["impressions_proxy"] = work["impressions_proxy"].replace(0, np.nan)
    fallback = work["likesCount"] + work["commentsCount"] + work["views_count"]
    work["reach_estimate"] = work["impressions_proxy"].fillna(fallback)
    if type_col not in work.columns:
        return
    grouped = work.groupby(type_col).agg(
        Reach=("reach_estimate", "sum"),
        Impressions=("impressions_proxy", "sum"),
    ).reset_index()
    grouped["Reach"] = pd.to_numeric(grouped["Reach"], errors="coerce").replace(0, np.nan)
    grouped["Impressions"] = pd.to_numeric(grouped["Impressions"], errors="coerce").replace(0, np.nan)
    if grouped[["Reach", "Impressions"]].fillna(0).sum().sum() == 0:
        st.info("No reach or impressions data available to visualize.")
        return
    col_a, col_b = st.columns(2)
    with col_a:
        reach_df = grouped[[type_col, "Reach"]].dropna(subset=["Reach"]) if "Reach" in grouped.columns else pd.DataFrame()
        if not reach_df.empty and reach_df["Reach"].sum() > 0:
            fig = px.pie(reach_df, names=type_col, values="Reach", hole=0.5,
                         color_discrete_sequence=px.colors.sequential.Purples)
            fig.update_traces(textposition="inside", texttemplate="%{label}<br>%{percent:.1%}")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Share of Estimated Reach by content type.")
    with col_b:
        imp_df = grouped[[type_col, "Impressions"]].dropna(subset=["Impressions"]) if "Impressions" in grouped.columns else pd.DataFrame()
        if not imp_df.empty and imp_df["Impressions"].sum() > 0:
            fig2 = px.pie(imp_df, names=type_col, values="Impressions", hole=0.5,
                          color_discrete_sequence=px.colors.sequential.Magma)
            fig2.update_traces(textposition="inside", texttemplate="%{label}<br>%{percent:.1%}")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Share of Impressions (proxy) by content type.")


# Tabs for search mode
tab1, tab2 = st.tabs(["Search by Hashtag", "Search by Owner Username"])

with tab1:
    hashtag = st.text_input("Enter Instagram Hashtag (without #):")
    max_posts = st.slider("Number of posts to fetch", min_value=10, max_value=100, value=50, step=10, key="hashtag_slider")
    owner_username_filter = st.text_input("Lock on ownerUsername (optional):", key="hashtag_owner_filter")
    if st.button("Search by Hashtag"):
        if hashtag:
            st.info(f"Fetching posts for #{hashtag}... This may take a few seconds.")
            try:
                actor_id = "apify/instagram-hashtag-scraper"
                run_input = {
                    "hashtags": [hashtag],
                    "resultsLimit": max_posts
                }
                client = ApifyClient(APIFY_TOKEN)
                run = client.actor(actor_id).call(run_input=run_input)
                dataset_id = run["defaultDatasetId"]
                dataset = client.dataset(dataset_id)
                items = list(dataset.list_items().items)
                if not items:
                    st.warning("No posts found.")
                else:
                    st.success(f"Found {len(items)} posts!")
                    df = pd.DataFrame(items)
                    # Filter by ownerUsername if specified
                    if owner_username_filter:
                        if "ownerUsername" in df.columns:
                            df = df[df["ownerUsername"].astype(str).str.lower() == owner_username_filter.strip().lower()]
                    # ...existing code for filtering columns, mapping productType, truncating caption, displaying and exporting...
                    columns_to_keep = [
                        "caption", "ownerUsername", "likesCount", "commentsCount", "url", "productType",
                        "mentions", "taggedUsers", "hashtags"
                    ]
                    filtered_df = df[[col for col in columns_to_keep if col in df.columns]].copy()
                    if "caption" in filtered_df.columns:
                        filtered_df["caption"] = filtered_df["caption"].astype(str).str.slice(0, 125)
                    product_type_map = {
                        "feed": "Feed Post (Photo/Video)",
                        "feed_single": "Feed Post (Photo/Video)",
                        "feed_video": "Feed Post (Photo/Video)",
                        "carousel_container": "Post (Multiple Images/Videos)",
                        "reels": "Reel (Short Video)",
                        "clips": "Reel (Short Video)",
                        "story": "Story (24h Post)",
                        "igtv": "IGTV (Long Video, Legacy)",
                        "live": "Live Video",
                        "ad": "Sponsored Post",
                        "sponsored": "Sponsored Post",
                        "shopping": "Shoppable Post",
                        "product_tag": "Shoppable Post",
                        "guide": "Guide (Curated Content)",
                        "carousel_child": "Carousel Slide (Part of Post)"
                    }
                    if "productType" in filtered_df.columns:
                        filtered_df["productType"] = filtered_df["productType"].map(
                            lambda x: product_type_map.get(str(x), "Other")
                        )
                    st.subheader("🍰 Reach & Impressions Breakdown")
                    render_reach_impressions_pies(filtered_df)
                    st.subheader("📋 Filtered Posts Data")
                    st.dataframe(filtered_df)
                    csv = filtered_df.to_csv(index=False)
                    st.download_button("Download CSV", data=csv, file_name=f"{hashtag}_posts.csv")
            except Exception as e:
                st.error(f"Error fetching data: {e}")
        else:
            st.warning("Please enter a hashtag!")

with tab2:
    owner_username = st.text_input("Enter Instagram Owner Username:")
    max_posts_owner = st.slider("Number of posts to fetch", min_value=10, max_value=100, value=50, step=10, key="owner_slider")
    if st.button("Search by Owner Username"):
        if owner_username:
            st.info(f"Fetching posts for @{owner_username}... This may take a few seconds.")
            try:
                actor_id = "apify/instagram-post-scraper"
                run_input = {
                    "username": [owner_username],
                    "resultsLimit": max_posts_owner
                }
                client = ApifyClient(APIFY_TOKEN)
                run = client.actor(actor_id).call(run_input=run_input)
                dataset_id = run["defaultDatasetId"]
                dataset = client.dataset(dataset_id)
                items = list(dataset.list_items().items)
                if not items:
                    st.warning("No posts found.")
                else:
                    st.success(f"Found {len(items)} posts!")
                    df = pd.DataFrame(items)
                    columns_to_keep = [
                        "caption", "commentsCount", "firstComment", "hashtags", "lastComment",
                        "likesCount", "mentions", "ownerUsername", "productType", "timestamp",
                        "type", "url", "videoViewCount"
                    ]
                    filtered_df = df[[col for col in columns_to_keep if col in df.columns]].copy()
                    if "caption" in filtered_df.columns:
                        filtered_df["caption"] = filtered_df["caption"].astype(str).str.slice(0, 125)
                    product_type_map = {
                        "feed": "Feed Post (Photo/Video)",
                        "feed_single": "Feed Post (Photo/Video)",
                        "feed_video": "Feed Post (Photo/Video)",
                        "carousel_container": "Post (Multiple Images/Videos)",
                        "reels": "Reel (Short Video)",
                        "clips": "Reel (Short Video)",
                        "story": "Story (24h Post)",
                        "igtv": "IGTV (Long Video, Legacy)",
                        "live": "Live Video",
                        "ad": "Sponsored Post",
                        "sponsored": "Sponsored Post",
                        "shopping": "Shoppable Post",
                        "product_tag": "Shoppable Post",
                        "guide": "Guide (Curated Content)",
                        "carousel_child": "Carousel Slide (Part of Post)"
                    }
                    if "productType" in filtered_df.columns:
                        filtered_df["productType"] = filtered_df["productType"].map(
                            lambda x: product_type_map.get(str(x), "Other")
                        )
                    st.subheader("🍰 Reach & Impressions Breakdown")
                    render_reach_impressions_pies(filtered_df)
                    st.subheader("📋 Filtered Posts Data")
                    st.dataframe(filtered_df)
                    csv = filtered_df.to_csv(index=False)
                    st.download_button("Download CSV", data=csv, file_name=f"{owner_username}_posts.csv")
            except Exception as e:
                st.error(f"Error fetching data: {e}")
        else:
            st.warning("Please enter an owner username!")


if st.button("Search"):
    if hashtag:
        st.info(f"Fetching posts for #{hashtag}... This may take a few seconds.")

        try:
            actor_id = "apify/instagram-hashtag-scraper"

            run_input = {
                "hashtags": [hashtag],
                "resultsLimit": max_posts
            }

            run = client.actor(actor_id).call(run_input=run_input)

            dataset_id = run["defaultDatasetId"]
            dataset = client.dataset(dataset_id)
            items = list(dataset.list_items().items)

            if not items:
                st.warning("No posts found.")
            else:
                st.success(f"Found {len(items)} posts!")
                df = pd.DataFrame(items)

                # Filter by ownerUsername if specified
                if owner_username_filter:
                    if "ownerUsername" in df.columns:
                        df = df[df["ownerUsername"].astype(str).str.lower() == owner_username_filter.strip().lower()]

                # Only keep and reorder specified columns
                columns_to_keep = [
                    "ownerUsername", "caption", "likesCount", "commentsCount", "url",  "timestamp", "productType",
                    "mentions", "firstComment", "latestComments", "hashtags"
                ]
                filtered_df = df[[col for col in columns_to_keep if col in df.columns]].copy()

                # Truncate caption to 125 characters
                if "caption" in filtered_df.columns:
                    filtered_df["caption"] = filtered_df["caption"].astype(str).str.slice(0, 125)

                # Map productType values to user-friendly labels
                product_type_map = {
                    "feed": "Feed Post (Photo/Video)",
                    "feed_single": "Feed Post (Photo/Video)",
                    "feed_video": "Feed Post (Photo/Video)",
                    "carousel_container": "Post (Multiple Images/Videos)",
                    "reels": "Reel (Short Video)",
                    "clips": "Reel (Short Video)",
                    "story": "Story (24h Post)",
                    "igtv": "IGTV (Long Video, Legacy)",
                    "live": "Live Video",
                    "ad": "Sponsored Post",
                    "sponsored": "Sponsored Post",
                    "shopping": "Shoppable Post",
                    "product_tag": "Shoppable Post",
                    "guide": "Guide (Curated Content)",
                    "carousel_child": "Carousel Slide (Part of Post)"
                }
                if "productType" in filtered_df.columns:
                    filtered_df["productType"] = filtered_df["productType"].map(
                        lambda x: product_type_map.get(str(x), "Other")
                    )

                # -----------------------------
                # Show summary charts
                # -----------------------------
                st.subheader("📊 Posts Engagement Summary")
                if "likesCount" in filtered_df.columns and "commentsCount" in filtered_df.columns:
                    st.bar_chart(filtered_df[["likesCount", "commentsCount"]].head(20))

                st.subheader("🍰 Reach & Impressions Breakdown")
                render_reach_impressions_pies(filtered_df)

                # -----------------------------
                # Display full dataframe (only selected columns)
                # -----------------------------
                st.subheader("📋 Filtered Posts Data")
                st.dataframe(filtered_df)

                # CSV download (only selected columns)
                csv = filtered_df.to_csv(index=False)
                st.download_button("Download CSV", data=csv, file_name=f"{hashtag}_posts.csv")

        except Exception as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter a hashtag!")
