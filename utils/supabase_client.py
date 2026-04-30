import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """Returns a shared Supabase client for the current app process."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)
