"""
Sidebar filter functions for user interface filters.
"""

import streamlit as st
from ast import literal_eval
import config
from utils.genre import fetch_genre_map
from utils.csv_persistence import delete_csv_cache


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
        page_id = (
            ctx.page_script_hash
            if ctx and getattr(ctx, "page_script_hash", None)
            else "main"
        )
    except Exception:
        page_id = "main"

    W = f"__w__{page_id}__"  # widget key prefix (page-unique)
    SKEY = "GLOBAL_FILTERS"  # global persisted values (shared across pages)

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
            "original_language": "All",
        }

    g = st.session_state[SKEY]

    # Year bounds from data (for initializing filter values)
    min_year_val = (
        int(df["year"].min()) if df["year"].notna().any() else config.MIN_YEAR
    )
    max_year_val = (
        int(df["year"].max()) if df["year"].notna().any() else config.MAX_YEAR
    )

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
            "Min Rating",
            config.MIN_VOTE_AVERAGE,
            10.0,
            value=float(g["min_rating"]),
            step=0.1,
            key=W + "min_rating",
        )
        max_popularity = st.slider(
            "Max Popularity",
            0.0,
            100.0,
            value=float(g["max_popularity"]),
            step=1.0,
            key=W + "max_popularity",
        )
        min_vote_count = st.slider(
            "Min Vote Count",
            config.MIN_VOTE_COUNT,
            5000,
            value=int(g["min_vote_count"]),
            step=10,
            key=W + "min_vote_count",
        )

        # Get all unique genres from the dataframe
        # Prioritize genres_str as it's more reliable (always a string)
        all_genres = set()

        # First try genres_str (most reliable - always comma-separated string)
        if "genres_str" in df.columns:
            for genre_str in df["genres_str"].dropna():
                if (
                    isinstance(genre_str, str)
                    and genre_str != "Unknown"
                    and genre_str.strip()
                ):
                    # Split by comma and clean up
                    genres = [
                        g.strip()
                        for g in genre_str.split(",")
                        if g.strip() and g.strip() != "Unknown"
                    ]
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
                        parsed = literal_eval(genre_list)
                        if isinstance(parsed, list):
                            all_genres.update(
                                [g for g in parsed if g and g != "Unknown"]
                            )
                    except:
                        # If parsing fails, try splitting by comma
                        if "," in genre_list:
                            all_genres.update(
                                [
                                    g.strip()
                                    for g in genre_list.split(",")
                                    if g.strip() and g.strip() != "Unknown"
                                ]
                            )

        # If no genres found, try to regenerate from genre_ids
        if not all_genres and "genre_ids" in df.columns:
            genre_map = fetch_genre_map()
            for genre_ids in df["genre_ids"].dropna():
                if isinstance(genre_ids, list):
                    genres = [
                        genre_map.get(gid, "Unknown")
                        for gid in genre_ids
                        if genre_map.get(gid)
                    ]
                    all_genres.update([g for g in genres if g != "Unknown"])

        genres_list = ["All"] + sorted([g for g in all_genres if g and g != "Unknown"])

        if g["genre"] not in genres_list:
            g["genre"] = "All"

        genre = st.selectbox(
            "Genre", genres_list, index=genres_list.index(g["genre"]), key=W + "genre"
        )

        # Filter by language
        all_languages = set()

        all_languages.update(df["original_language"].dropna())

        language_list = ["All"] + sorted([lang for lang in all_languages if lang])
        if g["original_language"] not in language_list:
            g["original_language"] = "All"

        original_language = st.selectbox(
            "Language",
            language_list,
            index=language_list.index(g["original_language"]),
            key=W + "language",
        )

        st.write("**Year Range**")
        min_year = st.slider(
            "Min Year",
            config.MIN_YEAR,
            config.MAX_YEAR,
            value=int(g["min_year"]),
            step=1,
            key=W + "min_year",
        )
        max_year = st.slider(
            "Max Year",
            config.MIN_YEAR,
            config.MAX_YEAR,
            value=int(g["max_year"]),
            step=1,
            key=W + "max_year",
        )

        adult = st.checkbox(
            "Include Adult Content", value=bool(g["adult"]), key=W + "adult"
        )
        include_missing_dates = st.checkbox(
            "Include Missing Release Dates",
            value=bool(g["include_missing_dates"]),
            key=W + "include_missing_dates",
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
        g["original_language"] = original_language

        st.divider()

        if st.button("🔄 Refresh Data", use_container_width=True, key=W + "refresh"):
            st.cache_data.clear()
            # Delete CSV cache to force fresh fetch
            delete_csv_cache()
            # Clear only data; keep GLOBAL_FILTERS so filters persist
            for k in [
                "tmdb_prepared_data",
                "tmdb_show_progress",
                "tmdb_data_loaded",
                "csv_loaded_notified",
            ]:
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
        "original_language": g["original_language"],
    }
