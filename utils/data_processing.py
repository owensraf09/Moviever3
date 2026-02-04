"""
Data processing functions for preparing and filtering movie data.
"""

import pandas as pd
import numpy as np
from utils.genre import fetch_genre_map
from utils.tmdb_api import fetch_tmdb_lang_codes


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, add year, add gems_score, map genre IDs to names."""
    df = df.copy()

    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["year"] = df["release_date"].dt.year

    df["gems_score"] = (df["vote_average"] * np.log10(df["vote_count"] + 1)) / (
        df["popularity"] + 1
    )
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

    # Map language ISO 639-1 tags to names
    lang_map = fetch_tmdb_lang_codes()
    if lang_map is not None:
        df["original_language"] = df["original_language"].map(
            lambda x: lang_map.loc[x, "english_name"]
        )

    return df


def filter_df(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Filter DataFrame based on user filters."""
    df_filtered = df.copy()

    if not filters["adult"]:
        df_filtered = df_filtered[df_filtered["adult"] == False]

    # Filter by genre (check if selected genre is in the genres list)
    if filters["genre"] != "All":
        if "genres" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["genres"].apply(
                    lambda x: filters["genre"] in x if isinstance(x, list) else False
                )
            ]
        else:
            # Fallback: filter by genres_str if genres column doesn't exist
            df_filtered = df_filtered[
                df_filtered["genres_str"].str.contains(
                    filters["genre"], case=False, na=False
                )
            ]

    # Filter by language
    if filters["original_language"] != "All":
        if "original_language" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["original_language"] == filters["original_language"]
            ]

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
