# Taxi Fare Prediction Dashboard

A Dash-based web application running on Databricks that visualizes NYC Taxi trip data and provides fare prediction based on pickup and dropoff ZIP codes.

## Features

* Interactive scatter plot of taxi fares vs trip distance
* Fare prediction based on pickup and dropoff ZIP codes
* Data grid with trip records
* REST APIs for data access and fare prediction
* Databricks SQL Warehouse integration
* OpenAPI documentation endpoint

---

## Technology Stack

* Python 3.x
* Dash
* Plotly
* Flask
* Pandas
* Databricks SQL Connector
* Databricks SDK
* Dash Bootstrap Components
* Dash AG Grid

---

## Project Structure

```text
data-app/
│
├── app.py
├── requirements.txt
├── app.yaml
└── README.md
```

---

## Prerequisites

* Python 3.10+
* Databricks Workspace
* Running SQL Warehouse
* Databricks Personal Access Token (PAT)

---

## Configuration

### Databricks SQL Warehouse

Warehouse ID:

```text
Warehouse ID
```

### Environment Variables

```bash
export DATABRICKS_HOST="https://<workspace>.cloud.databricks.com"
export DATABRICKS_TOKEN="<personal-access-token>"
export DATABRICKS_WAREHOUSE_ID="YOUR_DATABRICKS_WAREHOUSE_ID"
```

---

## Local Development

Create virtual environment:

```bash
python -m venv env
source env/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run application:

```bash
python app.py
```

Application URL:

```text
http://localhost:8000
```

---

## Databricks SQL Query

The application loads sample NYC Taxi data:

```sql
SELECT *
FROM samples.nyctaxi.trips
LIMIT 5000
```

---

## API Endpoints

### Health Check

```http
GET /api/health
```

Response:

```json
{
  "ok": true,
  "data": {
    "status": "up"
  }
}
```

---

### Dataset Statistics

```http
GET /api/stats
```

---

### Trip Records

```http
GET /api/trips?limit=100&offset=0
```

---

### Fare Prediction

```http
GET /api/predict?pickup_zip=10003&dropoff_zip=11238
```

Response:

```json
{
  "ok": true,
  "data": {
    "pickup_zip": "10003",
    "dropoff_zip": "11238",
    "predicted_fare": 18.25,
    "currency": "USD"
  }
}
```

---

## OpenAPI Documentation

```http
GET /openapi.json
```

---

## Dashboard Features

### Visualization

* Trip Distance vs Fare Amount Scatter Plot
* Interactive Plotly Charts

### Prediction

Users can:

1. Enter pickup ZIP code
2. Enter dropoff ZIP code
3. Click Predict
4. View estimated fare

### Data Grid

* Sortable columns
* Filterable records
* Resizable columns

---

## Deployment

### Databricks Apps

Example app.yaml:

```yaml
command:
  - python
  - app.py

env:
  - name: DATABRICKS_HOST
    value: "<workspace-url>"

  - name: DATABRICKS_WAREHOUSE_ID
    value: "DATABRICKS_WAREHOUSE_ID"

expose:
  - path: /
    port: 8000
    protocol: http
```

---

## Security Notes

* Do not commit Personal Access Tokens.
* Use Databricks Secrets for production deployments.
* Restrict SQL Warehouse permissions appropriately.

---

## Future Enhancements

* ML-based fare prediction model
* Authentication and authorization
* Advanced filtering and analytics
* Real-time trip monitoring
* Export data to CSV/Excel

---

## Author

Anuj Sharma

Backend Developer | Python | Django | Databricks | Cloud Engineering
# databricks-taxi-dashboard
Databricks-powered Dash application for NYC Taxi fare analysis, visualisation, and fare prediction using SQL Warehouse integration.
