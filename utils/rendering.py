"""
Rendering functions for displaying UI components, charts, and tables.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import config


def render_metrics(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Movies Loaded", len(df_all))

    with col2:
        st.metric("Hidden Gems Count", len(df_filtered))

    with col3:
        median_rating = (
            df_filtered["vote_average"].median() if len(df_filtered) > 0 else 0
        )
        st.metric("Median Rating", f"{median_rating:.2f}")

    with col4:
        median_popularity = (
            df_filtered["popularity"].median() if len(df_filtered) > 0 else 0
        )
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

    df_display["release_date_str"] = (
        df_display["release_date"].dt.strftime("%Y-%m-%d").fillna("N/A")
    )
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
    default_value = (
        min(config.DEFAULT_TOP_N_MOVIES, total_movies)
        if total_movies >= min_slider
        else total_movies
    )

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
    df_table.columns = [
        "Title",
        "Release Date",
        "Rating",
        "Vote Count",
        "Popularity",
        "Language",
        "Gems Score",
    ]

    df_table["Rating"] = df_table["Rating"].round(2)
    df_table["Popularity"] = df_table["Popularity"].round(2)
    df_table["Gems Score"] = df_table["Gems Score"].round(3)

    st.dataframe(df_table, use_container_width=True, height=400)

    st.subheader("Movie Details")
    movie_titles = df_display_top["original_title"].tolist()
    selected_title = st.selectbox(
        "Select a movie to view details:", movie_titles, key="details_select_title"
    )

    if selected_title:
        selected_movie = df_display_top[
            df_display_top["original_title"] == selected_title
        ].iloc[0]

        col1, col2 = st.columns([1, 2])

        with col1:
            if (
                pd.notna(selected_movie.get("poster_path"))
                and selected_movie["poster_path"]
            ):
                poster_url = (
                    f"{config.TMDB_IMAGE_BASE_URL}{selected_movie['poster_path']}"
                )
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


def render_cards(df: pd.DataFrame, cards_per_row: int):
    # Card view
    cols = st.columns(cards_per_row)
    for idx, (_, movie) in enumerate(df.iterrows()):
        col = cols[idx % cards_per_row]
        with col:
            with st.container():
                # Poster
                if pd.notna(movie.get("poster_path")) and movie["poster_path"]:
                    poster_url = f"{config.TMDB_IMAGE_BASE_URL}{movie['poster_path']}"
                    st.image(poster_url, use_container_width=True)

                # Title and key info
                st.markdown(f"### {movie['original_title']}")
                st.caption(
                    f"📅 {movie['release_date_str']} | 🌍 {movie['original_language']}"
                )

                col_metrics = st.columns(3)
                with col_metrics[0]:
                    st.metric("⭐", f"{movie['vote_average']:.1f}")
                with col_metrics[1]:
                    st.metric("👥", f"{int(movie['vote_count']):,}")
                with col_metrics[2]:
                    st.metric("🔥", f"{movie['popularity']:.1f}")

                st.caption(f"💎 Gems Score: {movie['gems_score']:.3f}")

                if pd.notna(movie.get("overview")) and movie["overview"]:
                    with st.expander("Overview"):
                        st.write(
                            movie["overview"][:200] + "..."
                            if len(movie["overview"]) > 200
                            else movie["overview"]
                        )

                st.divider()
