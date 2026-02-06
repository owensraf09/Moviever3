"""
Font configuration utilities for Moviever dashboard.
Applies Cambria (regular, italic, bold) for regular text and Latha for headers/titles.
"""

import streamlit as st


def apply_moviever_fonts():
    """
    Injects custom CSS to apply Moviever fonts:
    - Cambria (regular, italic, bold) for regular text
    - Latha for headers/titles
    """
    css = """
    <style>
    /* Apply Latha for headers and titles FIRST - highest specificity */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Latha', 'Cambria', serif !important;
        font-weight: 700 !important;
    }
    
    /* Streamlit-specific header selectors with high specificity */
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4,
    div[data-testid="stMarkdownContainer"] h5,
    div[data-testid="stMarkdownContainer"] h6,
    .element-container h1,
    .element-container h2,
    .element-container h3,
    .element-container h4,
    .element-container h5,
    .element-container h6,
    [data-testid="stMarkdownContainer"] .element-container h1,
    [data-testid="stMarkdownContainer"] .element-container h2,
    [data-testid="stMarkdownContainer"] .element-container h3,
    [data-testid="stMarkdownContainer"] .element-container h4,
    [data-testid="stMarkdownContainer"] .element-container h5,
    [data-testid="stMarkdownContainer"] .element-container h6 {
        font-family: 'Latha', 'Cambria', serif !important;
        font-weight: 700 !important;
    }
    
    /* Streamlit title, header, subheader classes */
    [data-testid="stHeader"] h1,
    [data-testid="stHeader"] h2,
    [data-testid="stHeader"] h3,
    .stTitle,
    .stHeader,
    .stSubheader {
        font-family: 'Latha', 'Cambria', serif !important;
        font-weight: 700 !important;
    }
    
    /* Apply Cambria for regular text (body, paragraphs, etc.) - but NOT headers */
    body, .stApp, p, span, label, input, textarea, select, button, 
    .stText, .stDataFrame, .stMetric, .stCaption,
    .stSelectbox label, .stSlider label, .stRadio label,
    .stDataFrame table, .stDataFrame th, .stDataFrame td {
        font-family: 'Cambria', 'Times New Roman', serif !important;
    }
    
    /* Apply to element-container for non-header content */
    .element-container {
        font-family: 'Cambria', 'Times New Roman', serif !important;
    }
    
    /* Ensure italic and bold variants work with Cambria */
    em, i, .italic {
        font-family: 'Cambria', 'Times New Roman', serif !important;
        font-style: italic !important;
    }
    
    strong, b, .bold {
        font-family: 'Cambria', 'Times New Roman', serif !important;
        font-weight: bold !important;
    }
    
    /* Apply to sidebar elements */
    .css-1d391kg, .css-1lcbmhc, .css-1y4p8pa {
        font-family: 'Cambria', 'Times New Roman', serif !important;
    }
    
    /* Apply to Streamlit widget labels and text */
    .stTextInput label, .stTextArea label, .stNumberInput label,
    .stCheckbox label, .stButton button {
        font-family: 'Cambria', 'Times New Roman', serif !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
