import streamlit as st

st.set_page_config(page_title="Hidden Gems", layout="wide", page_icon="🏠")

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.data_processing import filter_df
from utils.rendering import render_metrics, render_table_and_details


# Load data FIRST - before any UI elements
# This ensures session state check happens before any rendering
df = get_data()
if df is None:
    st.stop()

st.title("🎬 TMDB Hidden Gems Finder")
st.markdown("Discover movies with high ratings but low popularity - the hidden gems!")

# Sidebar filters
filters = render_sidebar_filters(df)

# Apply filters
df_filtered = filter_df(df, filters)

# Main content
st.divider()

# Metrics
render_metrics(df, df_filtered)

st.divider()

# Table and details
render_table_and_details(df_filtered)
