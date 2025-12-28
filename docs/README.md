# VI_LAB_2
Information Visualization Lab 2

## Project Overview

This project creates an exploratory visualization tool using **Altair** and **Streamlit** to analyze NSF (National Science Foundation) grants data. The analysis focuses on:
- NSF grants awarded in the last 5 years (2020-2024)
- Trump-era terminated grants (2017-2021)

## Repository Structure

### Main Files
- **`VI_Lab2.ipynb`** - Main Jupyter notebook containing all visualizations and analysis (Q1-Q6)
- **`NSF_Grants_Last5Years_Clean.csv`** - Cleaned dataset of NSF grants (2020-2024)
- **`trump17-21-csv.csv`** - Cleaned dataset of Trump-era terminated grants (2017-2021)
- **`estimated_population.csv`** - Population data for per-capita calculations
- **`state_abbreviations.csv`** - State abbreviation mappings

### Data Processing Scripts
- **`update_csv_with_missing_states.py`** - Adds missing US states to the dataset with zero values
- **`add_missing_states.py`** - Alternative script for adding missing states

### Raw Data
- **`raw data/`** - Contains original data files:
  - `Awards20-21.csv`, `Awards22-23.csv`, `Awards24-24.csv` - NSF grants by time period
  - `trump17-21.csv` - Original Trump-era terminated grants data

### Documentation
- **`docs/PROJECT_PLAN.md`** - Detailed project plan and requirements
- **`docs/CHECKLIST.md`** - Project completion checklist
- **`docs/Project2.pdf`** - Project specification document

## Key Features

The project includes 6 main visualization questions:
- **Q1**: Grants by state per year
- **Q2**: Grants by directorate per year
- **Q3**: Cancelled grants analysis by directorate
- **Q4**: Total grants evolution over years
- **Q5**: State-specific grants evolution + cancelled grants
- **Q6**: Funding per capita by state

## Technologies Used

- **Altair** - For creating interactive visualizations
- **Streamlit** - For the interactive web application
- **Pandas** - For data manipulation
- **VegaFusion** - For performance optimization with large datasets (>5000 rows)

## Getting Started

1. Install required dependencies:
   ```bash
   pip install pandas altair streamlit vegafusion
   ```

2. Run the Jupyter notebook:
   ```bash
   jupyter notebook VI_Lab2.ipynb
   ```

3. Run the Streamlit app (when available):
   ```bash
   streamlit run streamlit_app.py
   ```

## Data Sources

All data was obtained from the **NSF Award Search portal**, the official source for National Science Foundation grant information.
