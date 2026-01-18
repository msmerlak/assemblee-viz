#!/usr/bin/env python
"""Test Parquet loading speed"""
import time
from src.utils.data_loader import OptimizedDataLoader

loader = OptimizedDataLoader(legislature=17)

print("Testing load times with Parquet cache...")
print()

start = time.time()
df_deputies = loader.get_deputies_df()
print(f"Deputies: {time.time()-start:.3f}s ({len(df_deputies)} rows)")

start = time.time()
df_amendments = loader.get_amendments_df(limit=2000)
print(f"Amendments (2000): {time.time()-start:.3f}s ({len(df_amendments)} rows)")

start = time.time()
df_stats = loader.compute_activity_stats(df_deputies, df_amendments)
print(f"Stats computation: {time.time()-start:.3f}s ({len(df_stats)} rows)")

print()
print("Total would be ~instant for Activity page!")
