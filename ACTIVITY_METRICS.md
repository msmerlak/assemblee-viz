# Deputy Activity Metrics - Feature Documentation

## Overview

A new page has been added to analyze deputy performance through their amendment activity, providing success metrics and comparative statistics.

## 📊 New Page: Activité des Députés

**URL**: Available in navigation menu or directly at `pages/4_Activité.py`

### What It Shows

#### Key Metrics per Deputy:
- **Total Amendments**: Number of amendments deposited
- **Adopted**: Amendments that were adopted
- **Rejected**: Amendments that were rejected
- **Withdrawn**: Amendments withdrawn by the deputy
- **Inadmissible**: Amendments ruled inadmissible
- **Success Rate**: Percentage of adopted amendments among those examined (adopted + rejected)

### Four Analysis Tabs

#### 1. 🏆 Classement (Rankings)
- **Top 20 most active deputies** by number of amendments
- Visual bar chart colored by success rate
- Interactive table with sortable columns
- Shows deputy name, political group, total amendments, adopted/rejected counts, and success rate

#### 2. 📈 Taux de succès (Success Rates)
- **Top 20 deputies by success rate** (minimum 5 examined amendments)
- Distribution histogram of success rates across all deputies
- Statistics: mean, median, and count of deputies with >50% success rate
- Helps identify which deputies are most effective at getting amendments adopted

#### 3. 📊 Par groupe (By Political Group)
- **Aggregate statistics per political group**
- Total amendments by group
- Success rate by group
- Shows which political groups are most active and successful
- Comparative analysis across the political spectrum

#### 4. 🔍 Détails (Detailed Search)
- **Full searchable table** of all deputies with amendment activity
- Filter by deputy name or political group
- Sort by: number of amendments, success rate, or name
- Complete statistics for each deputy
- CSV export functionality

## Data Source

**Amendments Dataset**: `/17/loi/amendements_div_legis/Amendements.json.zip`

**Source**: [Tous les amendements - Assemblée nationale](https://data.assemblee-nationale.fr/travaux-parlementaire/amendements/tous-les-amendements)

The dataset includes:
- All amendments filed in committee and public session
- Author and co-signatories information
- Amendment content, purpose, and reasoning
- Outcome (adopted, rejected, withdrawn, inadmissible)
- Legislative text references

## How It Works

### Amendment States

Amendments go through various states in their lifecycle:

**Processing States** (`etatDesTraitements`):
- **Discuté** (DI): Discussed/Examined
- **Retiré**: Withdrawn by author
- **Irrecevable**: Inadmissible (various reasons)
- **Irrecevable 40**: Inadmissible under Article 40 (financial impact)

**Final Outcomes** (`sort`):
- **Adopté**: Adopted (success)
- **Rejeté**: Rejected (failure)
- **Non soutenu**: Not sustained
- (Empty): Still pending or not yet voted

### Success Rate Calculation

```
Success Rate = (Adopted / (Adopted + Rejected)) × 100
```

**Note**: Only amendments that were actually examined (adopted or rejected) are counted. Withdrawn and inadmissible amendments are excluded from the success rate calculation as they never reached a vote.

### Filtering Criteria

For success rate rankings, only deputies with **at least 5 examined amendments** are included to ensure statistical relevance.

## Performance Considerations

### Data Loading
- **Default**: 2,000 amendments loaded
- **Adjustable**: 500 to 10,000 via sidebar slider
- **Load Time**: ~3-8 seconds depending on limit
- **Caching**: 1-hour TTL for better performance

### Why Limit Amendments?

The full amendments dataset contains tens of thousands of amendments. Loading all would:
- Take 30+ seconds
- Use significant memory
- Slow down calculations

The default 2,000 amendment sample provides:
- Representative statistics for all active deputies
- Fast loading and responsive interface
- Sufficient data for meaningful analysis

To get complete statistics, increase the slider to 10,000.

## Insights You Can Gain

### Individual Performance
- Which deputies are most prolific in proposing amendments?
- Which deputies have the highest success rates?
- How does activity vary across political groups?

### Group Dynamics
- Which political groups file the most amendments?
- Which groups have the highest adoption rates?
- Are opposition groups less successful than majority?

### Legislative Strategy
- Do deputies with more amendments have lower success rates?
- Is there a "sweet spot" for amendment activity?
- How do government vs. opposition deputies compare?

## Example Use Cases

### 1. Evaluate Deputy Effectiveness
```
1. Go to "Activité" page
2. Select "Classement" tab
3. Search for a specific deputy
4. Compare their metrics to peers in their group
```

### 2. Compare Political Groups
```
1. Go to "Par groupe" tab
2. Review total amendments by group
3. Check success rates across the spectrum
4. Identify most/least successful groups
```

### 3. Find Most Successful Deputies
```
1. Go to "Taux de succès" tab
2. Review Top 20 with highest adoption rates
3. Note their political affiliations
4. Download data for further analysis
```

### 4. Export Data for Research
```
1. Go to "Détails" tab
2. Apply desired filters
3. Click "Télécharger les données (CSV)"
4. Analyze in Excel/Python/R
```

## Technical Implementation

### API Method Added

```python
def get_amendments(self, legislature: int, limit: int) -> List[Dict]:
    """
    Downloads and parses amendments from the Assemblée Nationale
    Returns list of amendment dictionaries with:
    - uid, numero, dateDepot
    - auteur (deputy UID)
    - nombreCosignataires
    - etat, etatCode, sort, sortCode
    - texteLegislatifRef
    """
```

### Data Processing

The page calculates per-deputy statistics by:
1. Loading all deputies and amendments
2. Grouping amendments by author (deputy UID)
3. Counting outcomes: adopted, rejected, withdrawn, inadmissible
4. Computing success rate: adopted / (adopted + rejected)
5. Creating aggregate views by political group

### Visualizations

- **Plotly** for interactive charts
- **Color coding** by success rate (red-yellow-green gradient)
- **Pandas styling** for formatted tables with conditional coloring
- **Streamlit components** for filters, search, and exports

## Future Enhancements

Potential additions:
1. **Time series**: Track success rates over time
2. **Co-signature analysis**: Network of amendment co-signatories
3. **Topic analysis**: Most common amendment subjects
4. **Debate participation**: Speaking time and intervention counts
5. **Committee activity**: Amendments by committee
6. **Comparison tool**: Side-by-side deputy comparisons

## Data Accuracy Notes

- **Sample vs. Complete**: Default 2,000 amendments is a sample. Increase for full dataset.
- **Update Frequency**: Data is updated daily by Assemblée Nationale
- **Pending Amendments**: Some amendments may not have final outcomes yet
- **Historical Data**: Earlier legislatures may have incomplete amendment data

## References

- **Data Portal**: https://data.assemblee-nationale.fr/
- **Amendments Page**: https://data.assemblee-nationale.fr/travaux-parlementaires/amendements/tous-les-amendements
- **API Documentation**: Available on the data portal
- **Amendment Search**: https://www.assemblee-nationale.fr/dyn/17/amendements

---

**Added**: January 18, 2026
**Status**: ✅ Fully Operational
**Data Source**: Assemblée Nationale Open Data Portal
