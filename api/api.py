import os
import json
import pymysql
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "solar")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_ROOT_PASSWORD", "local")


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


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/latest")
def latest():
    conn = get_conn()
    try:
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

        payload = json.loads(row["json_data"])
        return jsonify({
            "ok": True,
            "id": row["id"],
            "device_row_key": row["device_row_key"],
            "update_time": row["update_time"],
            "created_at": str(row["created_at"]),
            "data": payload,
        })
    finally:
        conn.close()


@app.get("/api/device/<device_row_key>/latest")
def latest_for_device(device_row_key):
    conn = get_conn()
    try:
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

        payload = json.loads(row["json_data"])
        return jsonify({
            "ok": True,
            "id": row["id"],
            "device_row_key": row["device_row_key"],
            "update_time": row["update_time"],
            "created_at": str(row["created_at"]),
            "data": payload,
        })
    finally:
        conn.close()


@app.get("/api/snapshots")
def snapshots():
    limit = int(request.args.get("limit", "10"))

    conn = get_conn()
    try:
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
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)