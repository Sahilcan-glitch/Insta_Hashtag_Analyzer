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

# Input search bar
hashtag = st.text_input("Enter Instagram Hashtag (without #):")

# Slider for number of posts to fetch
max_posts = st.slider("Number of posts to fetch", min_value=10, max_value=100, value=50, step=10)

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
                top_images = df.head(10)["imageUrl"].dropna() if "imageUrl" in df.columns else []

                cols = st.columns(5)
                for idx, img_url in enumerate(top_images):
                    cols[idx % 5].image(img_url, use_column_width=True)

                # -----------------------------
                # Display full dataframe
                # -----------------------------
                st.subheader("📋 Full Posts Data")
                st.dataframe(df)

                # CSV download
                    # Filter DataFrame to only required columns
                    columns_to_keep = [
                        "id", "shortCode", "caption", "hashtags", "mentions", "url",
                        "likeCount", "commentCount", "timestamp", "ownerUsername", "productType"
                    ]
                    filtered_df = df[[col for col in columns_to_keep if col in df.columns]]
                    csv = filtered_df.to_csv(index=False)
                    st.download_button("Download CSV", data=csv, file_name=f"{hashtag}_posts.csv")

        except Exception as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter a hashtag!")
