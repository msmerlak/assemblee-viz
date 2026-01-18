"""
Optimized data loader using Polars and Parquet caching.
This provides much faster loading compared to JSON caching.
"""

import polars as pl
import time
import json
import zipfile
import io
import requests
from pathlib import Path
from typing import Optional


class OptimizedDataLoader:
    """Fast data loader with Parquet caching and Polars processing"""

    BASE_URL = "https://data.assemblee-nationale.fr/static/openData/repository"
    CACHE_DIR = Path(".cache/parquet_data")
    JSON_CACHE_DIR = Path(".cache/assemblee_data")  # Existing JSON cache
    CACHE_TTL = 86400  # 24 hours

    def __init__(self, legislature: int = 17):
        self.legislature = legislature
        self.session = requests.Session()
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, name: str, limit: Optional[int] = None) -> Path:
        """Generate cache path for processed data"""
        suffix = f"_{limit}" if limit else ""
        return self.CACHE_DIR / f"{self.legislature}_{name}{suffix}.parquet"

    def _get_json_cache_path(self, url: str) -> Path:
        """Get path to existing JSON cache"""
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.JSON_CACHE_DIR / f"{url_hash}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache exists and is fresh"""
        if not cache_path.exists():
            return False
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.CACHE_TTL

    def _load_from_json_cache(self, url: str) -> Optional[list]:
        """Load from existing JSON cache if available (with progress)"""
        json_path = self._get_json_cache_path(url)
        if json_path.exists():
            size_mb = json_path.stat().st_size / (1024 * 1024)
            print(f"Loading from JSON cache: {json_path.name} ({size_mb:.0f} MB)...")
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _download_zip(self, url: str) -> list:
        """Download and extract ZIP file"""
        print(f"Downloading from: {url}")
        response = self.session.get(url, timeout=120)
        response.raise_for_status()

        data = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    with zf.open(name) as f:
                        data.append(json.loads(f.read()))
        return data

    def get_amendments_df(self, limit: Optional[int] = None) -> pl.DataFrame:
        """
        Get amendments as a Polars DataFrame with Parquet caching.
        Much faster than JSON for large datasets.

        Args:
            limit: Max number of amendments to process. None = all amendments.
        """
        cache_path = self._get_cache_path("amendments", limit if limit else "all")

        # Try loading from Parquet cache
        if self._is_cache_valid(cache_path):
            print("Loading amendments from Parquet cache...")
            return pl.read_parquet(cache_path)

        # Try existing JSON cache first, then download
        url = f"{self.BASE_URL}/{self.legislature}/loi/amendements_div_legis/Amendements.json.zip"
        print("Fetching amendments data...")

        raw_data = self._load_from_json_cache(url)
        if raw_data is None:
            raw_data = self._download_zip(url)

        # Helper to safely extract string value
        def safe_str(val):
            if val is None:
                return ""
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return val.get("#text", val.get("libelle", str(val)))
            return str(val)

        # Process amendments
        items_to_process = raw_data if limit is None else raw_data[:limit]
        print(f"Processing {len(items_to_process)} amendments...")
        amendments = []
        for item in items_to_process:
            if "amendement" not in item:
                continue

            amdt = item["amendement"]
            signataires = amdt.get("signataires", {}) or {}
            auteur = signataires.get("auteur", {}) or {}
            cosignataires = signataires.get("cosignataires", {}) or {}
            cosig_refs = cosignataires.get("acteurRef", [])
            if not isinstance(cosig_refs, list):
                cosig_refs = [cosig_refs] if cosig_refs else []

            cycle = amdt.get("cycleDeVie", {}) or {}
            etat = cycle.get("etatDesTraitements", {})
            if isinstance(etat, dict):
                etat = etat.get("etat", {}) or {}
            else:
                etat = {}

            # sort can be a string or a dict
            sort_raw = cycle.get("sort", "")
            if isinstance(sort_raw, dict):
                sort_libelle = safe_str(sort_raw.get("libelle", ""))
                sort_code = safe_str(sort_raw.get("code", ""))
            else:
                sort_libelle = safe_str(sort_raw)
                sort_code = safe_str(sort_raw)

            amendments.append(
                {
                    "uid": safe_str(amdt.get("uid", "")),
                    "numero": safe_str(
                        amdt.get("identification", {}).get("numeroLong", "")
                    ),
                    "dateDepot": safe_str(cycle.get("dateDepot", "")),
                    "auteur": safe_str(auteur.get("acteurRef", "")),
                    "nombreCosignataires": len(cosig_refs),
                    "etat": (
                        safe_str(etat.get("libelle", ""))
                        if isinstance(etat, dict)
                        else ""
                    ),
                    "etatCode": (
                        safe_str(etat.get("code", "")) if isinstance(etat, dict) else ""
                    ),
                    "sort": sort_libelle,
                    "sortCode": sort_code,
                    "texteLegislatifRef": safe_str(amdt.get("texteLegislatifRef", "")),
                }
            )

        # Create DataFrame and save to Parquet
        df = pl.DataFrame(amendments)

        # Save to Parquet cache
        df.write_parquet(cache_path)
        print(f"Cached {len(df)} amendments to Parquet ({cache_path.name})")

        return df

    def get_deputies_df(self) -> pl.DataFrame:
        """Get deputies as a Polars DataFrame with Parquet caching."""
        cache_path = self._get_cache_path("deputies")

        if self._is_cache_valid(cache_path):
            print("Loading deputies from Parquet cache...")
            return pl.read_parquet(cache_path)

        url = f"{self.BASE_URL}/{self.legislature}/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
        print("Fetching deputies data...")

        raw_data = self._load_from_json_cache(url)
        if raw_data is None:
            raw_data = self._download_zip(url)

        # Build organe lookup
        organe_map = {}
        for item in raw_data:
            if "organe" in item:
                organe = item["organe"]
                uid = organe.get("uid", "")
                if uid:
                    organe_map[uid] = organe

        # Process deputies
        deputies = []
        for item in raw_data:
            if "acteur" not in item:
                continue

            acteur = item["acteur"]
            uid = acteur.get("uid", {})
            if isinstance(uid, dict):
                uid = uid.get("#text", "")

            deputy = {
                "uid": uid,
                "civ": acteur.get("etatCivil", {}).get("ident", {}).get("civ", ""),
                "prenom": acteur.get("etatCivil", {})
                .get("ident", {})
                .get("prenom", ""),
                "nom": acteur.get("etatCivil", {}).get("ident", {}).get("nom", ""),
                "profession": acteur.get("profession", {}).get("libelleCourant", ""),
                "groupe_sigle": "",
                "groupe_libelle": "",
                "departement": "",
                "circonscription": "",
            }

            # Extract from mandats
            mandats = acteur.get("mandats", {}).get("mandat", [])
            if not isinstance(mandats, list):
                mandats = [mandats]

            for mandat in mandats:
                type_organe = mandat.get("typeOrgane", "")

                if type_organe == "ASSEMBLEE":
                    election = mandat.get("election", {})
                    lieu = election.get("lieu", {})
                    deputy["departement"] = lieu.get("departement", "")
                    deputy["circonscription"] = lieu.get("numCirco", "")

                elif type_organe == "GP":
                    organe_ref = mandat.get("organes", {}).get("organeRef", "")
                    if organe_ref and organe_ref in organe_map:
                        organe = organe_map[organe_ref]
                        deputy["groupe_sigle"] = organe.get("libelleAbrev", "")
                        deputy["groupe_libelle"] = organe.get("libelle", "")

            deputies.append(deputy)

        df = pl.DataFrame(deputies)
        df = df.with_columns(
            [(pl.col("prenom") + " " + pl.col("nom")).alias("nom_complet")]
        )

        df.write_parquet(cache_path)
        print(f"Cached {len(df)} deputies to Parquet")

        return df

    def compute_activity_stats(
        self, df_deputies: pl.DataFrame, df_amendments: pl.DataFrame
    ) -> pl.DataFrame:
        """
        Compute deputy activity statistics using Polars.
        This is MUCH faster than pandas for this type of aggregation.
        """
        # Add boolean columns for outcomes (vectorized)
        df_amendments = df_amendments.with_columns(
            [
                pl.col("sort").str.contains("(?i)adopté").alias("is_adopted"),
                pl.col("sort").str.contains("(?i)rejet").alias("is_rejected"),
                pl.col("etat").str.contains("(?i)retiré").alias("is_withdrawn"),
                pl.col("etat").str.contains("(?i)irrecevable").alias("is_inadmissible"),
            ]
        )

        # Aggregate by author
        stats = df_amendments.group_by("auteur").agg(
            [
                pl.len().alias("total_amendements"),
                pl.col("is_adopted").sum().alias("adoptes"),
                pl.col("is_rejected").sum().alias("rejetes"),
                pl.col("is_withdrawn").sum().alias("retires"),
                pl.col("is_inadmissible").sum().alias("irrecevables"),
            ]
        )

        # Calculate derived columns
        stats = stats.with_columns(
            [(pl.col("adoptes") + pl.col("rejetes")).alias("examines")]
        ).with_columns(
            [
                (pl.col("adoptes") / pl.col("examines") * 100)
                .fill_null(0)
                .alias("taux_succes")
            ]
        )

        # Join with deputies
        result = df_deputies.join(
            stats, left_on="uid", right_on="auteur", how="inner"
        ).sort("total_amendements", descending=True)

        return result

    def clear_cache(self):
        """Clear Parquet cache"""
        import shutil

        if self.CACHE_DIR.exists():
            shutil.rmtree(self.CACHE_DIR)
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            print("Parquet cache cleared")
