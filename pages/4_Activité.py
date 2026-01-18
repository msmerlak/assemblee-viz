"""
Deputy Activity Metrics page - Success rates for amendments
Uses Polars + Parquet for fast data processing
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.api import AssembleeNationaleAPI
from src.utils.data_loader import OptimizedDataLoader

st.set_page_config(
    page_title="Activité des Députés - Assemblée Nationale",
    page_icon="📊",
    layout="wide",
)

# Initialize API client
if "api_client" not in st.session_state:
    st.session_state.api_client = AssembleeNationaleAPI(legislature=17)

st.title("📊 Activité des Députés")
st.markdown(f"**Législature**: {st.session_state.api_client.legislature}")

# Sidebar controls
with st.sidebar:
    st.markdown("### Informations")
    st.info("Chargement de tous les amendements de la législature.")


# Load data using optimized Polars + Parquet loader
@st.cache_data(ttl=3600)
def load_activity_data(legislature):
    """Load deputies and amendments data using Polars (much faster)"""
    loader = OptimizedDataLoader(legislature=legislature)

    # Load data as Polars DataFrames
    df_deputies_pl = loader.get_deputies_df()
    df_amendments_pl = loader.get_amendments_df(limit=None)  # All amendments

    # Compute stats using Polars (very fast)
    df_stats_pl = loader.compute_activity_stats(df_deputies_pl, df_amendments_pl)

    # Convert to pandas for Streamlit/Plotly compatibility
    df_deputies = df_deputies_pl.to_pandas()
    df_amendments = df_amendments_pl.to_pandas()
    df_stats = df_stats_pl.to_pandas()

    return df_deputies, df_amendments, df_stats


with st.spinner("Chargement des données d'activité..."):
    try:
        df_deputies, df_amendments, df_stats = load_activity_data(
            st.session_state.api_client.legislature
        )

        if df_deputies.empty or df_amendments.empty:
            st.warning("Données non disponibles")
            st.stop()

        # Calculate metrics per deputy
        st.markdown("## Statistiques globales")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Députés analysés", len(df_deputies))

        with col2:
            st.metric("Amendements analysés", len(df_amendments))

        with col3:
            # Count deputies with at least one amendment (from pre-computed stats)
            active_deputies = len(df_stats)
            st.metric("Députés actifs", active_deputies)

        with col4:
            # Average amendments per deputy
            avg_per_deputy = (
                len(df_amendments) / active_deputies if active_deputies > 0 else 0
            )
            st.metric("Moyenne par député", f"{avg_per_deputy:.1f}")

        st.divider()

        # Stats already computed by Polars - much faster!

        df_stats = df_stats.sort_values("total_amendements", ascending=False)

        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(
            ["🏆 Classement", "📈 Taux de succès", "📊 Par groupe", "🔍 Détails"]
        )

        with tab1:
            st.markdown("### Top 20 - Députés les plus actifs")
            st.markdown("Classement par nombre total d'amendements déposés")

            top20 = df_stats.head(20)

            # Bar chart
            fig = px.bar(
                top20,
                x="total_amendements",
                y="nom_complet",
                orientation="h",
                title="Nombre d'amendements par député (Top 20)",
                color="taux_succes",
                color_continuous_scale="RdYlGn",
                hover_data=["groupe_sigle", "adoptes", "rejetes"],
                labels={
                    "total_amendements": "Nombre d'amendements",
                    "nom_complet": "Député",
                    "taux_succes": "Taux de succès (%)",
                },
            )
            fig.update_layout(height=600, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch")

            # Display table
            display_cols = [
                "nom_complet",
                "groupe_sigle",
                "total_amendements",
                "adoptes",
                "rejetes",
                "taux_succes",
            ]
            display_names = {
                "nom_complet": "Député",
                "groupe_sigle": "Groupe",
                "total_amendements": "Total",
                "adoptes": "Adoptés",
                "rejetes": "Rejetés",
                "taux_succes": "Taux de succès (%)",
            }

            st.dataframe(
                top20[display_cols]
                .rename(columns=display_names)
                .style.format(
                    {
                        "Total": "{:,.0f}",
                        "Adoptés": "{:,.0f}",
                        "Rejetés": "{:,.0f}",
                        "Taux de succès (%)": "{:.1f}%",
                    }
                )
                .background_gradient(
                    subset=["Taux de succès (%)"], cmap="RdYlGn", vmin=0, vmax=100
                ),
                width="stretch",
                hide_index=True,
            )

        with tab2:
            st.markdown("### Taux de succès des amendements")
            st.markdown(
                "Pourcentage d'amendements adoptés parmi ceux examinés (min. 5 amendements)"
            )

            # Filter deputies with at least 5 examined amendments
            df_with_success = df_stats[df_stats["examines"] >= 5].copy()
            df_with_success = df_with_success.sort_values(
                "taux_succes", ascending=False
            )

            if not df_with_success.empty:
                # Top 20 by success rate
                top_success = df_with_success.head(20)

                col1, col2 = st.columns([2, 1])

                with col1:
                    # Bar chart
                    fig = px.bar(
                        top_success,
                        x="taux_succes",
                        y="nom_complet",
                        orientation="h",
                        title="Top 20 - Meilleurs taux de succès",
                        color="taux_succes",
                        color_continuous_scale="RdYlGn",
                        hover_data=[
                            "groupe_sigle",
                            "total_amendements",
                            "adoptes",
                            "examines",
                        ],
                        labels={
                            "taux_succes": "Taux de succès (%)",
                            "nom_complet": "Député",
                        },
                    )
                    fig.update_layout(
                        height=600, yaxis={"categoryorder": "total ascending"}
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    st.markdown("#### Statistiques")

                    st.metric(
                        "Taux de succès moyen",
                        f"{df_with_success['taux_succes'].mean():.1f}%",
                    )

                    st.metric(
                        "Taux médian", f"{df_with_success['taux_succes'].median():.1f}%"
                    )

                    high_success = len(
                        df_with_success[df_with_success["taux_succes"] >= 50]
                    )
                    st.metric(
                        "Députés avec >50%", f"{high_success}/{len(df_with_success)}"
                    )

                # Histogram of success rates
                st.markdown("#### Distribution des taux de succès")
                fig = px.histogram(
                    df_with_success,
                    x="taux_succes",
                    nbins=20,
                    title="Répartition des députés par taux de succès",
                    labels={
                        "taux_succes": "Taux de succès (%)",
                        "count": "Nombre de députés",
                    },
                )
                fig.update_traces(marker_color="#1f77b4")
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Pas assez de données pour calculer les taux de succès")

        with tab3:
            st.markdown("### Activité par groupe politique")

            if not df_stats.empty and "groupe_sigle" in df_stats.columns:
                # Aggregate by group
                group_stats = (
                    df_stats.groupby("groupe_sigle")
                    .agg(
                        {
                            "total_amendements": "sum",
                            "adoptes": "sum",
                            "rejetes": "sum",
                            "retires": "sum",
                            "examines": "sum",
                            "nom_complet": "count",
                        }
                    )
                    .rename(columns={"nom_complet": "nombre_deputes"})
                )

                group_stats["taux_succes"] = (
                    group_stats["adoptes"] / group_stats["examines"] * 100
                ).fillna(0)

                group_stats = group_stats.sort_values(
                    "total_amendements", ascending=False
                ).reset_index()

                col1, col2 = st.columns([1, 1])

                with col1:
                    # Bar chart - total amendments by group
                    fig = px.bar(
                        group_stats,
                        x="groupe_sigle",
                        y="total_amendements",
                        title="Nombre total d'amendements par groupe",
                        color="taux_succes",
                        color_continuous_scale="RdYlGn",
                        hover_data=["nombre_deputes", "adoptes", "rejetes"],
                        labels={
                            "groupe_sigle": "Groupe politique",
                            "total_amendements": "Nombre d'amendements",
                            "taux_succes": "Taux de succès (%)",
                        },
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Success rate by group
                    fig = px.bar(
                        group_stats.sort_values("taux_succes", ascending=False),
                        x="groupe_sigle",
                        y="taux_succes",
                        title="Taux de succès par groupe",
                        color="taux_succes",
                        color_continuous_scale="RdYlGn",
                        labels={
                            "groupe_sigle": "Groupe politique",
                            "taux_succes": "Taux de succès (%)",
                        },
                    )
                    st.plotly_chart(fig, width="stretch")

                # Display table
                display_names = {
                    "groupe_sigle": "Groupe",
                    "nombre_deputes": "Députés",
                    "total_amendements": "Total amendements",
                    "adoptes": "Adoptés",
                    "rejetes": "Rejetés",
                    "examines": "Examinés",
                    "taux_succes": "Taux de succès (%)",
                }

                st.dataframe(
                    group_stats[list(display_names.keys())]
                    .rename(columns=display_names)
                    .style.format(
                        {
                            "Députés": "{:,.0f}",
                            "Total amendements": "{:,.0f}",
                            "Adoptés": "{:,.0f}",
                            "Rejetés": "{:,.0f}",
                            "Examinés": "{:,.0f}",
                            "Taux de succès (%)": "{:.1f}%",
                        }
                    )
                    .background_gradient(
                        subset=["Taux de succès (%)"], cmap="RdYlGn", vmin=0, vmax=100
                    ),
                    width="stretch",
                    hide_index=True,
                )

        with tab4:
            st.markdown("### Recherche détaillée")

            col1, col2 = st.columns([2, 1])

            with col1:
                search_term = st.text_input(
                    "Rechercher un député", placeholder="Nom..."
                )

            with col2:
                if "groupe_sigle" in df_stats.columns:
                    groups = ["Tous"] + sorted(
                        df_stats["groupe_sigle"].dropna().unique().tolist()
                    )
                    selected_group = st.selectbox("Filtrer par groupe", groups)
                else:
                    selected_group = "Tous"

            # Apply filters
            filtered_stats = df_stats.copy()

            if search_term:
                mask = filtered_stats["nom_complet"].str.contains(
                    search_term, case=False, na=False
                )
                filtered_stats = filtered_stats[mask]

            if selected_group != "Tous":
                filtered_stats = filtered_stats[
                    filtered_stats["groupe_sigle"] == selected_group
                ]

            # Sort options
            sort_by = st.selectbox(
                "Trier par", ["Nombre d'amendements", "Taux de succès", "Nom"], index=0
            )

            if sort_by == "Nombre d'amendements":
                filtered_stats = filtered_stats.sort_values(
                    "total_amendements", ascending=False
                )
            elif sort_by == "Taux de succès":
                filtered_stats = filtered_stats.sort_values(
                    "taux_succes", ascending=False
                )
            else:
                filtered_stats = filtered_stats.sort_values("nom_complet")

            # Display results count
            st.caption(
                f"Affichage de {len(filtered_stats)} députés sur {len(df_stats)}"
            )

            # Display table
            display_cols = [
                "nom_complet",
                "groupe_sigle",
                "departement",
                "total_amendements",
                "adoptes",
                "rejetes",
                "retires",
                "irrecevables",
                "taux_succes",
            ]

            display_names = {
                "nom_complet": "Député",
                "groupe_sigle": "Groupe",
                "departement": "Département",
                "total_amendements": "Total",
                "adoptes": "Adoptés",
                "rejetes": "Rejetés",
                "retires": "Retirés",
                "irrecevables": "Irrecevables",
                "taux_succes": "Taux de succès (%)",
            }

            st.dataframe(
                filtered_stats[display_cols]
                .rename(columns=display_names)
                .style.format(
                    {
                        "Total": "{:,.0f}",
                        "Adoptés": "{:,.0f}",
                        "Rejetés": "{:,.0f}",
                        "Retirés": "{:,.0f}",
                        "Irrecevables": "{:,.0f}",
                        "Taux de succès (%)": "{:.1f}%",
                    }
                )
                .background_gradient(
                    subset=["Taux de succès (%)"], cmap="RdYlGn", vmin=0, vmax=100
                ),
                width="stretch",
                hide_index=True,
                height=600,
            )

            # Download button
            csv = (
                filtered_stats[display_cols]
                .rename(columns=display_names)
                .to_csv(index=False)
                .encode("utf-8")
            )
            st.download_button(
                label="Télécharger les données (CSV)",
                data=csv,
                file_name=f"activite_deputes_legislature_{st.session_state.api_client.legislature}.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        st.exception(e)
