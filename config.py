"""
Configuration constants for TMDB Streamlit app.
This file contains all tunable, environment-independent constants.
Secrets (API keys, tokens) are stored in .env file, not here.
"""

# -----------------------------
# TMDB API Configuration
# -----------------------------

# TMDB API base URL (without filters - filters are added in fetch functions)
TMDB_BASE_URL = "https://api.themoviedb.org/3/discover/movie"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"
TMDB_GENRE_URL = "https://api.themoviedb.org/3/genre/movie/list"

MAX_TMDB_PAGES = 500
DEFAULT_FETCH_PAGES = 500

# -----------------------------
# Caching Configuration
# -----------------------------

TMDB_CACHE_TTL = 86400  # 24 hours
GENRE_CACHE_TTL = 86400  # 24 hours
LANGUAGE_CACHE_TTL = 86400  # 24 hours

# -----------------------------
# File Configuration
# -----------------------------

CSV_DATA_FILE = "tmdb_movies_data.csv"

# -----------------------------
# UI Defaults
# -----------------------------

DEFAULT_MIN_RATING = 7.5
DEFAULT_MAX_POPULARITY = 20.0
DEFAULT_MIN_VOTE_COUNT = 50
DEFAULT_TOP_N_MOVIES = 50

# for filters and sliders
MIN_YEAR = 1950
MAX_YEAR = 2026
MIN_VOTE_AVERAGE = 6.0
MIN_VOTE_COUNT = 10

from pandas import DataFrame
import numpy as np


def gems_score(df: DataFrame) -> DataFrame:
    scores = (df["vote_average"] * np.log10(df["vote_count"] + 1)) / (
        df["popularity"] + 1
    )
    scores.fillna(0, inplace=True)
    return scores
