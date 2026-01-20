"""
Bills and legislation (Législation) visualization page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.data_loader import OptimizedDataLoader
from src.utils import bills_to_dataframe

st.set_page_config(
    page_title="Législation - Assemblée Nationale", page_icon="📜", layout="wide"
)

# Initialize loader
legislature = 17

st.title("📜 Législation")
st.markdown(f"**Législature**: {legislature}")


# Load data
@st.cache_data(ttl=3600)
def load_bills(legislature):
    """Load all bills data with Parquet caching"""
    loader = OptimizedDataLoader(legislature=legislature)
    df = loader.get_bills_df()
    # Convert to pandas for compatibility with existing code
    return df.to_pandas(), df.to_dicts()


# Sidebar controls
with st.sidebar:
    st.markdown("### Informations")
    st.info("Chargement de tous les dossiers législatifs de la législature.")

with st.spinner("Chargement des dossiers législatifs..."):
    try:
        df_bills, raw_bills = load_bills(legislature)

        if df_bills.empty:
            st.warning("Aucun dossier législatif disponible pour cette législature.")
            st.stop()

        # Display key metrics
        st.markdown("## Statistiques générales")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Nombre de dossiers", len(df_bills))

        with col2:
            if "type" in df_bills.columns:
                unique_types = df_bills["type"].nunique()
                st.metric("Types de textes", unique_types)

        with col3:
            if "statut" in df_bills.columns and not df_bills["statut"].isna().all():
                status_counts = df_bills["statut"].value_counts()
                if len(status_counts) > 0:
                    st.metric("Statut principal", status_counts.index[0])

        with col4:
            if "date_depot" in df_bills.columns:
                recent_bills = df_bills[
                    df_bills["date_depot"] > (datetime.now() - timedelta(days=30))
                ]
                st.metric("Dépôts récents (30j)", len(recent_bills))

        st.divider()

        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Par type", "📅 Chronologie", "📈 Par statut", "📋 Liste complète"]
        )

        with tab1:
            st.markdown("### Répartition des dossiers par type")

            if "type" in df_bills.columns and not df_bills["type"].isna().all():
                type_counts = df_bills["type"].value_counts()
                type_data = pd.DataFrame(
                    {"Type": type_counts.index, "Nombre": type_counts.values}
                )

                col1, col2 = st.columns([2, 1])

                with col1:
                    # Bar chart
                    fig = px.bar(
                        type_data,
                        x="Nombre",
                        y="Type",
                        orientation="h",
                        title="Nombre de dossiers par type",
                        color="Nombre",
                        color_continuous_scale="Purples",
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Display table
                    st.markdown("#### Détails")
                    total = type_data["Nombre"].sum()
                    type_data["Pourcentage"] = (
                        type_data["Nombre"] / total * 100
                    ).round(1)
                    st.dataframe(
                        type_data.style.format(
                            {"Nombre": "{:,.0f}", "Pourcentage": "{:.1f}%"}
                        ),
                        width="stretch",
                        hide_index=True,
                    )
            else:
                st.info("Données de type non disponibles")

        with tab2:
            st.markdown("### Évolution des dépôts dans le temps")

            if "date_depot" in df_bills.columns:
                # Filter out NaT dates
                bills_with_dates = df_bills.dropna(subset=["date_depot"])

                if not bills_with_dates.empty:
                    # Group by month
                    bills_with_dates["mois"] = bills_with_dates[
                        "date_depot"
                    ].dt.to_period("M")
                    monthly_counts = (
                        bills_with_dates.groupby("mois")
                        .size()
                        .reset_index(name="Nombre")
                    )
                    monthly_counts["mois"] = monthly_counts["mois"].dt.to_timestamp()

                    # Line chart
                    fig = px.line(
                        monthly_counts,
                        x="mois",
                        y="Nombre",
                        title="Nombre de dossiers déposés par mois",
                        labels={"mois": "Mois", "Nombre": "Nombre de dossiers"},
                        markers=True,
                    )
                    fig.update_traces(line_color="#2ca02c", line_width=3)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, width="stretch")

                    # Additional statistics
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        avg_per_month = monthly_counts["Nombre"].mean()
                        st.metric("Moyenne par mois", f"{avg_per_month:.1f}")

                    with col2:
                        max_month = monthly_counts.loc[
                            monthly_counts["Nombre"].idxmax()
                        ]
                        st.metric(
                            "Mois le plus actif",
                            max_month["mois"].strftime("%B %Y"),
                            delta=f"{max_month['Nombre']} dossiers",
                        )

                    with col3:
                        total_days = (
                            bills_with_dates["date_depot"].max()
                            - bills_with_dates["date_depot"].min()
                        ).days
                        if total_days > 0:
                            avg_per_day = len(bills_with_dates) / total_days
                            st.metric("Moyenne par jour", f"{avg_per_day:.2f}")

                    # Display table
                    with st.expander("Voir les données mensuelles"):
                        display_monthly = monthly_counts.copy()
                        display_monthly["Mois"] = display_monthly["mois"].dt.strftime(
                            "%B %Y"
                        )
                        display_monthly = display_monthly[
                            ["Mois", "Nombre"]
                        ].sort_values("Mois", ascending=False)
                        st.dataframe(display_monthly, width="stretch", hide_index=True)
                else:
                    st.info("Aucune date de dépôt disponible")
            else:
                st.info("Données de date non disponibles")

        with tab3:
            st.markdown("### Répartition par statut")

            if "statut" in df_bills.columns and not df_bills["statut"].isna().all():
                status_counts = df_bills["statut"].value_counts()
                status_data = pd.DataFrame(
                    {"Statut": status_counts.index, "Nombre": status_counts.values}
                )

                col1, col2 = st.columns([1, 1])

                with col1:
                    # Pie chart
                    fig = px.pie(
                        status_data,
                        values="Nombre",
                        names="Statut",
                        title="Distribution par statut",
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Bar chart
                    fig = px.bar(
                        status_data,
                        x="Nombre",
                        y="Statut",
                        orientation="h",
                        color="Nombre",
                        color_continuous_scale="Reds",
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, width="stretch")

                # Display table
                total = status_data["Nombre"].sum()
                status_data["Pourcentage"] = (
                    status_data["Nombre"] / total * 100
                ).round(1)
                st.dataframe(
                    status_data.style.format(
                        {"Nombre": "{:,.0f}", "Pourcentage": "{:.1f}%"}
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Données de statut non disponibles")

        with tab4:
            st.markdown("### Liste complète des dossiers législatifs")

            # Add search and filter options
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                search_term = st.text_input(
                    "Rechercher un dossier", placeholder="Titre, type, statut..."
                )

            with col2:
                if "type" in df_bills.columns:
                    types = ["Tous"] + sorted(
                        df_bills["type"].dropna().unique().tolist()
                    )
                    selected_type = st.selectbox("Filtrer par type", types)
                else:
                    selected_type = "Tous"

            with col3:
                if "statut" in df_bills.columns:
                    statuses = ["Tous"] + sorted(
                        df_bills["statut"].dropna().unique().tolist()
                    )
                    selected_status = st.selectbox("Filtrer par statut", statuses)
                else:
                    selected_status = "Tous"

            # Apply filters
            filtered_df = df_bills.copy()

            if search_term:
                mask = (
                    filtered_df["titre"].str.contains(search_term, case=False, na=False)
                    | filtered_df["type"].str.contains(
                        search_term, case=False, na=False
                    )
                    | filtered_df["statut"].str.contains(
                        search_term, case=False, na=False
                    )
                )
                filtered_df = filtered_df[mask]

            if selected_type != "Tous":
                filtered_df = filtered_df[filtered_df["type"] == selected_type]

            if selected_status != "Tous":
                filtered_df = filtered_df[filtered_df["statut"] == selected_status]

            # Sort by date
            if "date_depot" in filtered_df.columns:
                filtered_df = filtered_df.sort_values("date_depot", ascending=False)

            # Display results count
            st.caption(f"Affichage de {len(filtered_df)} dossiers sur {len(df_bills)}")

            # Select columns to display (include url for links)
            display_columns = ["titre", "type", "date_depot", "statut", "url"]
            available_columns = [
                col for col in display_columns if col in filtered_df.columns
            ]

            if available_columns:
                # Rename columns for better display
                column_names = {
                    "titre": "Titre",
                    "type": "Type",
                    "date_depot": "Date de dépôt",
                    "statut": "Statut",
                    "url": "Lien",
                }

                display_df = filtered_df[available_columns].copy()

                # Format date column
                if "date_depot" in display_df.columns:
                    display_df["date_depot"] = display_df["date_depot"].dt.strftime(
                        "%d/%m/%Y"
                    )

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
                            help="Ouvrir le dossier sur assemblee-nationale.fr",
                        )
                    },
                )

                # Download button
                csv = display_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Télécharger les données (CSV)",
                    data=csv,
                    file_name=f"legislation_legislature_{legislature}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("Aucune colonne à afficher")

    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        st.exception(e)
