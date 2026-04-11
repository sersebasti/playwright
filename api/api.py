import os
import re
import json
import pymysql
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "solar")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_ROOT_PASSWORD", "")

CHART_FIELDS = [
    "Battery Voltage",
    "Battery Capacity",
    "Inverter Charging Current",
    "Load Percentage",
    "PV Voltage",
    "Controller Charging Current",
]


def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def safe_json_loads(raw_json):
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except Exception:
        return {}


def extract_numeric_value(raw_value):
    if raw_value is None:
        return None

    text = str(raw_value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None

    try:
        return float(match.group(0))
    except Exception:
        return None


@app.get("/")
def index():
    options_html = "\n".join(
        f'<option value="{field}">{field}</option>' for field in CHART_FIELDS
    )

    html = f"""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Solar API Charts</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 20px;
      background: #f7f7f7;
      color: #222;
    }}
    h1 {{
      margin-bottom: 10px;
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 20px;
    }}
    select, button, input {{
      padding: 8px 10px;
      font-size: 14px;
    }}
    .card {{
      background: white;
      border-radius: 10px;
      padding: 16px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      margin-bottom: 20px;
    }}
    #status {{
      margin-top: 10px;
      font-size: 14px;
      color: #444;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      background: white;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 8px;
      font-size: 13px;
      text-align: left;
    }}
    th {{
      background: #f0f0f0;
    }}
  </style>
</head>
<body>
  <h1>Solar data charts</h1>

  <div class="card">
    <div class="toolbar">
      <label for="fieldSelect">Valore:</label>
      <select id="fieldSelect">
        {options_html}
      </select>

      <label for="limitInput">Punti:</label>
      <input id="limitInput" type="number" min="1" max="1000" value="100">

      <button onclick="loadChart()">Aggiorna</button>
    </div>

    <canvas id="chart" height="110"></canvas>
    <div id="status"></div>
  </div>

  <div class="card">
    <h3>Ultimi valori</h3>
    <table>
      <thead>
        <tr>
          <th>created_at</th>
          <th>update_time</th>
          <th>value_raw</th>
          <th>value_num</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>

  <script>
    let chart = null;

    async function loadChart() {{
      const field = document.getElementById("fieldSelect").value;
      const limit = document.getElementById("limitInput").value || 100;
      const status = document.getElementById("status");
      const tableBody = document.getElementById("tableBody");

      status.textContent = "Caricamento...";
      tableBody.innerHTML = "";

      try {{
        const response = await fetch(`/api/history?field=${{encodeURIComponent(field)}}&limit=${{encodeURIComponent(limit)}}`);
        const data = await response.json();

        if (!data.ok) {{
          status.textContent = "Errore: " + (data.error || "errore sconosciuto");
          return;
        }}

        const labels = data.items.map(item => item.created_at);
        const values = data.items.map(item => item.value_num);

        if (chart) {{
          chart.destroy();
        }}

        const ctx = document.getElementById("chart").getContext("2d");
        chart = new Chart(ctx, {{
          type: "line",
          data: {{
            labels,
            datasets: [{{
              label: field,
              data: values,
              tension: 0.2
            }}]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: true,
            scales: {{
              y: {{
                beginAtZero: false
              }}
            }}
          }}
        }});

        const recentItems = [...data.items].reverse().slice(0, 20);
        for (const item of recentItems) {{
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${{item.created_at ?? ""}}</td>
            <td>${{item.update_time ?? ""}}</td>
            <td>${{item.value_raw ?? ""}}</td>
            <td>${{item.value_num ?? ""}}</td>
          `;
          tableBody.appendChild(tr);
        }}

        status.textContent = `Campo: ${{data.field}} | punti: ${{data.count}}`;
      }} catch (err) {{
        status.textContent = "Errore fetch: " + err;
      }}
    }}

    loadChart();
  </script>
</body>
</html>
    """
    return Response(html, mimetype="text/html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/latest")
def latest():
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, device_row_key, update_time, json_data, created_at
                FROM device_snapshots
                ORDER BY id DESC
                LIMIT 1
            """)
            row = cur.fetchone()

        if not row:
            return jsonify({"ok": False, "error": "no data"}), 404

        payload = safe_json_loads(row["json_data"])

        return jsonify({
            "ok": True,
            "id": row["id"],
            "device_row_key": row["device_row_key"],
            "update_time": row["update_time"],
            "created_at": str(row["created_at"]),
            "data": payload,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/device/<device_row_key>/latest")
def latest_for_device(device_row_key):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, device_row_key, update_time, json_data, created_at
                FROM device_snapshots
                WHERE device_row_key = %s
                ORDER BY id DESC
                LIMIT 1
            """, (device_row_key,))
            row = cur.fetchone()

        if not row:
            return jsonify({"ok": False, "error": "no data"}), 404

        payload = safe_json_loads(row["json_data"])

        return jsonify({
            "ok": True,
            "id": row["id"],
            "device_row_key": row["device_row_key"],
            "update_time": row["update_time"],
            "created_at": str(row["created_at"]),
            "data": payload,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/snapshots")
def snapshots():
    limit = int(request.args.get("limit", "10"))

    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, device_row_key, update_time, created_at
                FROM device_snapshots
                ORDER BY id DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()

        for row in rows:
            row["created_at"] = str(row["created_at"])

        return jsonify({"ok": True, "items": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/history")
def history():
    field = request.args.get("field")
    limit = int(request.args.get("limit", "100"))

    if not field:
        return jsonify({"ok": False, "error": "missing field"}), 400

    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, device_row_key, update_time, json_data, created_at
                FROM device_snapshots
                ORDER BY id DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()

        items = []
        for row in reversed(rows):
            payload = safe_json_loads(row["json_data"])
            raw_value = payload.get(field)
            num_value = extract_numeric_value(raw_value)

            items.append({
                "id": row["id"],
                "device_row_key": row["device_row_key"],
                "created_at": str(row["created_at"]),
                "update_time": row["update_time"],
                "value_raw": raw_value,
                "value_num": num_value,
            })

        return jsonify({
            "ok": True,
            "field": field,
            "count": len(items),
            "items": items,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)