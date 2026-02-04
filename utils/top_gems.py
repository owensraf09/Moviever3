"""
Functions for finding and rendering top gems from previous month.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.rendering import render_cards


def get_top_gems_previous_month(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Get top gems (by gems_score) released in the previous month.
    Returns DataFrame sorted by gems_score descending.
    """
    current_date = datetime.now()

    # Calculate previous month
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    previous_month = last_day_previous_month.month
    previous_year = last_day_previous_month.year

    # Filter for previous month and year
    df_previous_month = df[
        (df["release_date"].dt.month == previous_month)
        & (df["release_date"].dt.year == previous_year)
        & (df["release_date"].notna())
    ].copy()

    # Ensure gems_score exists
    if "gems_score" not in df_previous_month.columns:
        df_previous_month["gems_score"] = (
            df_previous_month["vote_average"]
            * np.log10(df_previous_month["vote_count"] + 1)
        ) / (df_previous_month["popularity"] + 1)
        df_previous_month["gems_score"] = df_previous_month["gems_score"].fillna(0)

    # Sort by gems_score descending
    df_previous_month = df_previous_month.sort_values("gems_score", ascending=False)

    return df_previous_month.head(top_n)


def render_top_gems_previous_month_table(df: pd.DataFrame) -> None:
    """
    Render a table showing the top 10 hidden gems of the previous month by gems_score.
    """
    current_date = datetime.now()

    # Calculate previous month name and year
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    previous_month_name = last_day_previous_month.strftime("%B")
    previous_year = last_day_previous_month.year

    st.subheader(f" Our Top 10 Film of {previous_month_name} {previous_year}")
    # Get top gems of previous month
    df_top_gems = get_top_gems_previous_month(df, top_n=10)

    if len(df_top_gems) == 0:
        st.info(f"No movies found for {previous_month_name} {previous_year}.")
        st.write("This might be because:")
        st.write("- No movies were released in that month")
        st.write("- The data doesn't include movies from that period")
        st.write("- Try refreshing the data to get more complete information")
        return

    # Prepare display data
    df_display = df_top_gems.copy()
    df_display["release_date_str"] = df_display["release_date"].dt.strftime("%Y-%m-%d")

    # Select columns for display
    display_cols = [
        "original_title",
        "release_date_str",
        "vote_average",
        "vote_count",
        "popularity",
        "gems_score",
        "genres_str",
    ]

    df_table = df_display[display_cols].copy()
    df_table.columns = [
        "Title",
        "Release Date",
        "Rating",
        "Vote Count",
        "Popularity",
        "Gems Score",
        "Genres",
    ]

    # Format numeric columns
    df_table["Rating"] = df_table["Rating"].round(2)
    df_table["Popularity"] = df_table["Popularity"].round(2)
    df_table["Gems Score"] = df_table["Gems Score"].round(4)

    # Add rank column
    df_table.insert(0, "Rank", range(1, len(df_table) + 1))

    # Show count
    total_movies = len(df_table)

    # Display the table
    st.dataframe(df_table, use_container_width=True, height=400)

    # Show some stats
    if len(df_top_gems) > 0:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_rating = df_top_gems["vote_average"].mean()
            st.metric("Average Rating", f"{avg_rating:.2f}")
        with col2:
            avg_gems_score = df_top_gems["gems_score"].mean()
            st.metric("Average Gems Score", f"{avg_gems_score:.4f}")
        with col3:
            total_votes = df_top_gems["vote_count"].sum()
            st.metric("Total Votes", f"{total_votes:,}")
        with col4:
            avg_popularity = df_top_gems["popularity"].mean()
            st.metric("Average Popularity", f"{avg_popularity:.2f}")


def render_top_gems_previous_month_cards(df: pd.DataFrame) -> None:
    """
    Render a table showing the top 10 hidden gems of the previous month by gems_score.
    """
    current_date = datetime.now()

    # Calculate previous month name and year
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    previous_month_name = last_day_previous_month.strftime("%B")
    previous_year = last_day_previous_month.year

    st.subheader(f" Our Top 10 Film of {previous_month_name} {previous_year}")
    # Get top gems of previous month
    df_top_gems = get_top_gems_previous_month(df, top_n=10)

    if len(df_top_gems) == 0:
        st.info(f"No movies found for {previous_month_name} {previous_year}.")
        st.write("This might be because:")
        st.write("- No movies were released in that month")
        st.write("- The data doesn't include movies from that period")
        st.write("- Try refreshing the data to get more complete information")
        return

    # Prepare display data
    df_display = df_top_gems.copy()
    df_display["release_date_str"] = df_display["release_date"].dt.strftime("%Y-%m-%d")

    # # Select columns for display
    # display_cols = [
    #     "original_title",
    #     "release_date_str",
    #     "vote_average",
    #     "vote_count",
    #     "popularity",
    #     "gems_score",
    #     "genres_str",
    # ]

    # df_table = df_display[display_cols].copy()
    # df_table.columns = [
    #     "Title",
    #     "Release Date",
    #     "Rating",
    #     "Vote Count",
    #     "Popularity",
    #     "Gems Score",
    #     "Genres",
    # ]

    # # Format numeric columns
    # df_table["Rating"] = df_table["Rating"].round(2)
    # df_table["Popularity"] = df_table["Popularity"].round(2)
    # df_table["Gems Score"] = df_table["Gems Score"].round(4)

    # # Add rank column
    # df_table.insert(0, "Rank", range(1, len(df_table) + 1))

    # # Show count
    # total_movies = len(df_table)

    # # Display the table
    # st.dataframe(df_table, use_container_width=True, height=400)

    render_cards(df_display, 5)

    # Show some stats
    if len(df_top_gems) > 0:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_rating = df_top_gems["vote_average"].mean()
            st.metric("Average Rating", f"{avg_rating:.2f}")
        with col2:
            avg_gems_score = df_top_gems["gems_score"].mean()
            st.metric("Average Gems Score", f"{avg_gems_score:.4f}")
        with col3:
            total_votes = df_top_gems["vote_count"].sum()
            st.metric("Total Votes", f"{total_votes:,}")
        with col4:
            avg_popularity = df_top_gems["popularity"].mean()
            st.metric("Average Popularity", f"{avg_popularity:.2f}")
