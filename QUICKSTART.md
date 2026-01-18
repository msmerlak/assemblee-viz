# Quick Start Guide

## Get Started in 3 Steps

### 1️⃣ Activate Virtual Environment
```bash
source venv/bin/activate
```

### 2️⃣ Run the Application
```bash
streamlit run app.py
```

### 3️⃣ Explore the Data
The application will open automatically at http://localhost:8501

## What You'll See

### 🏠 Home Page
- Overview of 575 deputies
- 12 political groups
- Recent voting activity

### 👥 Députés Page
Navigate to see:
- All 575 active deputies
- Political group distribution
- Gender parity statistics
- Geographic distribution

### 📜 Législation Page
Explore:
- Legislative dossiers
- Bill types and status
- Timeline of activity

### 🗳️ Scrutins Page
Analyze:
- Voting results
- Participation rates
- Vote breakdowns

## Tips

- **Search**: Use the search boxes to find specific deputies or bills
- **Filter**: Dropdown menus let you filter by group, type, or status
- **Export**: Download CSV files of filtered data
- **Legislature**: Change legislature in the sidebar (17, 16, or 15)

## First Load

⏱️ The first load will take 5-10 seconds as it downloads data from the Assemblée Nationale.
Subsequent loads are much faster thanks to caching!

## Need Help?

- See `SETUP_COMPLETE.md` for detailed documentation
- See `README.md` for full project information
- Run `python test_data_loading.py` to verify data sources

---

**Ready to explore French legislative data!** 🇫🇷
