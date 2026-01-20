# Local Caching System

## Overview

The application uses a **two-layer caching system** that dramatically improves performance:

1. **JSON Cache**: Raw API responses stored on disk (legacy, still used for debates)
2. **Parquet Cache**: Optimized columnar format for DataFrames (deputies, amendments, bills, votes)

### Performance Improvement

**🚀 20-50x faster loading times!**

- **First load**: ~2-5 seconds (downloads from API, converts to Parquet)
- **Cached load**: ~0.05-0.1 seconds (loads from Parquet)
- **Speedup**: 20-50x faster with cache

## How It Works

### Automatic Caching

When data is requested:
1. **Check Parquet cache**: Look for `.parquet` file in `.cache/parquet/`
2. **Check JSON cache**: Fall back to JSON in `.cache/assemblee_data/`
3. **Download if needed**: Fetch from API and create Parquet cache

### Cache Locations

```
.cache/
├── parquet/                                    # Optimized Parquet cache
│   ├── deputies_17.parquet                     # Deputies DataFrame
│   ├── amendments_17.parquet                   # Amendments DataFrame
│   ├── bills_17.parquet                        # Bills DataFrame
│   └── votes_17.parquet                        # Votes DataFrame
│
├── assemblee_data/                             # JSON cache (legacy)
│   ├── 2fb0b6d8935e7f28055ac4f245777c8b.json  # Deputies raw
│   ├── 11a7540cad62350dfef4599549cb18e4.json  # Votes raw
│   ├── 96de91112dfdd7ab7d3de73db0c58ec4.json  # Bills raw
│   ├── 90d24d99b1d61f0e140b489c37b6a158.json  # Amendments raw
│   ├── a0f50bb833c899a024f1747b006eea38.json  # Debates metadata
│   └── syseron_17.xml.zip                      # Debate transcripts XML
│
└── (both directories are in .gitignore)
```

### Cache Duration

- **TTL (Time To Live)**: 24 hours
- **Auto-refresh**: Cache expires after 24 hours
- **Manual refresh**: Use `cache_manager.py` to clear cache

## Cache Management

### Command Line Tool

A `cache_manager.py` script is provided for cache management:

#### Show Cache Info
```bash
python cache_manager.py info
```

Output:
```
============================================================
CACHE INFORMATION
============================================================
Number of cached files: 4
Total size: 741.57 MB
Oldest cache entry: 2026-01-19T00:12:04
Newest cache entry: 2026-01-19T00:13:37
============================================================
```

#### Clear Cache
```bash
python cache_manager.py clear
```

Removes all cached data. Next load will download fresh data.

#### Warm Cache (Pre-load Data)
```bash
python cache_manager.py warm --legislature 17
```

Pre-downloads all data for faster first use:
- Deputies (575 entries, ~12 MB)
- Votes (all scrutins, ~350 MB)
- Legislative dossiers (~150 MB)
- Amendments (first 1000, ~230 MB)

**Recommended**: Run `warm` after installation for best performance!

## Python API

### OptimizedDataLoader (Recommended)

```python
from src.utils.data_loader import OptimizedDataLoader

# Uses Parquet cache automatically
loader = OptimizedDataLoader(legislature=17)

# Get data as Polars DataFrames
df_deputies = loader.get_deputies_df()      # Fast Parquet load
df_amendments = loader.get_amendments_df()  # Fast Parquet load
df_bills = loader.get_bills_df()            # Fast Parquet load
df_votes = loader.get_votes_df()            # Fast Parquet load
```

### AssembleeNationaleAPI (Legacy JSON)

```python
from src.api import AssembleeNationaleAPI

# With JSON caching (default)
api = AssembleeNationaleAPI(legislature=17, use_cache=True)

# Without caching (always download fresh)
api = AssembleeNationaleAPI(legislature=17, use_cache=False)
```

### Cache Management Methods

```python
# Get cache information
info = api.get_cache_info()
print(f"Cache size: {info['size_mb']} MB")
print(f"Files: {info['files']}")

# Clear cache
api.clear_cache()
```

## Cache Size Estimates

For legislature 17:

| Data Source          | Uncompressed Size | Records                      |
| -------------------- | ----------------- | ---------------------------- |
| Deputies             | ~12 MB            | 575 deputies + 7,131 organes |
| Votes                | ~350 MB           | 5,000+ scrutins              |
| Legislative Dossiers | ~150 MB           | 1,000+ dossiers              |
| Amendments           | ~230 MB (1000)    | Depends on limit             |

**Total**: ~740 MB for full cache

**Recommendations**:
- Default amendment limit (1000): ~740 MB total
- Increased amendment limit (10000): ~2+ GB total
- Disk space required: Plan for 1-3 GB

