import os
from dotenv import load_dotenv
import streamlit as st
from apify_client import ApifyClient
import pandas as pd

# -----------------------------
# Load environment variables
# -----------------------------
# First, try to load from .env (for local use)
load_dotenv()

# Then, try Streamlit secrets (for Streamlit Cloud)
APIFY_TOKEN = os.getenv("APIFY_TOKEN") or st.secrets.get("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN not found. Please set it in .env (local) or in Streamlit Secrets (Cloud).")

# Initialize Apify client
client = ApifyClient(APIFY_TOKEN)

# -----------------------------
# Streamlit app
# -----------------------------
st.set_page_config(page_title="Instagram Hashtag Analyzer", layout="wide")
st.title("📸 Instagram Hashtag Analyzer")

# Input search bar
hashtag = st.text_input("Enter Instagram Hashtag (without #):")

# Slider for number of posts to fetch
max_posts = st.slider("Number of posts to fetch", min_value=10, max_value=100, value=50, step=10)

if st.button("Search"):
    if hashtag:
        st.info(f"Fetching posts for #{hashtag}... This may take a few seconds.")

        try:
            # Apify actor ID for Instagram hashtag scraper
            actor_id = "apify/instagram-hashtag-scraper"

            run_input = {
                "hashtags": [hashtag],
                "resultsLimit": max_posts
            }

            # Run the actor
            run = client.actor(actor_id).call(run_input=run_input)

            # Get dataset items
            dataset_id = run["defaultDatasetId"]
            dataset = client.dataset(dataset_id)
            items = list(dataset.list_items().items)

            if not items:
                st.warning("No posts found.")
            else:
                st.success(f"Found {len(items)} posts!")
                df = pd.DataFrame(items)

                # -----------------------------
                # Show summary charts
                # -----------------------------
                st.subheader("📊 Posts Engagement Summary")

                if "likeCount" in df.columns and "commentCount" in df.columns:
                    st.bar_chart(df[["likeCount", "commentCount"]].head(20))

                # -----------------------------
                # Display top posts images
                # -----------------------------
                st.subheader("🖼 Top Posts Preview")
                if "imageUrl" in df.columns:
                    top_images = df["imageUrl"].dropna().head(10)
                    cols = st.columns(5)
                    for idx, img_url in enumerate(top_images):
                        cols[idx % 5].image(img_url, use_column_width=True)

                # -----------------------------
                # Display full dataframe
                # -----------------------------
                st.subheader("📋 Full Posts Data")
                st.dataframe(df)

                # CSV download
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", data=csv, file_name=f"{hashtag}_posts.csv")

        except Exception as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter a hashtag!")
