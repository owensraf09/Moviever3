"""
TMDB API fetching functions for retrieving movie data.
"""

import streamlit as st
import pandas as pd
import requests
import time
import config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load TMDB Bearer Token from environment variable
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")
if not TMDB_BEARER_TOKEN:
    raise ValueError(
        "TMDB_BEARER_TOKEN not found in environment variables. Please create a .env file with your token."
    )

# Ensure token starts with "Bearer " prefix
if not TMDB_BEARER_TOKEN.startswith("Bearer "):
    TMDB_BEARER_TOKEN = f"Bearer {TMDB_BEARER_TOKEN}"


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
        raise RuntimeError(
            "No movies fetched. Please check your TMDB token / connection."
        )

    return pd.DataFrame(all_movies)


def fetch_tmdb_all_pages(max_pages: int = config.MAX_TMDB_PAGES) -> pd.DataFrame:
    """Public fetch function."""
    return _fetch_tmdb_pages_cached(max_pages=max_pages)


@st.cache_data(ttl=config.LANGUAGE_CACHE_TTL)
def fetch_tmdb_lang_codes() -> pd.DataFrame:
    headers = {
        "accept": "application/json",
        "Authorization": TMDB_BEARER_TOKEN,
    }
    response = requests.get(
        "https://api.themoviedb.org/3/configuration/languages", headers=headers
    )
    return pd.DataFrame(response.json()).set_index("iso_639_1")
