# Insta_Hashtag_Analyzer

A Streamlit dashboard that scrapes Instagram hashtag posts using Apify actors and provides post-level drilldowns and visualizations.

## Features
- Scrape posts for any hashtag via Apify's Instagram Hashtag Scraper actor.
- Upload an existing CSV exported from Apify.
- Preview images and captions for individual posts.
- Post-level visualizations: likes vs comments, engagement rate (if followers available).
- Word cloud of captions (requires `wordcloud` package).
- Time-series of daily engagement (if timestamps exist).
- Top posts comparison and CSV download.

## Setup (local)
1. Clone repo and `cd` into project folder.
2. Create a virtual environment and activate:
   ```bash
   python3 -m venv ig_scraper_env
   source ig_scraper_env/bin/activate
