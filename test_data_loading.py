"""
Test script to verify data loading from Assemblée Nationale API
"""

from src.api import AssembleeNationaleAPI
from src.utils import deputies_to_dataframe, votes_to_dataframe

def test_deputies():
    print("=" * 60)
    print("Testing Deputies Loading")
    print("=" * 60)
    api = AssembleeNationaleAPI(legislature=17)
    deputies = api.get_deputies()
    print(f"✓ Loaded {len(deputies)} deputies")

    df = deputies_to_dataframe(deputies)
    print(f"✓ Converted to DataFrame: {len(df)} rows, {len(df.columns)} columns")
    print(f"✓ Columns: {list(df.columns)}")

    # Check data quality
    with_groups = df['groupe_sigle'].notna().sum()
    with_dept = df['departement'].notna().sum()
    print(f"✓ Deputies with political groups: {with_groups}/{len(df)}")
    print(f"✓ Deputies with departments: {with_dept}/{len(df)}")
    print()
    return True

def test_votes():
    print("=" * 60)
    print("Testing Votes Loading")
    print("=" * 60)
    api = AssembleeNationaleAPI(legislature=17)
    try:
        votes = api.get_votes(limit=50)
        print(f"✓ Loaded {len(votes)} votes")

        df = votes_to_dataframe(votes)
        print(f"✓ Converted to DataFrame: {len(df)} rows, {len(df.columns)} columns")
        print()
        return True
    except Exception as e:
        print(f"✗ Error loading votes: {e}")
        print("  (This is expected if votes data structure differs)")
        print()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASSEMBLÉE NATIONALE DATA LOADING TEST")
    print("=" * 60 + "\n")

    results = []
    results.append(("Deputies", test_deputies()))
    results.append(("Votes", test_votes()))

    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20s} {status}")
    print()

    all_passed = all(p for _, p in results)
    if all_passed:
        print("✓ All critical tests passed! The application should work.")
    else:
        print("⚠ Some tests failed, but deputies data is working.")
    print()
