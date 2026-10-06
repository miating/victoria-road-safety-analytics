# Victoria Road Safety Analytics

An end-to-end analytics project built on official Victorian road crash open data.
Raw CSV files are cleaned and validated with Python, loaded into PostgreSQL,
modelled for analysis with SQL, and presented in a Power BI dashboard.

> Work in progress - currently at **Phase 0 (project setup)**.

## Architecture

```
Victorian open data (CSV)
        |
   Python ETL  (extract -> transform -> validate -> load)
        |
   PostgreSQL  (staging -> cleaned tables -> analytics model)
        |
   SQL views
        |
   Power BI dashboard
```

## Tech Stack

- PostgreSQL
- Python (pandas, SQLAlchemy, psycopg)
- Power BI
- Git / GitHub

## Getting Started

Requirements: Python 3.11+, PostgreSQL 16+, Git.

```bash
git clone <repo-url>
cd victoria-road-safety-analytics

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

cp .env.example .env            # then edit .env with your database credentials
createdb -U postgres vic_road_safety
```

## Repository Structure

```
data/        raw and processed data (not committed)
src/         Python ETL code: extract, transform, validation, load, utils
sql/         schema, staging, analytics, views, indexes, performance tests
notebooks/   exploratory analysis
tests/       pytest tests
docs/        architecture, data dictionary, database and dashboard design
powerbi/     Power BI dashboard
```
