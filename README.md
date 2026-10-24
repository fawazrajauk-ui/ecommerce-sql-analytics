# E-Commerce SQL & Customer Analytics

An end-to-end e-commerce analytics project using **SQL, Python, DuckDB, pandas, Plotly and Streamlit**.

This project transforms raw retail transactions into an interactive business intelligence dashboard covering sales performance, product rankings, customer segmentation and cohort retention.

## Dashboard

Run the interactive Streamlit dashboard locally to explore:

- Sales KPIs and monthly revenue trends
- Top products ranked by revenue, units sold or order count
- RFM customer segments and spending concentration
- Monthly customer cohort retention

## Key Findings

| Metric | Result |
|---|---:|
| Original transaction lines | 541,909 |
| Valid positive sales lines | 530,104 |
| Valid orders | 19,960 |
| Gross positive sales | £10.67M |
| Identified purchasing customers | 4,338 |
| Highest full-month sales | £1.51M (November 2011) |

### Business Insights

**Sales growth:** Monthly gross positive sales increased substantially during September–November 2011, reaching approximately £1.51M in November.

**Product performance:** REGENCY CAKESTAND 3 TIER generated approximately £174K across 1,988 orders. PAPER CRAFT, LITTLE BIRDIE generated approximately £168K from a single unusually large order, illustrating the difference between revenue concentration and broad demand.

**Customer segmentation:** Champions represented approximately 25.8% of identified purchasing customers but accounted for 65.8% of their historical positive spending.

**Retention:** Month-1 retention varied across customer cohorts. The December 2010 cohort had 36.61% month-1 retention, compared with 15.04% for March 2011.

## Technology

- **SQL / DuckDB:** Data cleaning, aggregations, CTEs, window functions and cohort analysis
- **Python / pandas:** Data processing and analytical workflows
- **Plotly:** Interactive charts
- **Streamlit:** Interactive business intelligence dashboard

## Getting Started

Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

Build the database:

```bash
python setup_database.py
```

Launch the dashboard:

```bash
streamlit run dashboard.py
```

The setup script downloads the original dataset from the UCI Machine Learning Repository and recreates the analytical tables.

## Methodology

### Data Cleaning

The raw dataset contains cancellations, negative quantities, zero or negative prices and missing customer identifiers.

The cleaned sales dataset retains positive-quantity, positive-price, non-cancellation transaction lines. Missing customer IDs are retained for sales analysis but excluded from customer-level analysis.

Reported sales are **gross positive-line sales**, not net revenue after returns.

### Product Analysis

Merchandise rankings exclude selected administrative stock codes, including postage, manual adjustments and bank charges. This is an approximate classification.

### RFM Segmentation

Customers are scored on:

- Recency: days since their last observed purchase
- Frequency: distinct invoices
- Monetary: cumulative positive spending

Relative quintile scores are used to create six illustrative customer segments. Tied values may cross quintile boundaries.

### Cohort Retention

Customers are grouped by their first observed purchase month. Retention measures the percentage purchasing again in each subsequent calendar month.

The dataset covers December 2010 to 9 December 2011. December 2011 is incomplete, and first observed purchases are not necessarily first-ever purchases.

## Dataset

UCI Machine Learning Repository: [Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail)

The original dataset contains 541,909 transaction lines from a UK-based online retailer.

## Project Structure

```text
ecommerce-sql-analytics/
├── dashboard.py
├── setup_database.py
├── requirements.txt
├── README.md
├── figures/
└── data/                 # Downloaded locally; excluded from Git
```

The DuckDB database is also excluded from Git because it can be recreated using the setup script.
