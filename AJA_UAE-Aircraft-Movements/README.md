# Analysis of International Aircraft Movements in the UAE, 2018 to 2025

MSc Programming for Data Science project, reworked for my portfolio.

The data is a monthly count of international aircraft arrivals and departures from Bayanat.ae (UAE General Civil Aviation Authority, CC BY-SA 4.0). I first treated it as flights at Dubai International (DXB). The UAE statistics centre reports 694,050 movements across all UAE airports in 2023 and 771,800 in 2024, against 694,130 and 775,248 in this file, so the data covers UAE airports as a whole and DXB is the largest part.

The notebook is in two parts. Part 1 uses the Bayanat dataset to look at UAE-wide aviation trends. Part 2 uses Dubai Airports' own published figures for DXB and DWC specifically, since the UAE-wide dataset can't speak to Dubai's own airport or to the case for its Al Maktoum (DWC) expansion on its own.

## What is in the notebook

**Part 1 — UAE aviation trend (Bayanat dataset)**
- Cleaning and feature creation with pandas
- Yearly and monthly flight trends
- Seasonality, using each month's share of its year in non-COVID years
- COVID-19 impact and recovery (2018 to 2022)
- Correlation between arrivals and departures
- Projection to 2032 using a trend fitted outside the COVID years, with a 95% prediction interval

**Part 2 — DXB/DWC capacity (Dubai Airports' own figures)**
- DXB annual passenger traffic, 2018-2025, compiled from Dubai Airports' press releases (one year gap-filled from a third-party source, marked as such)
- DXB's traffic against its stated ~115 million maximum capacity
- DWC's current traffic and capacity against its planned Phase II (150 million) and ultimate (260 million) capacity
- What this evidence does, and does not, say about whether the DWC expansion is justified

## Changes from the submitted version

- The projection no longer compounds an average growth rate that includes the COVID rebound.
- The submitted version stopped at Q1 2025 and estimated the rest of 2025. The data now covers all of 2025, so the estimate is gone.
- The projection is a trend fitted on the non-COVID years (2018, 2019, 2023, 2024, 2025), and it says where the line probably understates.
- The seasonality section no longer adds up an uneven number of years per month.
- The title and wording now say UAE, with a scope note explaining why.
- The COVID analysis itself is unchanged, apart from a few wording fixes.
- Added Part 2, a short DXB/DWC capacity analysis using Dubai Airports' own figures, to properly back the DWC discussion that the UAE-wide dataset can't support on its own.

The submitted notebook is kept in `original/` for comparison.

## Data note

The current Bayanat file runs to February 2026 and the sheet is called "Data Set". The notebook keeps the eight full years, January 2018 to December 2025 (96 months), and leaves out the two months of 2026 because that year is incomplete.

## Run it in VS Code

You need Python 3, VS Code with the Python and Jupyter extensions (both by Microsoft), and the data file in `data/` (see `data/README.txt`).

1. In VS Code, use File > Open Folder and open the `AJA_UAE-Aircraft-Movements` folder itself (not the folder above it).
2. Open the built-in terminal (Ctrl + `) and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Open `AJA_Prog4DS_Project_v3.ipynb`. Click Select Kernel at the top right, choose Python Environments, then `.venv`.
4. Click Run All.

Next time, just open the folder and the notebook. The kernel choice is remembered.

## Limits

Only flight counts, no passenger or capacity data. The series is short (96 months). The projection rests on five yearly points, so its range is wide, and the fitted line probably understates the next few years.
