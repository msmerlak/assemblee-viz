"""
Cache Management Utility for Assemblée Nationale Data
"""

import argparse
from src.api import AssembleeNationaleAPI
import json


def show_cache_info():
    """Display cache information"""
    api = AssembleeNationaleAPI()
    info = api.get_cache_info()

    print("\n" + "="*60)
    print("CACHE INFORMATION")
    print("="*60)
    print(f"Number of cached files: {info['files']}")
    print(f"Total size: {info['size_mb']} MB")
    if info['oldest']:
        print(f"Oldest cache entry: {info['oldest']}")
        print(f"Newest cache entry: {info['newest']}")
    else:
        print("Cache is empty")
    print("="*60 + "\n")


def clear_cache():
    """Clear all cached data"""
    api = AssembleeNationaleAPI()
    print("\nClearing cache...")
    api.clear_cache()
    print("✓ Cache cleared successfully\n")


def warm_cache(legislature: int = 17):
    """Pre-load all data into cache"""
    print(f"\n{'='*60}")
    print(f"WARMING CACHE FOR LEGISLATURE {legislature}")
    print(f"{'='*60}\n")

    api = AssembleeNationaleAPI(legislature=legislature)

    print("1/4 Loading deputies...")
    deputies = api.get_deputies()
    print(f"    ✓ Loaded {len(deputies)} deputies\n")

    print("2/4 Loading votes...")
    votes = api.get_votes(limit=100)
    print(f"    ✓ Loaded {len(votes)} votes\n")

    print("3/4 Loading legislative dossiers...")
    bills = api.get_bills(limit=100)
    print(f"    ✓ Loaded {len(bills)} bills\n")

    print("4/4 Loading amendments...")
    amendments = api.get_amendments(limit=1000)
    print(f"    ✓ Loaded {len(amendments)} amendments\n")

    print(f"{'='*60}")
    print("CACHE WARMING COMPLETE")
    print(f"{'='*60}\n")

    show_cache_info()


def main():
    parser = argparse.ArgumentParser(
        description='Manage local cache for Assemblée Nationale data'
    )

    parser.add_argument(
        'action',
        choices=['info', 'clear', 'warm'],
        help='Action to perform: info (show cache stats), clear (delete cache), warm (pre-load data)'
    )

    parser.add_argument(
        '--legislature',
        type=int,
        default=17,
        help='Legislature number (for warm action)'
    )

    args = parser.parse_args()

    if args.action == 'info':
        show_cache_info()
    elif args.action == 'clear':
        clear_cache()
        show_cache_info()
    elif args.action == 'warm':
        warm_cache(args.legislature)


if __name__ == '__main__':
    main()
