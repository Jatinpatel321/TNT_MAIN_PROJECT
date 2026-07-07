import streamlit as st
from google.adk.agents import ADKAgent
from google.adk.web import ADKWebUI

ADK_API_URL = "http://localhost:8000"

st.title("ADK Agent Interface")
st.write(f"ADK API URL: {ADK_API_URL}")
