import os
from dotenv import load_dotenv
import streamlit as st
from apify_client import ApifyClient
import pandas as pd

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
                st.subheader("� Posts Engagement Summary")
                if "likesCount" in filtered_df.columns and "commentsCount" in filtered_df.columns:
                    st.bar_chart(filtered_df[["likesCount", "commentsCount"]].head(20))

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
