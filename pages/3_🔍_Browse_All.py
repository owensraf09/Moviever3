import streamlit as st
import pandas as pd
from datetime import datetime
st.set_page_config(page_title="Browse All", layout="wide", page_icon="🔍")
from home import get_data, render_sidebar_filters, filter_df
import config


# Load data FIRST - before any UI elements
# This ensures session state check happens before any rendering
df = get_data()
if df is None:
    st.stop()

st.title("🔍 Browse All Movies")
st.markdown("Browse and search through all TMDB movies")

# Sidebar filters
filters = render_sidebar_filters(df)

# Apply filters
df_filtered = filter_df(df, filters)

if len(df_filtered) == 0:
    st.warning("No movies match your filters. Adjust filters to see movies.")
    st.stop()

# Search and sort options
st.divider()
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input("🔍 Search movies by title:", "")

with col2:
    sort_by = st.selectbox("Sort by:", 
                          ["Gems Score", "Rating", "Popularity", "Vote Count", "Release Date", "Title"])

with col3:
    sort_order = st.selectbox("Order:", ["Descending", "Ascending"])

# Apply search
if search_query:
    df_display = df_filtered[df_filtered['original_title'].str.contains(search_query, case=False, na=False)]
else:
    df_display = df_filtered.copy()

# Apply sorting
sort_columns = {
    "Gems Score": "gems_score",
    "Rating": "vote_average",
    "Popularity": "popularity",
    "Vote Count": "vote_count",
    "Release Date": "release_date",
    "Title": "original_title"
}

ascending = sort_order == "Ascending"
df_display = df_display.sort_values(sort_columns[sort_by], ascending=ascending)

# Format for display
df_display = df_display.copy()
df_display['release_date_str'] = df_display['release_date'].dt.strftime('%Y-%m-%d').fillna('N/A')
# genres_str is already created in prepare_df(), no need to recreate

# Display options
st.divider()
col1, col2 = st.columns([1, 3])

with col1:
    view_mode = st.radio("View Mode:", ["Table", "Cards"], horizontal=True)
    items_per_page = st.slider("Items per page:", 10, 100, 25, 10)

# Pagination
total_items = len(df_display)
total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    page_num = st.number_input(f"Page (1-{total_pages}):", min_value=1, max_value=total_pages, 
                              value=st.session_state.current_page, key="page_input")
    st.session_state.current_page = page_num

start_idx = (page_num - 1) * items_per_page
end_idx = min(start_idx + items_per_page, total_items)
df_page = df_display.iloc[start_idx:end_idx]

st.info(f"Showing {start_idx + 1}-{end_idx} of {total_items} movies")

if view_mode == "Table":
    # Table view
    display_cols = ['original_title', 'release_date_str', 'vote_average', 'vote_count', 
                   'popularity', 'original_language', 'gems_score']
    df_table = df_page[display_cols].copy()
    df_table.columns = ['Title', 'Release Date', 'Rating', 'Vote Count', 
                       'Popularity', 'Language', 'Gems Score']
    df_table['Rating'] = df_table['Rating'].round(2)
    df_table['Popularity'] = df_table['Popularity'].round(2)
    df_table['Gems Score'] = df_table['Gems Score'].round(3)
    
    st.dataframe(df_table, use_container_width=True, height=500)
else:
    # Card view
    cols = st.columns(3)
    for idx, (_, movie) in enumerate(df_page.iterrows()):
        col = cols[idx % 3]
        with col:
            with st.container():
                # Poster
                if pd.notna(movie.get('poster_path')) and movie['poster_path']:
                    poster_url = f"{config.TMDB_IMAGE_BASE_URL}{movie['poster_path']}"
                    st.image(poster_url, use_container_width=True)
                
                # Title and key info
                st.markdown(f"### {movie['original_title']}")
                st.caption(f"📅 {movie['release_date_str']} | 🌍 {movie['original_language']}")
                
                col_metrics = st.columns(3)
                with col_metrics[0]:
                    st.metric("⭐", f"{movie['vote_average']:.1f}")
                with col_metrics[1]:
                    st.metric("👥", f"{int(movie['vote_count']):,}")
                with col_metrics[2]:
                    st.metric("🔥", f"{movie['popularity']:.1f}")
                
                st.caption(f"💎 Gems Score: {movie['gems_score']:.3f}")
                
                if pd.notna(movie.get('overview')) and movie['overview']:
                    with st.expander("Overview"):
                        st.write(movie['overview'][:200] + "..." if len(movie['overview']) > 200 else movie['overview'])
                
                st.divider()

# Download button
st.divider()
st.download_button(
    label="📥 Download Current View as CSV",
    data=df_page.to_csv(index=False).encode('utf-8'),
    file_name=f"movies_browse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)
