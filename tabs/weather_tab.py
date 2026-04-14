import streamlit as st
import pandas as pd

def render(df: pd.DataFrame):
    st.write("Nội dung tab Thời tiết sẽ được cập nhật ở đây")
