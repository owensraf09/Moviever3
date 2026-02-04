import streamlit as st
from dotenv import load_dotenv

# This was added by Alex
# 123
# Load environment variables from .env file
# Note: .env file must be saved as UTF-8 encoding (without BOM)
try:
    load_dotenv()
except UnicodeDecodeError as e:
    st.error(f"❌ Failed to load .env file due to encoding error: {e}")
    st.error("Please ensure your .env file is saved as UTF-8 encoding (without BOM).")
    st.error(
        "You can recreate it by copying .env.example to .env and adding your token."
    )
    st.stop()
except Exception as e:
    st.warning(f"Could not load .env file: {e}. Continuing without it...")

# NOTE:
# - Remove st.set_page_config from app.py when using multipage with pages/.
#   Put it ONLY in your page scripts (as you already do).

# Import functions from utils modules
from utils.data_loader import get_data
from utils.top_gems import (
    render_top_gems_previous_month_table,
    render_top_gems_previous_month_cards,
)

st.title("Moviever Film Dashboard")


st.markdown(
    """
Welcome to the **Moviever Explorer**, your gateway to discovering hidden gems and analyzing movie trends! 
This app analyses our movie database to bring you comprehensive movie data with powerful filtering and analysis tools.
"""
)


# Usage example - add this to your Streamlit page
if __name__ == "__main__":
    # Load data
    df = get_data()
    if df is not None:
        col, _ = st.columns([1, 3])

        with col:
            view_mode = st.radio("View Mode:", ["Cards", "Table"], horizontal=True)

        if view_mode == "Cards":
            render_top_gems_previous_month_cards(df)
        else:
            render_top_gems_previous_month_table(df)


st.subheader("📋 Index:")

st.markdown("#### 🏠 Film Finder- Hidden Gems Finder")
st.markdown(
    "Find high-quality, underrated movies using the Gems Score algorithm. Shows top movies with detailed info and download options."
)

st.markdown("#### 📊 Analytics - Data Dashboard")
st.markdown(
    "Visual charts and statistics about the movie dataset. Includes rating distributions, popularity trends, and year/language breakdowns."
)

st.markdown("#### 🔍 Browse All - Movie Browser")
st.markdown(
    "Search, sort, and browse all movies with table or card views. Includes pagination and flexible sorting options."
)

st.caption(
    "💡 All pages share the same sidebar filters for consistent data exploration."
)
