import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
st.set_page_config(page_title="Analytics", layout="wide", page_icon="📊")

from home import get_data, render_sidebar_filters, filter_df, render_metrics


# Load data FIRST - before any UI elements
# This ensures session state check happens before any rendering
df = get_data()
if df is None:
    st.stop()

st.title("📊 Movie Analytics Dashboard")
st.markdown("Explore detailed analytics and visualizations of TMDB movie data")

# Sidebar filters
filters = render_sidebar_filters(df)

# Apply filters
df_filtered = filter_df(df, filters)

if len(df_filtered) == 0:
    st.warning("No movies match your filters. Adjust filters to see analytics.")
    st.stop()

# Metrics
render_metrics(df, df_filtered)

st.divider()

# Charts Section
st.header("📈 Visualizations")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Popularity vs Rating")
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(df_filtered['popularity'], df_filtered['vote_average'], 
                        c=df_filtered['gems_score'], cmap='viridis', 
                        alpha=0.6, s=50)
    ax.set_xlabel('Popularity')
    ax.set_ylabel('Vote Average')
    ax.set_title('Popularity vs Vote Average (colored by Gems Score)')
    ax.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax, label='Gems Score')
    st.pyplot(fig)
    plt.close()

with col2:
    st.subheader("Vote Average Distribution")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df_filtered['vote_average'].dropna(), bins=30, edgecolor='black', color='skyblue')
    ax.axvline(df_filtered['vote_average'].median(), color='red', linestyle='--', 
               label=f'Median: {df_filtered["vote_average"].median():.2f}')
    ax.set_xlabel('Vote Average')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Vote Averages')
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close()

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("Popularity Distribution")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df_filtered['popularity'].dropna(), bins=30, edgecolor='black', color='lightcoral')
    ax.axvline(df_filtered['popularity'].median(), color='blue', linestyle='--', 
               label=f'Median: {df_filtered["popularity"].median():.2f}')
    ax.set_xlabel('Popularity')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Popularity')
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close()

with col4:
    st.subheader("Gems Score Distribution")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df_filtered['gems_score'].dropna(), bins=30, edgecolor='black', color='lightgreen')
    ax.axvline(df_filtered['gems_score'].median(), color='red', linestyle='--', 
               label=f'Median: {df_filtered["gems_score"].median():.3f}')
    ax.set_xlabel('Gems Score')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Hidden Gems Score')
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close()

st.divider()

# Year analysis
st.subheader("📅 Movies by Release Year")
year_counts = df_filtered['year'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(year_counts.index, year_counts.values, color='steelblue', edgecolor='black')
ax.set_xlabel('Release Year')
ax.set_ylabel('Number of Movies')
ax.set_title('Movies by Release Year')
ax.grid(True, alpha=0.3, axis='y')
plt.xticks(rotation=45)
st.pyplot(fig)
plt.close()

st.divider()

# Language analysis
st.subheader("🌍 Movies by Language")
lang_counts = df_filtered['original_language'].value_counts().head(15)
fig, ax = plt.subplots(figsize=(12, 6))
ax.barh(lang_counts.index, lang_counts.values, color='coral', edgecolor='black')
ax.set_xlabel('Number of Movies')
ax.set_ylabel('Language')
ax.set_title('Top 15 Languages by Movie Count')
ax.grid(True, alpha=0.3, axis='x')
st.pyplot(fig)
plt.close()

st.divider()

# Statistical Summary
st.subheader("📋 Statistical Summary")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Mean Rating", f"{df_filtered['vote_average'].mean():.2f}")
    st.metric("Mean Popularity", f"{df_filtered['popularity'].mean():.2f}")

with col2:
    st.metric("Std Rating", f"{df_filtered['vote_average'].std():.2f}")
    st.metric("Std Popularity", f"{df_filtered['popularity'].std():.2f}")

with col3:
    st.metric("Min Rating", f"{df_filtered['vote_average'].min():.2f}")
    st.metric("Max Rating", f"{df_filtered['vote_average'].max():.2f}")

with col4:
    st.metric("Min Popularity", f"{df_filtered['popularity'].min():.2f}")
    st.metric("Max Popularity", f"{df_filtered['popularity'].max():.2f}")
