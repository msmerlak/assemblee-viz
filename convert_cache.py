#!/usr/bin/env python
"""Convert JSON cache to Parquet format for faster loading"""

from src.utils.data_loader import OptimizedDataLoader
import time
import os

print("=" * 60)
print("CONVERTING JSON CACHE TO PARQUET")
print("=" * 60)

loader = OptimizedDataLoader(legislature=17)

print("\n1/3 Converting deputies...")
start = time.time()
df_deputies = loader.get_deputies_df()
print(f"    ✓ {len(df_deputies)} deputies - took {time.time()-start:.2f}s")

# Pre-cache common limit values
limits = [500, 1000, 2000, 5000, 10000]
for i, limit in enumerate(limits):
    print(f"\n{i+2}/{len(limits)+1} Converting amendments (limit={limit})...")
    start = time.time()
    df_amendments = loader.get_amendments_df(limit=limit)
    print(f"    ✓ {len(df_amendments)} amendments - took {time.time()-start:.2f}s")

print("\n" + "=" * 60)
print("PARQUET CACHE CREATED!")
print("=" * 60)

cache_dir = ".cache/parquet_data"
total = 0
for f in sorted(os.listdir(cache_dir)):
    path = os.path.join(cache_dir, f)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    total += size_mb
    print(f"  {f}: {size_mb:.2f} MB")
print(f"  TOTAL: {total:.2f} MB")

# Compare with JSON
json_dir = ".cache/assemblee_data"
if os.path.exists(json_dir):
    json_total = sum(
        os.path.getsize(os.path.join(json_dir, f)) for f in os.listdir(json_dir)
    ) / (1024 * 1024)
    print(f"\nJSON cache was: {json_total:.2f} MB")
    print(f"Parquet is {json_total/total:.1f}x smaller!")
