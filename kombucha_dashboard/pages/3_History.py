"""
Full history log across processes, batches, and sources.
"""

import plotly.express as px
import streamlit as st

from kombucha import storage

st.set_page_config(page_title="History", layout="wide")
st.title("Reading history")

col1, col2, col3 = st.columns(3)
process = col1.selectbox("Process", ["All", "F1", "F2"])
source = col2.selectbox("Source", ["All", "live", "sim"])
batch_input = col3.text_input("Batch # (blank = all)")

df = storage.load_history(
    process=None if process == "All" else process,
    source=None if source == "All" else source,
    batch=int(batch_input) if batch_input.strip() else None,
)

st.write(f"{len(df)} rows")
st.dataframe(df, use_container_width=True)

if not df.empty:
    st.download_button(
        "Download as CSV", df.to_csv(index=False),
        file_name="kombucha_history.csv", mime="text/csv",
    )

    st.subheader("Temperature across all logged batches")
    if "temperature_C" in df.columns:
        fig = px.line(
            df, x="day", y="temperature_C",
            color=df["process"] + " batch " + df["batch"].astype(str),
            markers=True,
        )
        st.plotly_chart(fig, use_container_width=True)
