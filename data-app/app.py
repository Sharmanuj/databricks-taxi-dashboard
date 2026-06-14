import os
import time
from functools import lru_cache
from typing import Any, Dict, List

import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

from flask import jsonify, request, abort
import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import dash_bootstrap_components as dbc
import dash_ag_grid as dag

# ----------------------------
# Environment & configuration
# ----------------------------
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
assert WAREHOUSE_ID, "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

# Optional API key for external callers (set APP_API_KEY in app.yaml or as a secret)
APP_API_KEY = os.getenv("APP_API_KEY", "")

# Databricks SDK config reads host/credentials from env inside Apps
# (works with PAT or the app’s OIDC credentials)


def sqlQuery(query: str) -> pd.DataFrame:
    """Execute a SQL query and return the result as a pandas DataFrame."""
    cfg = Config() 
    # Pull environment variables for auth
    try:
        with sql.connect(
            server_hostname=cfg.host,
            # http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            credentials_provider=lambda: cfg.authenticate
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall_arrow().to_pandas()
    except Exception as e:
        print(f"An error occurred in querying data: {str(e)}")
        return pd.DataFrame()
    
data = sqlQuery("SELECT * FROM samples.nyctaxi.trips LIMIT 5000") 
print(f"Data shape: {data.shape}") 
print(f"Data columns: {data.columns}") 


def predict_fare(pickup_zip: str, dropoff_zip: str) -> float:
    """
    Very simple baseline: mean fare for the (pickup, dropoff) pair in the sample.
    Falls back to a default if no rows.
    """
    try:
        pz = int(pickup_zip)
        dz = int(dropoff_zip)
    except Exception:
        return 99.0

    d = data[(data["pickup_zip"] == pz) & (data["dropoff_zip"] == dz)]
    return float(d["fare_amount"].mean()) if len(d) > 0 else 99.0

# ----------------------------
# Dash app (UI still available)
# ----------------------------
dash_app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = dash_app.server  # Flask app underneath (used for API routes)

dash_app.layout = dbc.Container([
    dbc.Row([dbc.Col(html.H1("Taxi Fare Distribution"), width=12)]),
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='fare-scatter',
                figure=px.scatter(
                    data,
                    x='trip_distance',
                    y='fare_amount',
                    labels={'fare_amount': 'Fare', 'trip_distance': 'Distance'}
                ),
                style={'height': '400px', 'width': '100%'}
            )
        ], width=8),
        dbc.Col([
            html.H3("Predict Fare"),
            dbc.Label("From (zipcode)"),
            dbc.Input(id='from-zipcode', type='text', value='10003'),
            dbc.Label("To (zipcode)"),
            dbc.Input(id='to-zipcode', type='text', value='11238'),
            dbc.Button("Predict", id='submit-button', n_clicks=0, color='primary', className='mt-3'),
            html.Div(
                id='prediction-output',
                className='mt-3',
                style={'font-size': '24px', 'font-weight': 'bold'}
            )
        ], width=4)
    ]),
    dbc.Row([
        dbc.Col([
            dag.AgGrid(
                id='data-grid',
                columnDefs=[{"headerName": col, "field": col} for col in data.columns],
                rowData=data.to_dict('records'),
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                style={'height': '400px', 'width': '100%'}
            )
        ], width=12)
    ])
], fluid=True)

@dash_app.callback(
    Output('prediction-output', 'children'),
    Input('submit-button', 'n_clicks'),
    State('from-zipcode', 'value'),
    State('to-zipcode', 'value')
)
def render_prediction(n_clicks, pickup, dropoff):
    val = predict_fare(pickup, dropoff)
    return f"Predicted Fare: ${val:.2f}"

# --------------------------------------------------
# API helpers (auth + JSON response + error shaping)
# --------------------------------------------------
def api_auth_ok() -> bool:
    """
    If APP_API_KEY is set, require X-API-Key header to match.
    If APP_API_KEY is empty, auth is disabled (open).
    """
    if not APP_API_KEY:
        return True
    return request.headers.get("X-API-Key") == APP_API_KEY

