import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client:
    """Creates a fresh Supabase client. Credentials from st.secrets (never from .env)."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)
