"""
Runtime theme switching.

Streamlit's built-in theme (.streamlit/config.toml) is fixed at launch and
can't be swapped from inside a running session, so themes here work by
injecting a <style> block that overrides the relevant Streamlit CSS classes.

Alert colors (st.error / st.warning / st.success) are deliberately left
alone across every theme, so anomaly severity always reads the same way
regardless of which theme is active.
"""

import streamlit as st

THEMES = {
    "Light": {
        "bg": "#ffffff", "sidebar_bg": "#f4f4f6", "text": "#1a1a1a",
        "accent": "#2E7D32", "metric": "#1a1a1a", "card_bg": "#f8f9fa",
    },
    "Dark": {
        "bg": "#0e1117", "sidebar_bg": "#161a23", "text": "#e6e6e6",
        "accent": "#4FC3F7", "metric": "#e6e6e6", "card_bg": "#1c202b",
    },
    "Kombucha Amber": {
        "bg": "#fbf3e6", "sidebar_bg": "#f0e0c0", "text": "#3b2a1a",
        "accent": "#b5651d", "metric": "#7a4a12", "card_bg": "#f5e8d0",
    },
    "Lab Blue": {
        "bg": "#eef4fa", "sidebar_bg": "#dbe8f5", "text": "#0d2438",
        "accent": "#0277BD", "metric": "#0d2438", "card_bg": "#e2edf7",
    },
    "SCOBY Green": {
        "bg": "#f1f7ee", "sidebar_bg": "#dcecd4", "text": "#1e3320",
        "accent": "#4C7A3E", "metric": "#1e3320", "card_bg": "#e6f0e0",
    },
}


def apply_theme(theme_name):
    t = THEMES.get(theme_name, THEMES["Light"])
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {t['bg']};
            color: {t['text']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']};
        }}
        h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown {{
            color: {t['text']};
        }}
        div[data-testid="stMetricValue"] {{
            color: {t['metric']};
        }}
        div[data-testid="stMetric"] {{
            background-color: {t['card_bg']};
            border-radius: 8px;
            padding: 8px 12px;
        }}
        .stButton > button {{
            border-color: {t['accent']};
            color: {t['accent']};
        }}
        .stButton > button:hover {{
            background-color: {t['accent']};
            color: white;
            border-color: {t['accent']};
        }}
        div[data-testid="stProgress"] > div > div > div {{
            background-color: {t['accent']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def theme_picker():
    """
    Renders the theme selectbox in the sidebar and applies the chosen theme.
    Call once near the top of every page, before other sidebar widgets, so
    the CSS override is in place before the rest of the page renders.
    Selection is stored in st.session_state, so it carries over as you
    navigate between pages within the same session.
    """
    if "theme" not in st.session_state:
        st.session_state.theme = "Light"
    names = list(THEMES.keys())
    choice = st.sidebar.selectbox(
        "Theme", names, index=names.index(st.session_state.theme), key="theme_selector"
    )
    st.session_state.theme = choice
    apply_theme(choice)