def require_api_key():
    if not api_auth_ok():
        abort(401, description="Unauthorized: invalid or missing X-API-Key")

def json_ok(payload: Dict[str, Any], status=200):
    return jsonify({"ok": True, "data": payload, "ts": int(time.time())}), status

def json_err(message: str, status=400):
    return jsonify({"ok": False, "error": message, "ts": int(time.time())}), status

# -------------
# API endpoints
# -------------
@server.route("/api/health", methods=["GET"])
def api_health():
    # No auth for a basic liveness probe
    return json_ok({"status": "up", "warehouse_id": WAREHOUSE_ID})

@server.route("/api/trips", methods=["GET"])
def api_trips():
    require_api_key()
    # Small, safe page over the cached DataFrame
    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
        limit = max(1, min(limit, 1000))  # cap to avoid giant payloads
        offset = max(0, offset)

        df = data.iloc[offset:offset + limit]
        return json_ok({
            "count": len(df),
            "offset": offset,
            "limit": limit,
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
        })
    except Exception as e:
        return json_err(str(e), status=500)

@server.route("/api/stats", methods=["GET"])
def api_stats():
    require_api_key()
    try:
        # Quick descriptive stats useful to consumers
        stats = {
            "rows": int(len(data)),
            "columns": list(data.columns),
            "fare": {
                "min": float(pd.to_numeric(data["fare_amount"], errors="coerce").min(skipna=True)),
                "max": float(pd.to_numeric(data["fare_amount"], errors="coerce").max(skipna=True)),
                "mean": float(pd.to_numeric(data["fare_amount"], errors="coerce").mean(skipna=True)),
            },
            "distance": {
                "mean": float(pd.to_numeric(data["trip_distance"], errors="coerce").mean(skipna=True)),
            },
        }
        return json_ok(stats)
    except Exception as e:
        return json_err(str(e), status=500)

@server.route("/api/predict", methods=["GET", "POST"])
def api_predict():
    require_api_key()
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            pickup = str(payload.get("pickup_zip", ""))
            dropoff = str(payload.get("dropoff_zip", ""))
        else:
            pickup = request.args.get("pickup_zip", "")
            dropoff = request.args.get("dropoff_zip", "")
        if not pickup or not dropoff:
            return json_err("pickup_zip and dropoff_zip are required.", status=422)

        pred = predict_fare(pickup, dropoff)
        return json_ok({
            "pickup_zip": pickup,
            "dropoff_zip": dropoff,
            "predicted_fare": round(pred, 2),
            "currency": "USD"
        })
    except Exception as e:
        return json_err(str(e), status=500)

# Optional: very small OpenAPI doc to help integrators
@server.route("/openapi.json", methods=["GET"])
def openapi():
    return jsonify({
        "openapi": "3.0.0",
        "info": {"title": "Taxi API (Databricks App)", "version": "1.0.0"},
        "paths": {
            "/api/health": {"get": {"summary": "Healthcheck", "responses": {"200": {"description": "OK"}}}},
            "/api/trips": {
                "get": {
                    "summary": "Page through sample trips",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/stats": {"get": {"summary": "Dataset stats", "responses": {"200": {"description": "OK"}}}},
            "/api/predict": {
                "get": {
                    "summary": "Predict fare (query params)",
                    "parameters": [
                        {"name": "pickup_zip", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "dropoff_zip", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}}
                },
                "post": {
                    "summary": "Predict fare (JSON body)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "properties": {
                                "pickup_zip": {"type": "string"},
                                "dropoff_zip": {"type": "string"}
                            },
                            "required": ["pickup_zip", "dropoff_zip"]
                        }}}}
                }
            }
        }
    })

# ----------------
# App entrypoint
# ----------------
if __name__ == "__main__":
    # Prime the UI with an initial prediction text
    initial_prediction = f"Predicted Fare: ${predict_fare('10003', '11238'):.2f}"
    # This matches your original pattern to seed the component
    dash_app.layout.children[1].children[1].children[-1].children = initial_prediction

    # Bind to the port Databricks Apps provides
    port = int(os.getenv("PORT", "8000"))
    dash_app.run(host="0.0.0.0", port=port, debug=False)