## When Cache is Used

### Streamlit Pages

All pages use Streamlit's `@st.cache_data` decorator which:
1. Caches results in memory for the session
2. Uses the file cache underneath (via API client)

**Result**: After warming cache, pages load almost instantly!

### First Visit Performance

| Scenario                 | Load Time    |
| ------------------------ | ------------ |
| Cold start (no cache)    | 5-10 seconds |
| Warmed cache             | <1 second    |
| Cached + Streamlit cache | <0.1 seconds |

## Cache Invalidation

### Automatic

- Cache expires after **24 hours**
- Next request downloads fresh data

### Manual

```bash
# Clear all cache
python cache_manager.py clear

# Or programmatically
api.clear_cache()
```

### When to Clear Cache

- **Data seems outdated**: Clear to force refresh
- **Disk space needed**: Free up 740+ MB
- **After legislature change**: New legislature needs new data
- **Testing**: Ensure fresh data is loaded

## Best Practices

### For Development

```bash
# Clear cache frequently
python cache_manager.py clear

# Or disable caching
api = AssembleeNationaleAPI(use_cache=False)
```

### For Production

```bash
# Warm cache on deployment
python cache_manager.py warm --legislature 17

# Let cache auto-refresh daily
# No manual intervention needed
```

### For Users

**After installation**, run:
```bash
source venv/bin/activate
python cache_manager.py warm --legislature 17
```

This downloads all data once. Subsequent app launches will be instant!

## Troubleshooting

### Cache Not Working

Check cache directory exists:
```bash
ls -lh .cache/assemblee_data/
```

Should show JSON files.

### Slow After Cache

If still slow after caching:
1. Check cache info: `python cache_manager.py info`
2. Verify cache age (should be recent)
3. Try clearing and warming:
   ```bash
   python cache_manager.py clear
   python cache_manager.py warm
   ```

### Out of Disk Space

Cache uses ~740 MB. If space is tight:
```bash
# Clear cache
python cache_manager.py clear

# Or reduce amendment limit in pages
# Edit pages/4_Activité.py line 22:
value=500  # Instead of 2000
```

### Cache Files Corrupted

```bash
# Clear and rebuild
python cache_manager.py clear
python cache_manager.py warm
```

## Implementation Details

### Caching Strategy

**File-based caching** with:
- MD5 hash of URL as filename
- JSON format for fast parsing
- TTL-based expiration

**Why file-based?**
- Survives app restarts
- Shared across Streamlit sessions
- Simple to manage and debug
- No external dependencies (Redis, etc.)

### Cache Key Generation

```python
import hashlib

url = "https://data.assemblee-nationale.fr/.../Deputies.json.zip"
cache_key = hashlib.md5(url.encode()).hexdigest()
cache_file = f".cache/assemblee_data/{cache_key}.json"
```

Each unique URL gets its own cache file.

### Thread Safety

- **Read-heavy**: Multiple Streamlit sessions can read simultaneously
- **Write-once**: Each URL cached once per 24 hours
- **No locks needed**: File system handles concurrent reads

## Monitoring

### Cache Health

```python
info = api.get_cache_info()

# Check cache is healthy
assert info['files'] >= 4  # At least 4 datasets
assert info['size_mb'] > 100  # Reasonable size
assert info['newest'] is not None  # Has data
```

### Cache Miss Rate

Check logs for:
- `"Loading from cache"` = cache hit ✓
- `"Downloading from"` = cache miss ✗

High miss rate suggests:
- Cache expired (>24 hours old)
- Cache was cleared
- New data sources added

## Future Enhancements

Potential improvements:
1. **Compression**: Gzip cache files (save 70% space)
2. **Smart refresh**: Background updates while serving cached data
3. **Partial cache**: Cache individual deputies/votes
4. **CDN support**: Optional external cache layer
5. **Cache statistics**: Track hit/miss rates

## FAQ

**Q: Will cache use too much disk space?**
A: ~740 MB is reasonable for a data application. Clear periodically if needed.

**Q: Can I share cache between users?**
A: Yes! Cache is in `.cache/` directory. Can be shared on network drive.

**Q: What if Assemblée Nationale updates data?**
A: Cache auto-refreshes after 24 hours. Or manually clear cache.

**Q: Can I backup the cache?**
A: Yes! Just copy `.cache/` directory. Restore by copying back.

**Q: Does cache affect data accuracy?**
A: No. Cache refreshes daily. For real-time data, clear cache or disable.

---

**Added**: January 19, 2026
**Status**: ✅ Fully Operational
**Performance**: 20x faster loading times
