# Insta Hashtag Analyzer (Streamlit)

A **Streamlit dashboard** that scrapes Instagram hashtag posts (via **Apify actors**) and provides post-level drilldowns and visualizations.

---

## ✨ Features
- 🔍 Scrape posts for any hashtag using **Apify’s Instagram Hashtag Scraper actor**  
- 📂 Upload an existing CSV exported from Apify  
- 🖼️ Preview images and captions for individual posts  
- 📊 Post-level visualizations:
  - Likes vs comments  
  - Engagement rate (if followers available)  
- ☁️ Word cloud of captions *(requires `wordcloud` package)*  
- 📆 Time-series of daily engagement (if timestamps exist)  
- 🏆 Top posts comparison + CSV download  

---

## 🚀 Live Demo
Try it here: [instahashtaganalyzer.streamlit.app](https://instahashtaganalyzer.streamlit.app/)

---

## 🧪 Quick start (local)

Clone the repo and set up locally:

```bash
git clone https://github.com/<your-username>/Insta_Hashtag_Analyzer.git
cd Insta_Hashtag_Analyzer

# Create and activate virtual env
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Run the app
streamlit run app.py
