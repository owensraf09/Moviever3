"""
Main data loading function with CSV persistence and TMDB fetching.
"""

import streamlit as st
import pandas as pd
import time
import config
from utils.tmdb_api import fetch_tmdb_page, fetch_tmdb_all_pages
from utils.data_processing import prepare_df
from utils.csv_persistence import save_data_to_csv, load_data_from_csv


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
            return prepare_df(cached)

    # Second: Check CSV file (fast, no API calls)
    csv_data = load_data_from_csv()
    if csv_data is not None and len(csv_data) > 0:
        st.session_state[session_key] = csv_data
        st.session_state.tmdb_show_progress = False
        # Show info only once per session
        if "csv_loaded_notified" not in st.session_state:
            st.info(
                f"📁 Loaded {len(csv_data):,} movies from CSV cache. Use 'Refresh Data' to fetch fresh data from TMDB."
            )
            st.session_state.csv_loaded_notified = True
        return prepare_df(csv_data)

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
                        status_text.warning(
                            f"⏳ Rate limited. Waiting {backoff:.0f}s..."
                        )
                        time.sleep(backoff)
                        backoff = min(backoff * 2, backoff_max)
                        continue
                    backoff = 1.0
                    break

                if total_pages_known is None:
                    total_pages_known = min(
                        data.get("total_pages", max_pages), max_pages
                    )

                movies = data.get("results", [])
                if not movies:
                    break

                all_movies.extend(movies)

                # Update UI (lightweight)
                progress_bar.progress(min(1.0, page / max(total_pages_known, 1)))
                status_text.text(
                    f"📥 Page {page}/{total_pages_known} | movies {len(all_movies):,}"
                )

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
                st.success(
                    f"💾 Saved {len(df_prepared):,} movies to {config.CSV_DATA_FILE}"
                )

            st.session_state[session_key] = df_prepared
            st.session_state.tmdb_show_progress = False
            return df_prepared

        # Subsequent loads in same session: full fetch via cached all-pages
        df_raw = fetch_tmdb_all_pages(max_pages=config.MAX_TMDB_PAGES)
        df_prepared = prepare_df(df_raw)

        # Save to CSV after fetching
        if save_data_to_csv(df_prepared):
            st.success(
                f"💾 Saved {len(df_prepared):,} movies to {config.CSV_DATA_FILE}"
            )

        st.session_state[session_key] = df_prepared
        st.session_state.tmdb_show_progress = False
        return df_prepared

    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return None
