import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from dotenv import load_dotenv
import config

# This was added by Alex
#123
# Load environment variables from .env file
# Note: .env file must be saved as UTF-8 encoding (without BOM)
try:
    load_dotenv()
except UnicodeDecodeError as e:
    st.error(f"❌ Failed to load .env file due to encoding error: {e}")
    st.error("Please ensure your .env file is saved as UTF-8 encoding (without BOM).")
    st.error("You can recreate it by copying .env.example to .env and adding your token.")
    st.stop()
except Exception as e:
    st.warning(f"Could not load .env file: {e}. Continuing without it...")

# NOTE:
# - Remove st.set_page_config from app.py when using multipage with pages/.
#   Put it ONLY in your page scripts (as you already do).

# Load TMDB Bearer Token from environment variable
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")
if not TMDB_BEARER_TOKEN:
    st.error("❌ TMDB_BEARER_TOKEN not found in environment variables. Please create a .env file with your token.")
    st.stop()

# Ensure token starts with "Bearer " prefix
if not TMDB_BEARER_TOKEN.startswith("Bearer "):
    TMDB_BEARER_TOKEN = f"Bearer {TMDB_BEARER_TOKEN}"


# -----------------------------
# Genre lookup
# -----------------------------

@st.cache_data(ttl=config.GENRE_CACHE_TTL)
def fetch_genre_map() -> dict[int, str]:
    """
    Fetch genre ID to name mapping from TMDB.
    Returns dict mapping genre_id -> genre_name.
    Unknown IDs will map to "Unknown".
    """
    headers = {
        "accept": "application/json",
        "Authorization": TMDB_BEARER_TOKEN,
    }
    
    try:
        response = requests.get(
            config.TMDB_GENRE_URL,
            headers=headers,
            params={"language": "en-US"},
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        
        # Build mapping: {genre_id: genre_name}
        genre_map = {genre["id"]: genre["name"] for genre in data.get("genres", [])}
        return genre_map
    except Exception as e:
        st.warning(f"Failed to fetch genre map: {e}. Using empty map.")
        return {}


# -----------------------------
# TMDB fetching (resumable)
# -----------------------------

@st.cache_data(ttl=config.TMDB_CACHE_TTL)
def fetch_tmdb_page(
    page: int,
    sort_by: str = "popularity.desc",
    language: str = "en-US",
    include_adult: bool = False,
) -> dict:
    """
    Fetch a single TMDB page. Cached per-page, so multipage reruns won't restart from scratch.
    Returns JSON dict. If rate limited, returns {"_rate_limited": True}.
    """
    headers = {
        "accept": "application/json",
        "Authorization": TMDB_BEARER_TOKEN,
        "accept-encoding": "gzip",
    }
    params = {
        "include_adult": str(include_adult).lower(),
        "language": language,
        "sort_by": sort_by,
        "page": page,
        "primary_release_date.gte": f"{config.MIN_YEAR}-01-01",
        "primary_release_date.lte": f"{config.MAX_YEAR}-12-31",
        "vote_average.gte": config.MIN_VOTE_AVERAGE,
        "vote_count.gte": config.MIN_VOTE_COUNT,
    }

    r = requests.get(config.TMDB_BASE_URL, headers=headers, params=params, timeout=20)

    if r.status_code == 429:
        return {"_rate_limited": True}

    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=config.TMDB_CACHE_TTL)
