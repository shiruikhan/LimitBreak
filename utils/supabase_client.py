import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """Returns a shared Supabase client for the current app process."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


@st.cache_resource(show_spinner=False)
def get_supabase_admin() -> Client:
    """Returns a Supabase client with service_role key (admin operations only)."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_key"]
    return create_client(url, key)
