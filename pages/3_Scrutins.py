"""
Votes (Scrutins) visualization page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.api import AssembleeNationaleAPI
from src.utils import votes_to_dataframe, calculate_vote_statistics

st.set_page_config(
    page_title="Scrutins - Assemblée Nationale", page_icon="🗳️", layout="wide"
)

# Initialize API client
if "api_client" not in st.session_state:
    st.session_state.api_client = AssembleeNationaleAPI(legislature=17)

st.title("🗳️ Scrutins")
st.markdown(f"**Législature**: {st.session_state.api_client.legislature}")


# Load data
@st.cache_data(ttl=3600)
def load_votes(legislature):
    """Load votes data with caching"""
    api = AssembleeNationaleAPI(legislature=legislature)
    votes = api.get_votes(limit=None)  # All votes
    return votes_to_dataframe(votes, legislature=legislature), votes


# Sidebar controls
with st.sidebar:
    st.markdown("### Informations")
    st.info("Chargement de tous les scrutins de la législature.")

with st.spinner("Chargement des scrutins..."):
    try:
        df_votes, raw_votes = load_votes(st.session_state.api_client.legislature)

        if df_votes.empty:
            st.warning("Aucun scrutin disponible pour cette législature.")
            st.stop()

        # Calculate statistics
        stats = calculate_vote_statistics(df_votes)

        # Display key metrics
        st.markdown("## Statistiques générales")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Nombre de scrutins", stats.get("total_votes", 0))

        with col2:
            if "average_voters" in stats:
                st.metric("Votants moyens", f"{int(stats['average_voters'])}")

        with col3:
            if stats.get("by_outcome"):
                adopted = stats["by_outcome"].get("adopté", 0) + stats[
                    "by_outcome"
                ].get("Adopté", 0)
                st.metric("Scrutins adoptés", adopted)

        with col4:
            if stats.get("by_outcome"):
                rejected = stats["by_outcome"].get("rejeté", 0) + stats[
                    "by_outcome"
                ].get("Rejeté", 0)
                st.metric("Scrutins rejetés", rejected)

        st.divider()

        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Résultats", "📅 Chronologie", "📈 Participation", "📋 Liste complète"]
        )

        with tab1:
            st.markdown("### Répartition des résultats de scrutins")

            if stats.get("by_outcome"):
                outcome_data = pd.DataFrame(
                    [
                        {"Résultat": k, "Nombre": v}
                        for k, v in stats["by_outcome"].items()
                    ]
                ).sort_values("Nombre", ascending=False)

                col1, col2 = st.columns([2, 1])

                with col1:
                    # Bar chart
                    fig = px.bar(
                        outcome_data,
                        x="Nombre",
                        y="Résultat",
                        orientation="h",
                        title="Nombre de scrutins par résultat",
                        color="Nombre",
                        color_continuous_scale="RdYlGn",
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Pie chart
                    fig = px.pie(
                        outcome_data,
                        values="Nombre",
                        names="Résultat",
                        title="Proportions",
                    )
                    st.plotly_chart(fig, width="stretch")

                # Display table
                total = outcome_data["Nombre"].sum()
                outcome_data["Pourcentage"] = (
                    outcome_data["Nombre"] / total * 100
                ).round(1)
                st.dataframe(
                    outcome_data.style.format(
                        {"Nombre": "{:,.0f}", "Pourcentage": "{:.1f}%"}
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Données de résultat non disponibles")

            # Vote breakdown analysis
            if all(
                col in df_votes.columns
                for col in ["nombre_pour", "nombre_contre", "nombre_abstentions"]
            ):
                st.markdown("### Répartition des votes")

                # Calculate totals
                total_pour = df_votes["nombre_pour"].sum()
                total_contre = df_votes["nombre_contre"].sum()
                total_abstentions = df_votes["nombre_abstentions"].sum()

                vote_breakdown = pd.DataFrame(
                    {
                        "Type": ["Pour", "Contre", "Abstentions"],
                        "Nombre": [total_pour, total_contre, total_abstentions],
                    }
                )

                col1, col2 = st.columns([1, 1])

                with col1:
                    # Pie chart
                    fig = px.pie(
                        vote_breakdown,
                        values="Nombre",
                        names="Type",
                        title="Répartition totale des votes",
                        color="Type",
                        color_discrete_map={
                            "Pour": "#2ca02c",
                            "Contre": "#d62728",
                            "Abstentions": "#ff7f0e",
                        },
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Metrics
                    st.markdown("#### Totaux")
                    total_votes = total_pour + total_contre + total_abstentions
                    st.metric("Total de votes", f"{int(total_votes):,}")
                    st.metric(
                        "Pour",
                        f"{int(total_pour):,}",
                        f"{total_pour/total_votes*100:.1f}%",
                    )
                    st.metric(
                        "Contre",
                        f"{int(total_contre):,}",
                        f"{total_contre/total_votes*100:.1f}%",
                    )
                    st.metric(
                        "Abstentions",
                        f"{int(total_abstentions):,}",
                        f"{total_abstentions/total_votes*100:.1f}%",
                    )

        with tab2:
            st.markdown("### Évolution des scrutins dans le temps")

            if "date" in df_votes.columns:
                # Filter out NaT dates
                votes_with_dates = df_votes.dropna(subset=["date"])

                if not votes_with_dates.empty:
                    # Group by month
                    votes_with_dates["mois"] = votes_with_dates["date"].dt.to_period(
                        "M"
                    )
                    monthly_counts = (
                        votes_with_dates.groupby("mois")
                        .size()
                        .reset_index(name="Nombre")
                    )
                    monthly_counts["mois"] = monthly_counts["mois"].dt.to_timestamp()

                    # Line chart
                    fig = px.line(
                        monthly_counts,
                        x="mois",
                        y="Nombre",
                        title="Nombre de scrutins par mois",
                        labels={"mois": "Mois", "Nombre": "Nombre de scrutins"},
                        markers=True,
                    )
                    fig.update_traces(line_color="#1f77b4", line_width=3)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, width="stretch")

                    # Additional analysis - votes by outcome over time
                    if "sort" in votes_with_dates.columns:
                        st.markdown("### Résultats des scrutins dans le temps")

                        monthly_outcomes = (
                            votes_with_dates.groupby(["mois", "sort"])
                            .size()
                            .reset_index(name="Nombre")
                        )
                        monthly_outcomes["mois"] = monthly_outcomes[
                            "mois"
                        ].dt.to_timestamp()

                        fig = px.bar(
                            monthly_outcomes,
                            x="mois",
                            y="Nombre",
                            color="sort",
                            title="Résultats des scrutins par mois",
                            labels={
                                "mois": "Mois",
                                "Nombre": "Nombre de scrutins",
                                "sort": "Résultat",
                            },
                            barmode="stack",
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, width="stretch")

                else:
                    st.info("Aucune date de scrutin disponible")
            else:
                st.info("Données de date non disponibles")

        with tab3:
            st.markdown("### Analyse de la participation")

            if "nombre_votants" in df_votes.columns:
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Histogram of voter counts
                    fig = px.histogram(
                        df_votes,
                        x="nombre_votants",
                        nbins=30,
                        title="Distribution du nombre de votants",
                        labels={
                            "nombre_votants": "Nombre de votants",
                            "count": "Fréquence",
                        },
                    )
                    fig.update_traces(marker_color="#9467bd")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    st.markdown("#### Statistiques")
                    st.metric("Moyenne", f"{df_votes['nombre_votants'].mean():.0f}")
                    st.metric("Médiane", f"{df_votes['nombre_votants'].median():.0f}")
                    st.metric("Maximum", f"{df_votes['nombre_votants'].max():.0f}")
                    st.metric("Minimum", f"{df_votes['nombre_votants'].min():.0f}")

                # Participation over time
                if "date" in df_votes.columns:
                    votes_with_dates = df_votes.dropna(
                        subset=["date", "nombre_votants"]
                    )

                    if not votes_with_dates.empty:
                        st.markdown("### Évolution de la participation")

                        # Group by month and calculate average participation
                        votes_with_dates["mois"] = votes_with_dates[
                            "date"
                        ].dt.to_period("M")
                        monthly_participation = (
                            votes_with_dates.groupby("mois")["nombre_votants"]
                            .mean()
                            .reset_index()
                        )
                        monthly_participation["mois"] = monthly_participation[
                            "mois"
                        ].dt.to_timestamp()

                        fig = px.line(
                            monthly_participation,
                            x="mois",
                            y="nombre_votants",
                            title="Nombre moyen de votants par mois",
                            labels={
                                "mois": "Mois",
                                "nombre_votants": "Nombre moyen de votants",
                            },
                            markers=True,
                        )
                        fig.update_traces(line_color="#e377c2", line_width=3)
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, width="stretch")
            else:
                st.info("Données de participation non disponibles")

        with tab4:
            st.markdown("### Liste complète des scrutins")

            # Add search and filter options
            col1, col2 = st.columns([3, 1])

            with col1:
                search_term = st.text_input(
                    "Rechercher un scrutin", placeholder="Titre, résultat..."
                )

            with col2:
                if "sort" in df_votes.columns:
                    outcomes = ["Tous"] + sorted(
                        df_votes["sort"].dropna().unique().tolist()
                    )
                    selected_outcome = st.selectbox("Filtrer par résultat", outcomes)
                else:
                    selected_outcome = "Tous"

            # Apply filters
            filtered_df = df_votes.copy()

            if search_term:
                mask = filtered_df["titre"].str.contains(
                    search_term, case=False, na=False
                ) | filtered_df["sort"].str.contains(search_term, case=False, na=False)
                filtered_df = filtered_df[mask]

            if selected_outcome != "Tous":
                filtered_df = filtered_df[filtered_df["sort"] == selected_outcome]

            # Sort by date
            if "date" in filtered_df.columns:
                filtered_df = filtered_df.sort_values("date", ascending=False)

            # Display results count
            st.caption(f"Affichage de {len(filtered_df)} scrutins sur {len(df_votes)}")

            # Select columns to display (include url for links)
            display_columns = [
                "numero",
                "date",
                "titre",
                "sort",
                "nombre_votants",
                "nombre_pour",
                "nombre_contre",
                "nombre_abstentions",
                "url",
            ]
            available_columns = [
                col for col in display_columns if col in filtered_df.columns
            ]

            if available_columns:
                # Rename columns for better display
                column_names = {
                    "numero": "N°",
                    "date": "Date",
                    "titre": "Titre",
                    "sort": "Résultat",
                    "nombre_votants": "Votants",
                    "nombre_pour": "Pour",
                    "nombre_contre": "Contre",
                    "nombre_abstentions": "Abstentions",
                    "url": "Lien",
                }

                display_df = filtered_df[available_columns].copy()

                # Format date column
                if "date" in display_df.columns:
                    display_df["date"] = display_df["date"].dt.strftime("%d/%m/%Y")
                
                display_df = display_df.rename(columns=column_names)

                st.dataframe(
                    display_df,
                    width="stretch",
                    hide_index=True,
                    height=600,
                    column_config={
                        "Lien": st.column_config.LinkColumn(
                            "Lien",
                            display_text="Voir ↗",
                            help="Ouvrir le scrutin sur assemblee-nationale.fr"
                        )
                    }
                )

                # Download button
                csv = display_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Télécharger les données (CSV)",
                    data=csv,
                    file_name=f"scrutins_legislature_{st.session_state.api_client.legislature}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("Aucune colonne à afficher")

    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        st.exception(e)