def _fetch_tmdb_pages_cached(max_pages: int = config.MAX_TMDB_PAGES) -> pd.DataFrame:
    """
    Cached TMDB fetcher: fetches all pages (up to max_pages) and returns one row per movie.
    Uses per-page cached fetches so it is resilient to Streamlit reruns.
    """
    all_movies = []
    total_pages_known = None

    backoff = 1.0
    backoff_max = 10.0

    # We still iterate pages sequentially, but each page is cached independently.
    for page in range(1, max_pages + 1):
        while True:
            data = fetch_tmdb_page(page)

            if isinstance(data, dict) and data.get("_rate_limited"):
                time.sleep(backoff)
                backoff = min(backoff * 2, backoff_max)
                continue

            backoff = 1.0
            break

        if total_pages_known is None:
            total_pages_known = min(data.get("total_pages", max_pages), max_pages)

        movies = data.get("results", [])
        if not movies:
            break

        all_movies.extend(movies)

        if page >= total_pages_known:
            break

    if not all_movies:
        raise RuntimeError("No movies fetched. Please check your TMDB token / connection.")

    return pd.DataFrame(all_movies)


def fetch_tmdb_all_pages(max_pages: int = config.MAX_TMDB_PAGES) -> pd.DataFrame:
    """Public fetch function."""
    return _fetch_tmdb_pages_cached(max_pages=max_pages)


# -----------------------------
# Data prep + filtering
# -----------------------------

def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, add year, add gems_score, map genre IDs to names."""
    df = df.copy()

    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["year"] = df["release_date"].dt.year

    df["gems_score"] = (df["vote_average"] * np.log10(df["vote_count"] + 1)) / (df["popularity"] + 1)
    df["gems_score"] = df["gems_score"].fillna(0)

    # Map genre IDs to genre names
    genre_map = fetch_genre_map()
    
    def map_genre_ids(genre_ids):
        """Convert list of genre IDs to list of genre names."""
        if not isinstance(genre_ids, list):
            return []
        return [genre_map.get(gid, "Unknown") for gid in genre_ids]
    
    # Add genres column (list of genre names)
    df["genres"] = df["genre_ids"].apply(map_genre_ids)
    
    # Add genres_str column (comma-separated string)
    df["genres_str"] = df["genres"].apply(lambda x: ", ".join(x) if x else "Unknown")

    return df


def filter_df(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Filter DataFrame based on user filters."""
    df_filtered = df.copy()

    if not filters["adult"]:
        df_filtered = df_filtered[df_filtered["adult"] == False]

    # Filter by genre (check if selected genre is in the genres list)
    if filters["genre"] != "All":
        if "genres" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["genres"].apply(
                lambda x: filters["genre"] in x if isinstance(x, list) else False
            )]
        else:
            # Fallback: filter by genres_str if genres column doesn't exist
            df_filtered = df_filtered[df_filtered["genres_str"].str.contains(filters["genre"], case=False, na=False)]

    df_filtered = df_filtered[df_filtered["vote_average"] >= filters["min_rating"]]
    df_filtered = df_filtered[df_filtered["popularity"] <= filters["max_popularity"]]
    df_filtered = df_filtered[df_filtered["vote_count"] >= filters["min_vote_count"]]

    if filters["min_year"] is not None:
        df_filtered = df_filtered[df_filtered["year"] >= filters["min_year"]]
    if filters["max_year"] is not None:
        df_filtered = df_filtered[df_filtered["year"] <= filters["max_year"]]

    if not filters["include_missing_dates"]:
        df_filtered = df_filtered[df_filtered["release_date"].notna()]

    return df_filtered


# -----------------------------
# Rendering helpers
# -----------------------------

def render_metrics(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Movies Loaded", len(df_all))

    with col2:
        st.metric("Hidden Gems Count", len(df_filtered))

    with col3:
        median_rating = df_filtered["vote_average"].median() if len(df_filtered) > 0 else 0
        st.metric("Median Rating", f"{median_rating:.2f}")

    with col4:
        median_popularity = df_filtered["popularity"].median() if len(df_filtered) > 0 else 0
        st.metric("Median Popularity", f"{median_popularity:.2f}")


def render_charts(df_filtered: pd.DataFrame) -> None:
    if len(df_filtered) == 0:
        st.info("No data to display charts.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Popularity vs Rating")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(df_filtered["popularity"], df_filtered["vote_average"], alpha=0.5)
        ax.set_xlabel("Popularity")
        ax.set_ylabel("Vote Average")
        ax.set_title("Popularity vs Vote Average")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)

    with col2:
        st.subheader("Vote Average Distribution")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(df_filtered["vote_average"].dropna(), bins=30, edgecolor="black")
        ax.set_xlabel("Vote Average")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of Vote Averages")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)


