import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import os

# Load Apify token from environment variable
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    st.error("Please set your APIFY_TOKEN as an environment variable!")
    st.stop()

# Initialize Apify client
client = ApifyClient(APIFY_TOKEN)

st.title("Instagram Hashtag Analyzer")

# Input search bar
hashtag = st.text_input("Enter Instagram Hashtag (without #):")

max_posts = st.slider("Number of posts to fetch", min_value=10, max_value=100, value=50, step=10)

if st.button("Search"):
    if hashtag:
        st.info(f"Fetching posts for #{hashtag}... This may take a few seconds.")

        try:
            run_input = {
                "hashtags": [hashtag],
                "resultsLimit": max_posts
            }

            # Replace with the correct Apify Instagram scraper actor ID
            actor_id = "apify/instagram-hashtag-scraper"
            
            run = client.actor(actor_id).call(run_input=run_input)

            # Get dataset items
            dataset_id = run["defaultDatasetId"]
            dataset = client.dataset(dataset_id)
            items = list(dataset.list_items().items)

            if items:
                st.success(f"Found {len(items)} posts!")
                df = pd.DataFrame(items)
                st.dataframe(df)

                # CSV download
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", data=csv, file_name=f"{hashtag}_posts.csv")

            else:
                st.warning("No posts found.")

        except Exception as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please enter a hashtag!")
