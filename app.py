import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import unicodedata

# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="DEA-PROMETHEE Agency Performance App",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def normalize_text(text):
    text = str(text).replace('"', "").strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text.lower()


def clean_columns(df):
    df = df.copy()
    df.columns = [str(col).replace('"', "").strip() for col in df.columns]
    return df


def find_column(df, keywords):
    """
    Find a column containing all keywords after normalization.
    """
    for col in df.columns:
        normalized_col = normalize_text(col)
        if all(keyword in normalized_col for keyword in keywords):
            return col
    return None


@st.cache_data
def load_csv_file(file_path):
    """
    Load CSV files with French format:
    - semicolon separator
    - comma decimal separator
    """
    try:
        df = pd.read_csv(file_path, sep=";", decimal=",", encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=";", decimal=",", encoding="latin1")

    df = clean_columns(df)
    return df


# --------------------------------------------------
# Load data
# --------------------------------------------------

PRIVATE_DIR = Path("data_private")
PUBLIC_DIR = Path("data_public")

st.sidebar.title("Data version")

available_versions = ["Public anonymized data"]

if PRIVATE_DIR.exists():
    available_versions.append("Private jury data")

selected_version = st.sidebar.radio(
    "Select data version",
    available_versions
)

if selected_version == "Private jury data":
    DATA_DIR = PRIVATE_DIR
else:
    DATA_DIR = PUBLIC_DIR

dea_file = DATA_DIR / "annexe_2_classement_complet_dea.csv"
promethee_file = DATA_DIR / "annexe_3_classement_complet_promethee.csv"
typology_file = DATA_DIR / "annexe_4_typologie_finale_dea_promethee.csv"

dea_df = load_csv_file(dea_file)
promethee_df = load_csv_file(promethee_file)
typology_df = load_csv_file(typology_file)

# --------------------------------------------------
# Detect important columns
# --------------------------------------------------

classe_col = find_column(typology_df, ["classe"])
designation_col = find_column(typology_df, ["designation"])
upw_col = find_column(typology_df, ["upw"])

score_dea_col = find_column(typology_df, ["score", "dea"])
rang_dea_col = find_column(typology_df, ["rang", "dea"])
flux_net_col = find_column(typology_df, ["flux", "net"])
rang_promethee_col = find_column(typology_df, ["rang", "promethee"])
ecart_col = find_column(typology_df, ["ecart"])

profil_col = None
for col in typology_df.columns:
    if "profil" in normalize_text(col) or "typologie" in normalize_text(col) or "performance" in normalize_text(col):
        profil_col = col
        break

# --------------------------------------------------
# App title
# --------------------------------------------------

st.title("DEA-PROMETHEE Agency Performance App")
st.subheader("Interactive decision-support application for agency performance evaluation")

st.write(
    """
    This application presents the numerical results of a hybrid DEA-PROMETHEE approach
    used to evaluate, rank, and analyze the performance of agencies.
    """
)

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

st.sidebar.title("Filters")

if classe_col:
    selected_classes = st.sidebar.multiselect(
        "Select agency class",
        options=sorted(typology_df[classe_col].dropna().unique()),
        default=sorted(typology_df[classe_col].dropna().unique())
    )
else:
    selected_classes = []

filtered_df = typology_df.copy()

if classe_col and selected_classes:
    filtered_df = filtered_df[filtered_df[classe_col].isin(selected_classes)]

if upw_col:
    selected_upw = st.sidebar.multiselect(
        "Select UPW",
        options=sorted(filtered_df[upw_col].dropna().unique()),
        default=[]
    )

    if selected_upw:
        filtered_df = filtered_df[filtered_df[upw_col].isin(selected_upw)]

# --------------------------------------------------
# KPIs
# --------------------------------------------------

st.header("Performance Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total agencies", filtered_df.shape[0])

with col2:
    if classe_col:
        st.metric("Number of classes", filtered_df[classe_col].nunique())
    else:
        st.metric("Number of classes", "N/A")

with col3:
    if score_dea_col:
        st.metric("Average DEA score", f"{filtered_df[score_dea_col].mean():.3f}")
    else:
        st.metric("Average DEA score", "N/A")

with col4:
    if flux_net_col:
        st.metric("Average PROMETHEE net flow", f"{filtered_df[flux_net_col].mean():.3f}")
    else:
        st.metric("Average PROMETHEE net flow", "N/A")

# --------------------------------------------------
# Main charts
# --------------------------------------------------