def render_table_and_details(df_filtered: pd.DataFrame) -> None:
    if len(df_filtered) == 0:
        st.info("No movies match your filters.")
        return

    df_display = df_filtered.copy()

    df_display["release_date_str"] = df_display["release_date"].dt.strftime("%Y-%m-%d").fillna("N/A")
    # genres_str is already created in prepare_df(), no need to recreate

    display_cols = [
        "original_title",
        "release_date_str",
        "vote_average",
        "vote_count",
        "popularity",
        "original_language",
        "gems_score",
    ]

    df_display = df_display.sort_values("gems_score", ascending=False)

    st.subheader("Hidden Gems Results")

    # Calculate safe slider values
    total_movies = len(df_display)
    min_slider = 10
    max_slider = max(min_slider, min(200, total_movies))  # Ensure max >= min
    default_value = min(config.DEFAULT_TOP_N_MOVIES, total_movies) if total_movies >= min_slider else total_movies
    
    # Only show slider if we have enough movies, otherwise show all
    if total_movies >= min_slider:
        top_n = st.slider(
            "Show Top N Movies",
            min_value=min_slider,
            max_value=max_slider,
            value=default_value,
            step=10,
            key="table_top_n",
        )
    else:
        # If fewer than min_slider movies, show all
        top_n = total_movies
        st.caption(f"Showing all {total_movies} movies")
    df_display_top = df_display.head(top_n)

    df_table = df_display_top[display_cols].copy()
    df_table.columns = ["Title", "Release Date", "Rating", "Vote Count", "Popularity", "Language", "Gems Score"]

    df_table["Rating"] = df_table["Rating"].round(2)
    df_table["Popularity"] = df_table["Popularity"].round(2)
    df_table["Gems Score"] = df_table["Gems Score"].round(3)

    st.dataframe(df_table, use_container_width=True, height=400)

    st.subheader("Movie Details")
    movie_titles = df_display_top["original_title"].tolist()
    selected_title = st.selectbox("Select a movie to view details:", movie_titles, key="details_select_title")

    if selected_title:
        selected_movie = df_display_top[df_display_top["original_title"] == selected_title].iloc[0]

        col1, col2 = st.columns([1, 2])

        with col1:
            if pd.notna(selected_movie.get("poster_path")) and selected_movie["poster_path"]:
                poster_url = f"{config.TMDB_IMAGE_BASE_URL}{selected_movie['poster_path']}"
                st.image(poster_url, use_container_width=True)
            else:
                st.info("No poster available")

        with col2:
            st.write(f"**Title:** {selected_movie['original_title']}")
            st.write(f"**Release Date:** {selected_movie['release_date_str']}")
            st.write(f"**Rating:** {selected_movie['vote_average']:.2f}")
            st.write(f"**Vote Count:** {int(selected_movie['vote_count'])}")
            st.write(f"**Popularity:** {selected_movie['popularity']:.2f}")
            st.write(f"**Language:** {selected_movie['original_language']}")
            st.write(f"**Gems Score:** {selected_movie['gems_score']:.3f}")
            st.write(f"**Genres:** {selected_movie.get('genres_str', 'Unknown')}")

            if pd.notna(selected_movie.get("overview")) and selected_movie["overview"]:
                st.write("**Overview:**")
                st.write(selected_movie["overview"])
            else:
                st.write("**Overview:** N/A")

    st.download_button(
        label="Download Filtered Results as CSV",
        data=df_display_top.to_csv(index=False).encode("utf-8"),
        file_name=f"hidden_gems_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


# -----------------------------
# Sidebar filters (stable across pages)
# -----------------------------

def render_sidebar_filters(df):
    """
    Multipage-safe sidebar filters:
    - Stores filter values in st.session_state["GLOBAL_FILTERS"] (one source of truth)
    - Uses page-unique widget keys so Streamlit won't reset/override when switching pages
    - No "default + session_state" warning
    """
    # --- Get a stable per-page identifier (so widget keys are unique per page) ---
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        page_id = ctx.page_script_hash if ctx and getattr(ctx, "page_script_hash", None) else "main"
    except Exception:
        page_id = "main"

    W = f"__w__{page_id}__"          # widget key prefix (page-unique)
    SKEY = "GLOBAL_FILTERS"          # global persisted values (shared across pages)

    # --- Ensure global filter store exists ---
    if SKEY not in st.session_state:
        st.session_state[SKEY] = {
            "min_rating": config.DEFAULT_MIN_RATING,
            "max_popularity": config.DEFAULT_MAX_POPULARITY,
            "min_vote_count": config.DEFAULT_MIN_VOTE_COUNT,
            "genre": "All",
            "adult": False,
            "include_missing_dates": False,
            "min_year": None,
            "max_year": None,
        }

    g = st.session_state[SKEY]

    # Year bounds from data (for initializing filter values)
    min_year_val = int(df["year"].min()) if df["year"].notna().any() else config.MIN_YEAR
    max_year_val = int(df["year"].max()) if df["year"].notna().any() else config.MAX_YEAR

    # Initialize years in global store once (use data bounds, but clamp to config range)
    if g["min_year"] is None:
        g["min_year"] = max(config.MIN_YEAR, min(min_year_val, config.MAX_YEAR))
    if g["max_year"] is None:
        g["max_year"] = min(config.MAX_YEAR, max(max_year_val, config.MIN_YEAR))

    # Clamp global year values to config range (prevents reset)
    g["min_year"] = max(config.MIN_YEAR, min(int(g["min_year"]), config.MAX_YEAR))
    g["max_year"] = max(config.MIN_YEAR, min(int(g["max_year"]), config.MAX_YEAR))
    if g["min_year"] > g["max_year"]:
        g["min_year"] = g["max_year"]

    with st.sidebar:
        st.header("🎛️ Filters")

        # Widgets use PAGE-UNIQUE keys, but DEFAULTS come from GLOBAL store
        min_rating = st.slider(
            "Min Rating", config.MIN_VOTE_AVERAGE, 10.0, value=float(g["min_rating"]), step=0.1, key=W + "min_rating"
        )
        max_popularity = st.slider(
            "Max Popularity", 0.0, 100.0, value=float(g["max_popularity"]), step=1.0, key=W + "max_popularity"
        )
        min_vote_count = st.slider(
            "Min Vote Count", config.MIN_VOTE_COUNT, 5000, value=int(g["min_vote_count"]), step=10, key=W + "min_vote_count"
        )

        # Get all unique genres from the dataframe
        # Prioritize genres_str as it's more reliable (always a string)
        all_genres = set()
        
        # First try genres_str (most reliable - always comma-separated string)
        if "genres_str" in df.columns:
            for genre_str in df["genres_str"].dropna():
                if isinstance(genre_str, str) and genre_str != "Unknown" and genre_str.strip():
                    # Split by comma and clean up
                    genres = [g.strip() for g in genre_str.split(",") if g.strip() and g.strip() != "Unknown"]
                    all_genres.update(genres)
        
        # Fallback to genres column (list of genre names)
        if not all_genres and "genres" in df.columns:
            for genre_list in df["genres"].dropna():
                # Handle both list and string representation of list
                if isinstance(genre_list, list):
                    all_genres.update([g for g in genre_list if g and g != "Unknown"])
                elif isinstance(genre_list, str):
                    # Try to parse string representation of list
                    try:
                        import ast
                        parsed = ast.literal_eval(genre_list)
                        if isinstance(parsed, list):
                            all_genres.update([g for g in parsed if g and g != "Unknown"])
                    except:
                        # If parsing fails, try splitting by comma
                        if "," in genre_list:
                            all_genres.update([g.strip() for g in genre_list.split(",") if g.strip() and g.strip() != "Unknown"])
        
        # If no genres found, try to regenerate from genre_ids
        if not all_genres and "genre_ids" in df.columns:
            genre_map = fetch_genre_map()
            for genre_ids in df["genre_ids"].dropna():
                if isinstance(genre_ids, list):
                    genres = [genre_map.get(gid, "Unknown") for gid in genre_ids if genre_map.get(gid)]
                    all_genres.update([g for g in genres if g and g != "Unknown"])
        
        genres_list = ["All"] + sorted([g for g in all_genres if g and g != "Unknown"])
        
        if g["genre"] not in genres_list:
            g["genre"] = "All"

        genre = st.selectbox(
            "Genre", genres_list, index=genres_list.index(g["genre"]), key=W + "genre"
        )

        st.write("**Year Range**")
        min_year = st.slider(
            "Min Year", config.MIN_YEAR, config.MAX_YEAR, value=int(g["min_year"]), step=1, key=W + "min_year"
        )
        max_year = st.slider(
            "Max Year", config.MIN_YEAR, config.MAX_YEAR, value=int(g["max_year"]), step=1, key=W + "max_year"
        )

        adult = st.checkbox(
            "Include Adult Content", value=bool(g["adult"]), key=W + "adult"
        )
        include_missing_dates = st.checkbox(
            "Include Missing Release Dates", value=bool(g["include_missing_dates"]), key=W + "include_missing_dates"
        )

        # --- Write back into GLOBAL store (single source of truth) ---
        g["min_rating"] = min_rating
        g["max_popularity"] = max_popularity
        g["min_vote_count"] = min_vote_count
        g["genre"] = genre
        g["min_year"] = min_year
        g["max_year"] = max_year
        g["adult"] = adult
        g["include_missing_dates"] = include_missing_dates

        st.divider()

        if st.button("🔄 Refresh Data", use_container_width=True, key=W + "refresh"):
            st.cache_data.clear()
            # Delete CSV cache to force fresh fetch
            delete_csv_cache()
            # Clear only data; keep GLOBAL_FILTERS so filters persist
            for k in ["tmdb_prepared_data", "tmdb_show_progress", "tmdb_data_loaded", "csv_loaded_notified"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        st.divider()
        st.caption(f"📊 Total Movies: {len(df):,}")

    # Return filters from GLOBAL store (stable across pages)
    return {
        "min_rating": g["min_rating"],
        "max_popularity": g["max_popularity"],
        "min_vote_count": g["min_vote_count"],
        "genre": g["genre"],
        "adult": g["adult"],
        "min_year": g["min_year"],
        "max_year": g["max_year"],
        "include_missing_dates": g["include_missing_dates"],
    }




# -----------------------------
# CSV persistence functions
# -----------------------------

def save_data_to_csv(df: pd.DataFrame) -> bool:
    """Save prepared DataFrame to CSV file."""
    try:
        df.to_csv(config.CSV_DATA_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Failed to save data to CSV: {e}")
        return False

def load_data_from_csv() -> pd.DataFrame | None:
    """Load prepared DataFrame from CSV file if it exists."""
    if not os.path.exists(config.CSV_DATA_FILE):
        return None
    
    try:
        df = pd.read_csv(config.CSV_DATA_FILE)
        # Convert release_date back to datetime
        df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
        
        # Handle genre_ids column (might be stored as string in CSV)
        if "genre_ids" in df.columns:
            # Convert string representation of list back to list if needed
            if df["genre_ids"].dtype == "object":
                def parse_genre_ids(x):
                    if pd.isna(x) or x == "":
                        return []
                    if isinstance(x, list):
                        return x
                    # Try to parse string representation
                    try:
                        import ast
                        return ast.literal_eval(str(x))
                    except:
                        return []
                df["genre_ids"] = df["genre_ids"].apply(parse_genre_ids)
        
        # Ensure gems_score and year are present (for backward compatibility)
        if "gems_score" not in df.columns:
            df["gems_score"] = (df["vote_average"] * np.log10(df["vote_count"] + 1)) / (df["popularity"] + 1)
            df["gems_score"] = df["gems_score"].fillna(0)
        if "year" not in df.columns:
            df["year"] = df["release_date"].dt.year
        
        # Handle genres column (might be stored as string in CSV)
        if "genres" in df.columns:
            # Convert string representation of list back to list if needed
            if df["genres"].dtype == "object":
                def parse_genres(x):
                    if pd.isna(x) or x == "":
                        return []
                    if isinstance(x, list):
                        return x
                    # Try to parse string representation
                    try:
                        import ast
                        parsed = ast.literal_eval(str(x))
                        if isinstance(parsed, list):
                            return parsed
                    except:
                        pass
                    return []
                df["genres"] = df["genres"].apply(parse_genres)
        
        # Regenerate genres columns if missing (for backward compatibility with old CSV files)
        if "genres" not in df.columns or "genres_str" not in df.columns:
            genre_map = fetch_genre_map()
            def map_genre_ids(genre_ids):
                if not isinstance(genre_ids, list):
                    return []
                return [genre_map.get(gid, "Unknown") for gid in genre_ids]
            df["genres"] = df["genre_ids"].apply(map_genre_ids)
            df["genres_str"] = df["genres"].apply(lambda x: ", ".join(x) if x else "Unknown")
        elif "genres_str" not in df.columns and "genres" in df.columns:
            # Regenerate genres_str if missing
            df["genres_str"] = df["genres"].apply(lambda x: ", ".join(x) if isinstance(x, list) and x else "Unknown")
        
        return df
    except Exception as e:
        st.warning(f"Failed to load data from CSV: {e}. Will fetch from TMDB instead.")
        return None

def delete_csv_cache():
    """Delete the CSV cache file."""
    try:
        if os.path.exists(config.CSV_DATA_FILE):
            os.remove(config.CSV_DATA_FILE)
            return True
    except Exception as e:
        st.error(f"Failed to delete CSV cache: {e}")
    return False

# -----------------------------
# Shared data loader (multipage-safe)
# -----------------------------

def get_data() -> pd.DataFrame | None:
    """
    Multipage-safe loader with CSV persistence.
    - First checks session_state (fastest)
    - Then checks CSV file (fast, no API calls)
    - Finally fetches from TMDB (slow, with progress)
    - Saves to CSV after fetching from TMDB
    - Stores prepared df in session_state so switching pages does NOT refetch.
    """
    session_key = "tmdb_prepared_data"
    
    # First: Check session state (fastest, no I/O)
    if session_key in st.session_state:
        cached = st.session_state.get(session_key)
        if isinstance(cached, pd.DataFrame) and len(cached) > 0:
            return cached

    # Second: Check CSV file (fast, no API calls)
    csv_data = load_data_from_csv()
    if csv_data is not None and len(csv_data) > 0:
        st.session_state[session_key] = csv_data
        st.session_state.tmdb_show_progress = False
        # Show info only once per session
        if "csv_loaded_notified" not in st.session_state:
            st.info(f"📁 Loaded {len(csv_data):,} movies from CSV cache. Use 'Refresh Data' to fetch fresh data from TMDB.")
            st.session_state.csv_loaded_notified = True
        return csv_data

    # Third: Fetch from TMDB (slow, with progress)
    # show progress only on first load in this session
    st.session_state.setdefault("tmdb_show_progress", True)
    show_progress = st.session_state.tmdb_show_progress

    try:
        if show_progress:
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            progress_bar = progress_placeholder.progress(0.0)
            status_text = status_placeholder.empty()

            max_pages = config.DEFAULT_FETCH_PAGES

            all_movies = []
            total_pages_known = None

            backoff = 1.0
            backoff_max = 10.0

            for page in range(1, max_pages + 1):
                # Fetch page (cached) with backoff on 429
                while True:
                    data = fetch_tmdb_page(page)
                    if isinstance(data, dict) and data.get("_rate_limited"):
                        status_text.warning(f"⏳ Rate limited. Waiting {backoff:.0f}s...")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, backoff_max)
                        continue
                    backoff = 1.0
                    break

                if total_pages_known is None:
                    total_pages_known = min(data.get("total_pages", max_pages), max_pages)

                movies = data.get("results", [])
                if not movies:
                    break

                all_movies.extend(movies)

                # Update UI (lightweight)
                progress_bar.progress(min(1.0, page / max(total_pages_known, 1)))
                status_text.text(f"📥 Page {page}/{total_pages_known} | movies {len(all_movies):,}")

                if page >= total_pages_known:
                    break

            progress_bar.progress(1.0)
            status_text.text(f"✅ Complete! Fetched {len(all_movies):,} movies.")
            time.sleep(0.5)
            progress_placeholder.empty()
            status_placeholder.empty()

            if not all_movies:
                st.error("No movies fetched. Please check your API token.")
                return None

            df_prepared = prepare_df(pd.DataFrame(all_movies))
            
            # Save to CSV after fetching
            if save_data_to_csv(df_prepared):
                st.success(f"💾 Saved {len(df_prepared):,} movies to {config.CSV_DATA_FILE}")
            
            st.session_state[session_key] = df_prepared
            st.session_state.tmdb_show_progress = False
            return df_prepared

        # Subsequent loads in same session: full fetch via cached all-pages
        df_raw = fetch_tmdb_all_pages(max_pages=config.MAX_TMDB_PAGES)
        df_prepared = prepare_df(df_raw)
        
        # Save to CSV after fetching
        if save_data_to_csv(df_prepared):
            st.success(f"💾 Saved {len(df_prepared):,} movies to {config.CSV_DATA_FILE}")
        
        st.session_state[session_key] = df_prepared
        st.session_state.tmdb_show_progress = False
        return df_prepared

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return None






# -----------------------------
# Top 10 rated films of current month
# -----------------------------

def get_top_rated_current_month(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Get top rated films released in the current month.
    Returns DataFrame sorted by vote_average descending.
    """
    from datetime import datetime
    
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # Filter for current month and year
    df_current_month = df[
        (df["release_date"].dt.month == current_month) & 
        (df["release_date"].dt.year == current_year) &
        (df["release_date"].notna())
    ].copy()
    
    # Sort by vote_average descending, then by vote_count descending as tiebreaker
    df_current_month = df_current_month.sort_values(
        ["vote_average", "vote_count"], 
        ascending=[False, False]
    )
    
    return df_current_month.head(top_n)


def render_top_rated_current_month_table(df: pd.DataFrame) -> None:
    """
    Render a table showing the top rated films of the current month.
    """
    from datetime import datetime
    
    current_date = datetime.now()
    month_name = current_date.strftime("%B")
    current_year = current_date.year
    
    st.subheader(f"🏆 Top Rated Films of {month_name} {current_year}")
    
    # Get top rated films of current month
    df_top_month = get_top_rated_current_month(df, top_n=50)
    
    if len(df_top_month) == 0:
        st.info(f"No movies found for {month_name} {current_year}. This might be because:")
        st.write("- Movies for this month haven't been released yet")
        st.write("- The data doesn't include recent releases")
        st.write("- Try refreshing the data to get the latest movies")
        return
    
    # Prepare display data
    df_display = df_top_month.copy()
    df_display["release_date_str"] = df_display["release_date"].dt.strftime("%Y-%m-%d")
    
    # Select columns for display
    display_cols = [
        "original_title",
        "release_date_str", 
        "vote_average",
        "vote_count",
        "popularity",
        "genres_str"
    ]
    
    df_table = df_display[display_cols].copy()
    df_table.columns = ["Title", "Release Date", "Rating", "Vote Count", "Popularity", "Genres"]
    
    # Format numeric columns
    df_table["Rating"] = df_table["Rating"].round(2)
    df_table["Popularity"] = df_table["Popularity"].round(2)
    
    # Show count and slider for limiting results
    total_movies = len(df_table)
    st.caption(f"Found {total_movies} movies released in {month_name} {current_year}")
    
    if total_movies > 10:
        show_n = st.slider(
            "Number of movies to display",
            min_value=5,
            max_value=min(50, total_movies),
            value=min(20, total_movies),
            step=5,
            key="current_month_slider"
        )
        df_table = df_table.head(show_n)
    





st.title("Moviever Film database")

import pandas as pd
from datetime import datetime, timedelta
from app import get_data

def get_top_rated_previous_month(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Get top rated films released in the previous month.
    Returns DataFrame sorted by vote_average descending.
    """
    current_date = datetime.now()
    
    # Calculate previous month
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    previous_month = last_day_previous_month.month
    previous_year = last_day_previous_month.year
    
    # Filter for previous month and year
    df_previous_month = df[
        (df["release_date"].dt.month == previous_month) & 
        (df["release_date"].dt.year == previous_year) &
        (df["release_date"].notna())
    ].copy()
    
    # Sort by vote_average descending, then by vote_count descending as tiebreaker
    df_previous_month = df_previous_month.sort_values(
        ["vote_average", "vote_count"], 
        ascending=[False, False]
    )
    
    return df_previous_month.head(top_n)

def render_top_rated_previous_month_table(df: pd.DataFrame) -> None:
    """
    Render a table showing the top rated films of the previous month.
    """
    current_date = datetime.now()
    
    # Calculate previous month name and year
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    previous_month_name = last_day_previous_month.strftime("%B")
    previous_year = last_day_previous_month.year
    
    st.subheader(f"🏆 Top 10 Rated Films of {previous_month_name} {previous_year}")
    
    # Get top rated films of previous month
    df_top_month = get_top_rated_previous_month(df, top_n=10)
    
    if len(df_top_month) == 0:
        st.info(f"No movies found for {previous_month_name} {previous_year}.")
        st.write("This might be because:")
        st.write("- No movies were released in that month")
        st.write("- The data doesn't include movies from that period")
        st.write("- Try refreshing the data to get more complete information")
        return
    
    # Prepare display data
    df_display = df_top_month.copy()
    df_display["release_date_str"] = df_display["release_date"].dt.strftime("%Y-%m-%d")
    
    # Select columns for display
    display_cols = [
        "original_title",
        "release_date_str", 
        "vote_average",
        "vote_count",
        "popularity",
        "genres_str"
    ]
    
    df_table = df_display[display_cols].copy()
    df_table.columns = ["Title", "Release Date", "Rating", "Vote Count", "Popularity", "Genres"]
    
    # Format numeric columns
    df_table["Rating"] = df_table["Rating"].round(2)
    df_table["Popularity"] = df_table["Popularity"].round(2)
    
    
    # Display the table
    st.dataframe(df_table, use_container_width=True, height=400)
    
    
    # Show some stats
    if len(df_top_month) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_rating = df_top_month["vote_average"].mean()
            st.metric("Average Rating", f"{avg_rating:.2f}")
        with col2:
            total_votes = df_top_month["vote_count"].sum()
            st.metric("Total Votes", f"{total_votes:,}")
        with col3:
            highest_rated = df_top_month["vote_average"].max()
            st.metric("Highest Rating", f"{highest_rated:.2f}")

# Usage example - add this to your Streamlit page
if __name__ == "__main__":
    # Load data
    df = get_data()
    if df is not None:
        render_top_rated_previous_month_table(df)

