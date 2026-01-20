"""
Utility functions for processing Assemblée Nationale data
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter


def deputies_to_dataframe(deputies: List[Dict]) -> pd.DataFrame:
    """
    Convert list of deputies to a structured DataFrame

    Args:
        deputies: List of deputy dictionaries from API

    Returns:
        DataFrame with deputy information
    """
    if not deputies:
        return pd.DataFrame()

    processed = []
    for deputy in deputies:
        # Extract nested information safely
        processed.append(
            {
                "uid": deputy.get("uid", ""),
                "nom": deputy.get("nom", ""),
                "prenom": deputy.get("prenom", ""),
                "nom_complet": f"{deputy.get('prenom', '')} {deputy.get('nom', '')}",
                "sexe": deputy.get("sexe", ""),
                "date_naissance": deputy.get("dateNaissance", ""),
                "lieu_naissance": deputy.get("lieuNaissance", ""),
                "profession": deputy.get("profession", ""),
                "departement": (
                    deputy.get("departement", {}).get("nom", "")
                    if isinstance(deputy.get("departement"), dict)
                    else ""
                ),
                "circonscription": (
                    deputy.get("circonscription", {}).get("numero", "")
                    if isinstance(deputy.get("circonscription"), dict)
                    else ""
                ),
                "groupe": (
                    deputy.get("groupe", {}).get("libelle", "")
                    if isinstance(deputy.get("groupe"), dict)
                    else ""
                ),
                "groupe_sigle": (
                    deputy.get("groupe", {}).get("sigle", "")
                    if isinstance(deputy.get("groupe"), dict)
                    else ""
                ),
            }
        )

    df = pd.DataFrame(processed)

    # Convert date columns
    if "date_naissance" in df.columns:
        df["date_naissance"] = pd.to_datetime(df["date_naissance"], errors="coerce")

    return df


def bills_to_dataframe(bills: List[Dict]) -> pd.DataFrame:
    """
    Convert list of bills to a structured DataFrame

    Args:
        bills: List of bill dictionaries from API

    Returns:
        DataFrame with bill information
    """
    if not bills:
        return pd.DataFrame()

    processed = []
    for bill in bills:
        uid = bill.get("uid", "")
        legislature = bill.get("legislature", "")
        # Build URL to the official Assemblée Nationale page
        url = (
            f"https://www.assemblee-nationale.fr/dyn/{legislature}/dossiers/{uid}"
            if uid and legislature
            else ""
        )

        processed.append(
            {
                "uid": uid,
                "titre": bill.get("titre", ""),
                "type": bill.get("type", ""),
                "date_depot": bill.get("dateDepot", ""),
                "statut": bill.get("statut", ""),
                "legislature": legislature,
                "url": url,
            }
        )

    df = pd.DataFrame(processed)

    # Convert date columns
    if "date_depot" in df.columns:
        df["date_depot"] = pd.to_datetime(df["date_depot"], errors="coerce")

    return df


def votes_to_dataframe(votes: List[Dict], legislature: int = 17) -> pd.DataFrame:
    """
    Convert list of votes to a structured DataFrame

    Args:
        votes: List of vote dictionaries from API or Parquet cache
        legislature: Legislature number for URL construction

    Returns:
        DataFrame with vote information
    """
    if not votes:
        return pd.DataFrame()

    processed = []
    for vote in votes:
        uid = vote.get("uid", "")
        # Build URL to the official Assemblée Nationale page
        url = (
            f"https://www.assemblee-nationale.fr/dyn/{legislature}/scrutins/{uid}"
            if uid
            else ""
        )

        # Handle both nested (API) and flat (Parquet) formats
        if "decompte" in vote and isinstance(vote.get("decompte"), dict):
            # Nested format from API
            pour = vote["decompte"].get("pour", 0)
            contre = vote["decompte"].get("contre", 0)
            abstention = vote["decompte"].get("abstention", 0)
        else:
            # Flat format from Parquet
            pour = vote.get("pour", 0)
            contre = vote.get("contre", 0)
            abstention = vote.get("abstention", 0)

        processed.append(
            {
                "uid": uid,
                "numero": vote.get("numero", ""),
                "date": vote.get("dateScrutin", ""),
                "titre": vote.get("titre", ""),
                "sort": vote.get("sort", ""),
                "nombre_votants": vote.get("nombreVotants", 0),
                "nombre_pour": pour,
                "nombre_contre": contre,
                "nombre_abstentions": abstention,
                "url": url,
            }
        )

    df = pd.DataFrame(processed)

    # Convert date columns
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


def calculate_deputy_statistics(deputies_df: pd.DataFrame) -> Dict:
    """
    Calculate various statistics about deputies

    Args:
        deputies_df: DataFrame with deputy information

    Returns:
        Dictionary with statistics
    """
    if deputies_df.empty:
        return {}

    stats = {
        "total_deputies": len(deputies_df),
        "by_gender": (
            deputies_df["sexe"].value_counts().to_dict()
            if "sexe" in deputies_df.columns
            else {}
        ),
        "by_group": (
            deputies_df["groupe_sigle"].value_counts().to_dict()
            if "groupe_sigle" in deputies_df.columns
            else {}
        ),
        "by_department": (
            deputies_df["departement"].value_counts().head(10).to_dict()
            if "departement" in deputies_df.columns
            else {}
        ),
    }

    # Calculate average age if birth dates are available
    if "date_naissance" in deputies_df.columns:
        current_year = datetime.now().year
        birth_years = deputies_df["date_naissance"].dt.year.dropna()
        if not birth_years.empty:
            stats["average_age"] = round(current_year - birth_years.mean(), 1)

    return stats


def calculate_vote_statistics(votes_df: pd.DataFrame) -> Dict:
    """
    Calculate various statistics about votes

    Args:
        votes_df: DataFrame with vote information

    Returns:
        Dictionary with statistics
    """
    if votes_df.empty:
        return {}

    stats = {
        "total_votes": len(votes_df),
        "by_outcome": (
            votes_df["sort"].value_counts().to_dict()
            if "sort" in votes_df.columns
            else {}
        ),
    }

    # Calculate participation statistics
    if "nombre_votants" in votes_df.columns:
        stats["average_voters"] = round(votes_df["nombre_votants"].mean(), 0)

    return stats


def filter_by_date_range(
    df: pd.DataFrame,
    date_column: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Filter DataFrame by date range

    Args:
        df: DataFrame to filter
        date_column: Name of the date column
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Filtered DataFrame
    """
    if df.empty or date_column not in df.columns:
        return df

    filtered_df = df.copy()

    if start_date:
        filtered_df = filtered_df[filtered_df[date_column] >= start_date]

    if end_date:
        filtered_df = filtered_df[filtered_df[date_column] <= end_date]

    return filtered_df