st.header("Interactive Visual Analysis")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    if flux_net_col and designation_col:
        top_promethee = filtered_df.sort_values(by=flux_net_col, ascending=False).head(10)

        fig_top_promethee = px.bar(
            top_promethee,
            x=flux_net_col,
            y=designation_col,
            orientation="h",
            title="Top 10 Agencies by PROMETHEE Net Flow",
            labels={
                flux_net_col: "PROMETHEE Net Flow",
                designation_col: "Agency"
            }
        )
        fig_top_promethee.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_top_promethee, use_container_width=True)

with chart_col2:
    if score_dea_col and designation_col:
        top_dea = filtered_df.sort_values(by=score_dea_col, ascending=False).head(10)

        fig_top_dea = px.bar(
            top_dea,
            x=score_dea_col,
            y=designation_col,
            orientation="h",
            title="Top 10 Agencies by DEA Score",
            labels={
                score_dea_col: "DEA Score",
                designation_col: "Agency"
            }
        )
        fig_top_dea.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_top_dea, use_container_width=True)

# --------------------------------------------------
# Distribution charts
# --------------------------------------------------

dist_col1, dist_col2 = st.columns(2)

with dist_col1:
    if flux_net_col:
        fig_flux = px.histogram(
            filtered_df,
            x=flux_net_col,
            nbins=30,
            title="Distribution of PROMETHEE Net Flow",
            labels={flux_net_col: "PROMETHEE Net Flow"}
        )
        st.plotly_chart(fig_flux, use_container_width=True)

with dist_col2:
    if score_dea_col:
        fig_dea = px.histogram(
            filtered_df,
            x=score_dea_col,
            nbins=30,
            title="Distribution of DEA Scores",
            labels={score_dea_col: "DEA Score"}
        )
        st.plotly_chart(fig_dea, use_container_width=True)

# --------------------------------------------------
# Typology / profile analysis
# --------------------------------------------------

if profil_col:
    st.header("Agency Typology")

    profile_counts = filtered_df[profil_col].value_counts().reset_index()
    profile_counts.columns = [profil_col, "Count"]

    fig_profile = px.pie(
        profile_counts,
        names=profil_col,
        values="Count",
        title="Distribution of Agencies by Typology"
    )

    st.plotly_chart(fig_profile, use_container_width=True)

# --------------------------------------------------
# Ranking comparison
# --------------------------------------------------

if rang_dea_col and rang_promethee_col and designation_col:
    st.header("DEA vs PROMETHEE Ranking Comparison")

    comparison_df = filtered_df.copy()

    fig_rank = px.scatter(
        comparison_df,
        x=rang_dea_col,
        y=rang_promethee_col,
        hover_name=designation_col,
        color=classe_col if classe_col else None,
        title="Comparison between DEA Ranking and PROMETHEE Ranking",
        labels={
            rang_dea_col: "DEA Rank",
            rang_promethee_col: "PROMETHEE Rank"
        }
    )

    st.plotly_chart(fig_rank, use_container_width=True)

# --------------------------------------------------
# Detailed tables
# --------------------------------------------------

st.header("Detailed Results")

tab1, tab2, tab3 = st.tabs([
    "Final Typology",
    "DEA Ranking",
    "PROMETHEE Ranking"
])

with tab1:
    st.subheader("Final DEA-PROMETHEE Typology")
    st.dataframe(filtered_df, use_container_width=True)

with tab2:
    st.subheader("DEA Complete Ranking")
    st.dataframe(dea_df, use_container_width=True)

with tab3:
    st.subheader("PROMETHEE Complete Ranking")
    st.dataframe(promethee_df, use_container_width=True)

# --------------------------------------------------
# Download button
# --------------------------------------------------

st.header("Download Filtered Results")

csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered typology as CSV",
    data=csv,
    file_name="filtered_agency_typology.csv",
    mime="text/csv"
)
# --------------------------------------------------
# Interpretation
# --------------------------------------------------

st.header("Interpretation and Decision Support")

st.markdown(
    """
    This application provides an interactive overview of agency performance based on DEA and PROMETHEE results.

    The DEA score helps identify technically efficient agencies, while the PROMETHEE net flow provides a multicriteria ranking based on preference flows.

    The final typology highlights different agency profiles, including:
    
    - agencies performing well on both DEA and PROMETHEE dimensions;
    - agencies efficient in DEA but weaker from a multicriteria perspective;
    - agencies weaker in DEA but better ranked in PROMETHEE;
    - agencies requiring improvement on both dimensions.

    This tool can support decision-makers in identifying high-performing agencies, detecting agencies requiring improvement, and comparing results across agency classes and UPWs.
    """
)