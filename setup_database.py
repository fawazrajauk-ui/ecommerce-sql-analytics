from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile
import duckdb
import pandas as pd

DATA = Path("data")
DATA.mkdir(exist_ok=True)

zip_path = DATA / "online_retail.zip"
excel_path = DATA / "Online Retail.xlsx"

if not excel_path.exists():
    print("Downloading UCI Online Retail dataset...")
    if not zip_path.exists():
        urlretrieve(
            "https://archive.ics.uci.edu/static/public/352/online+retail.zip",
            zip_path
        )
    with ZipFile(zip_path) as archive:
        archive.extract("Online Retail.xlsx", DATA)

print("Reading transactions...")
df = pd.read_excel(excel_path)

con = duckdb.connect("ecommerce.duckdb")
con.register("retail_df", df)

con.execute("""
CREATE OR REPLACE TABLE transactions AS
SELECT * FROM retail_df
""")

con.execute("""
CREATE OR REPLACE TABLE clean_sales AS
SELECT
    CAST(InvoiceNo AS VARCHAR) AS invoice_no,
    CAST(StockCode AS VARCHAR) AS stock_code,
    Description AS description,
    Quantity AS quantity,
    InvoiceDate AS invoice_date,
    UnitPrice AS unit_price,
    TRY_CAST(CustomerID AS BIGINT) AS customer_id,
    Country AS country,
    ROUND(Quantity * UnitPrice, 2) AS revenue
FROM transactions
WHERE Quantity > 0
  AND UnitPrice > 0
  AND InvoiceNo IS NOT NULL
  AND UPPER(CAST(InvoiceNo AS VARCHAR)) NOT LIKE 'C%'
""")

con.execute("""
CREATE OR REPLACE VIEW customer_sales AS
SELECT *
FROM clean_sales
WHERE customer_id IS NOT NULL
""")

con.execute("""
CREATE OR REPLACE VIEW merchandise_sales AS
SELECT *
FROM clean_sales
WHERE stock_code NOT IN (
    'DOT', 'POST', 'M', 'D', 'C2',
    'BANK CHARGES', 'AMAZONFEE',
    'CRUK', 'PADS', 'S', 'B'
)
AND description IS NOT NULL
""")

con.execute("""
CREATE OR REPLACE TABLE customer_rfm AS
SELECT
    customer_id,
    DATE_DIFF(
        'day',
        MAX(CAST(invoice_date AS DATE)),
        DATE '2011-12-10'
    ) AS recency_days,
    COUNT(DISTINCT invoice_no) AS frequency,
    ROUND(SUM(revenue), 2) AS monetary_gbp
FROM customer_sales
GROUP BY customer_id
""")

con.execute("""
CREATE OR REPLACE TABLE customer_rfm_scored AS
WITH scores AS (
    SELECT
        *,
        NTILE(5) OVER (
            ORDER BY recency_days DESC, customer_id
        ) AS r_score,
        NTILE(5) OVER (
            ORDER BY frequency ASC, customer_id
        ) AS f_score,
        NTILE(5) OVER (
            ORDER BY monetary_gbp ASC, customer_id
        ) AS m_score
    FROM customer_rfm
)
SELECT
    *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4
            THEN 'Champions'
        WHEN f_score >= 4
            THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2
            THEN 'Recent Low-Frequency'
        WHEN r_score <= 2 AND f_score >= 3
            THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2
            THEN 'Hibernating'
        ELSE 'Potential Loyalists'
    END AS segment
FROM scores
""")

con.execute("""
CREATE OR REPLACE TABLE cohort_retention AS
WITH customer_months AS (
    SELECT DISTINCT
        customer_id,
        DATE_TRUNC('month', invoice_date) AS purchase_month
    FROM customer_sales
),
first_purchase AS (
    SELECT
        customer_id,
        MIN(purchase_month) AS cohort_month
    FROM customer_months
    GROUP BY customer_id
),
cohort_activity AS (
    SELECT
        f.cohort_month,
        DATE_DIFF(
            'month',
            f.cohort_month,
            c.purchase_month
        ) AS months_since_first,
        COUNT(DISTINCT c.customer_id) AS active_customers
    FROM customer_months c
    JOIN first_purchase f
        ON c.customer_id = f.customer_id
    GROUP BY 1, 2
),
cohort_sizes AS (
    SELECT
        cohort_month,
        active_customers AS cohort_size
    FROM cohort_activity
    WHERE months_since_first = 0
)
SELECT
    a.cohort_month,
    a.months_since_first,
    s.cohort_size,
    a.active_customers,
    ROUND(
        100.0 * a.active_customers / s.cohort_size,
        2
    ) AS retention_pct
FROM cohort_activity a
JOIN cohort_sizes s
    ON a.cohort_month = s.cohort_month
ORDER BY a.cohort_month, a.months_since_first
""")

for table in [
    "transactions",
    "clean_sales",
    "customer_rfm",
    "customer_rfm_scored",
    "cohort_retention"
]:
    count = con.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]
    print(f"{table}: {count:,} rows")

con.close()
print("Database setup complete!")
