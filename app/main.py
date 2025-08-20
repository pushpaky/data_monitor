import matplotlib.pyplot as plt
import pandas as pd
import uuid
import io
import json
import logging

# from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import schedule
import threading

from fastapi import FastAPI, Request, Query, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import Binary, UuidRepresentation
import matplotlib


import smtplib
from email.message import EmailMessage

# import matplotlib


from .fetch_data import get_data_from_mongodb
from .duplicates import find_duplicates
from .missings import find_missing_intervals

# from pytz import timezone
from .config import (
    MONGO_URI,
    DB_NAME,
    COLLECTION_NAME,
    MONGO_MAX_POOL_SIZE,
    MONGO_MIN_POOL_SIZE,
    THREAD_POOL_WORKERS,
    # MAX_RECORDS_LIMIT,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    SMTP_SERVER,
    SMTP_PORT,
    DEVICE_EMAIL_MAP,
    SCHEDULE_TIME,
    CHART_DPI,
)

matplotlib.use("Agg")  # Use non-interactive backend for better performance

# Global MongoDB client for connection pooling
_mongo_client = None
_thread_pool = ThreadPoolExecutor(max_workers=THREAD_POOL_WORKERS)

# Simple cache for device status (cache for 5 minutes since we're fetching ALL devices) # noqa
_device_status_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 300  # 5 minutes in seconds (longer cache for all devices)


def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(
            MONGO_URI,
            uuidRepresentation="standard",
            maxPoolSize=MONGO_MAX_POOL_SIZE,
            minPoolSize=MONGO_MIN_POOL_SIZE,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
        )
    return _mongo_client


app = FastAPI()

# Static and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Global variable to track scheduler thread
_scheduler_thread = None


@app.on_event("startup")
async def startup_event():
    """Initialize the email scheduler when the app starts"""
    global _scheduler_thread

    if DEVICE_EMAIL_MAP:  # Only start if devices are configured
        _scheduler_thread = threading.Thread(
            target=run_email_scheduler, daemon=True
        )  # noqa
        _scheduler_thread.start()
        logging.info("🚀 Email scheduler thread started successfully")
        logging.info(f"📧 Daily reports will be sent at {SCHEDULE_TIME}")
        logging.info(f"📋 Configured devices: {list(DEVICE_EMAIL_MAP.keys())}")
    else:
        logging.warning(
            "⚠️ No devices configured for email reports in DEVICE_EMAIL_MAP"
        )  # noqa


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the app shuts down"""
    logging.info("🛑 Application shutting down...")


# Routes for UI Pages
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/duplicates", response_class=HTMLResponse)
async def duplicates_page(request: Request):
    return templates.TemplateResponse("duplicates.html", {"request": request})


@app.get("/missing-data", response_class=HTMLResponse)
async def missing_data_page(request: Request):
    return templates.TemplateResponse("missing_data.html", {"request": request})  # noqa


@app.get("/fetch", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("fetch.html", {"request": request})


@app.get("/device-status", response_class=HTMLResponse)
async def device_status_page(request: Request):
    return templates.TemplateResponse(
        "device_status.html", {"request": request}
    )  # noqa


@app.get("/all-device-status", response_class=HTMLResponse)
async def all_device_status(request: Request):
    return templates.TemplateResponse("all_status.html", {"request": request})  # noqa


@app.get("/battery-status", response_class=HTMLResponse)
async def battery_status_page(request: Request):
    return templates.TemplateResponse(
        "battery_status.html", {"request": request}
    )  # noqa


@app.get("/email-scheduler", response_class=HTMLResponse)
async def email_scheduler_page(request: Request):
    return templates.TemplateResponse(
        "email_scheduler.html", {"request": request}
    )  # noqa


@app.get("/data-table", response_class=HTMLResponse)
async def data_table_page(request: Request):
    return templates.TemplateResponse("data_table.html", {"request": request})


@app.get("/api/get-data")
async def fetch_data(device_id: str, start_date: str, end_date: str):
    data = get_data_from_mongodb(device_id, start_date, end_date)
    if isinstance(data, dict) and "error" in data:
        return JSONResponse(status_code=400, content={"error": data["error"]})
    return JSONResponse(content=data)


def _generate_chart_sync(records, start_date, end_date):
    """Synchronous chart generation for thread pool execution"""
    try:
        df = pd.DataFrame(records)
        if df.empty:
            return None

        df["devicetime"] = pd.to_datetime(df["devicetime"], errors="coerce")
        df = df.dropna(subset=["devicetime"])
        df["hour"] = df["devicetime"].dt.floor("h")
        df["csm"] = df["data"].apply(
            lambda x: (
                x.get("evt", {}).get("csm", 0) if isinstance(x, dict) else 0
            )  # noqa
        )

        hourly = df.groupby("hour")["csm"].sum().reset_index()

        # Use smaller figure size and lower DPI for faster rendering
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(
            hourly["hour"].dt.strftime("%H:%M"), hourly["csm"], color="skyblue"
        )  # noqa

        ax.set_title(
            f"Hourly Consumption from {start_date} to {end_date}", fontsize=11
        )  # noqa
        ax.set_xlabel("Hour")
        ax.set_ylabel("Total CSM")
        ax.tick_params(axis="x", rotation=45)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")  # Lower DPI # noqa
        buf.seek(0)
        plt.close(fig)  # Important: close figure to free memory
        return buf
    except Exception as e:
        logging.error(f"Chart generation error: {e}")
        return None


@app.post("/api/render-chart")
async def render_chart(request: Request):
    try:
        body = await request.body()
        data = json.loads(body)

        records = data.get("records", [])
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")

        if not records:
            return Response(content="No data to plot", media_type="text/plain")

        # Run chart generation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(
            _thread_pool, _generate_chart_sync, records, start_date, end_date
        )

        if buf is None:
            return Response(
                content="Error generating chart", media_type="text/plain"
            )  # noqa

        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        logging.error(f"Chart API error: {e}")
        return Response(
            content="Internal server error", media_type="text/plain"
        )  # noqa


def safe_deviceid_to_str(deviceid):
    try:
        if isinstance(deviceid, Binary):
            return str(deviceid.as_uuid())
        elif isinstance(deviceid, uuid.UUID):
            return str(deviceid)
        else:
            return str(uuid.UUID(deviceid))  # in case it's a string UUID
    except Exception:
        return str(deviceid)


def _find_duplicates_sync(device_id, start, end):
    """Synchronous duplicate finding for thread pool execution"""
    try:
        client = get_mongo_client()
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

        device_uuid = uuid.UUID(device_id)
        binary_uuid = Binary.from_uuid(device_uuid, UuidRepresentation.STANDARD)  # noqa

        query = {
            "deviceid": binary_uuid,
            "devicetime": {"$gte": start_dt, "$lte": end_dt},
        }

        projection = {"_id": 0, "deviceid": 1, "devicetime": 1}
        # Use limit to prevent excessive memory usage
        cursor = list(collection.find(query, projection).limit(10000))

        # Format results
        for doc in cursor:
            doc["deviceid"] = safe_deviceid_to_str(doc["deviceid"])
            doc["devicetime"] = doc["devicetime"].isoformat()

        duplicates = find_duplicates(cursor)
        return {"count": len(duplicates), "duplicates": duplicates}

    except Exception as e:
        raise e


# API: Find Duplicates
@app.get("/api/find-duplicates")
async def get_duplicate_data(
    device_id: str = Query(...), start: str = Query(...), end: str = Query(...)
):
    try:
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _thread_pool, _find_duplicates_sync, device_id, start, end
        )
        return JSONResponse(content=result)

    except Exception as e:
        logging.error(f"Duplicates API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Missing data
@app.get("/api/missing-intervals")
async def missing_intervals(
    device_id: str = Query(...), start: str = Query(...), end: str = Query(...)
):
    # 1) Parse inputs
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
        dev_uuid = uuid.UUID(device_id)
        bin_dev = Binary.from_uuid(dev_uuid, UuidRepresentation.STANDARD)
    except Exception as e:
        raise HTTPException(400, f"Invalid inputs: {e}")

    # 2) Query MongoDB on devicetime
    client = MongoClient(MONGO_URI, uuidRepresentation="standard")
    col = client[DB_NAME][COLLECTION_NAME]
    records = list(
        col.find(
            {
                "deviceid": bin_dev,
                "devicetime": {"$gte": start_dt, "$lte": end_dt},
            }  # noqa
        )
    )

    # print(f"📦 Retrieved {len(records)} records (using devicetime)")

    if not records:
        return {
            "device_id": device_id,
            "start": start,
            "end": end,
            "count": 0,
            "message": "No records found",
        }

    # 3) Detect missing intervals
    missing = find_missing_intervals(records)

    return {
        "device_id": device_id,
        "start": start,
        "end": end,
        "count": len(missing),
        "missing_intervals": missing,
    }


def _get_all_device_status_sync():
    """Fast device status check using single aggregation query with caching"""
    global _device_status_cache

    # Check cache first
    current_time = time.time()
    if (
        _device_status_cache["data"] is not None
        and current_time - _device_status_cache["timestamp"] < CACHE_DURATION
    ):
        logging.info("Returning cached device status data")
        return _device_status_cache["data"]

    try:
        logging.info("Fetching ALL device status data from database...")
        client = get_mongo_client()
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        # First, get total count of unique devices for logging
        total_devices = len(collection.distinct("data.devId"))
        logging.info(f"Found {total_devices} unique devices in database")

        # Get ALL devices from the database - no limits, fetch everything
        all_devices_pipeline = [
            {
                "$group": {
                    "_id": "$data.devId",
                    "latest_time": {"$max": "$devicetime"},
                    "first_seen": {"$min": "$devicetime"},
                    "record_count": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "device_id": {"$toString": "$_id"},
                    "latest_time": 1,
                    "first_seen": 1,
                    "record_count": 1,
                    "status": {
                        "$cond": {
                            "if": {"$gte": ["$latest_time", one_hour_ago]},
                            "then": "Active",
                            "else": "Inactive",
                        }
                    },
                    "hours_since_last_seen": {
                        "$divide": [
                            {"$subtract": [now, "$latest_time"]},
                            3600000,  # Convert milliseconds to hours
                        ]
                    },
                }
            },
            {
                "$sort": {
                    "status": 1,
                    "latest_time": -1,
                }  # Active first, then by latest activity
            },
            # NO LIMIT - fetch ALL devices in the database
        ]

        # Execute the aggregation to get all devices
        results = list(collection.aggregate(all_devices_pipeline))

        # Format the results with more detailed information
        formatted_results = []
        for result in results:
            latest_time = result["latest_time"]
            hours_since_last = result.get("hours_since_last_seen", 0)

            device_data = {
                "device_id": result["device_id"],
                "status": result["status"],
                "latest_time": latest_time.strftime("%Y-%m-%d %H:%M:%S"),
                "hours_since_last": round(hours_since_last, 1),
                "record_count": result["record_count"],
                "first_seen": (
                    result["first_seen"].strftime("%Y-%m-%d %H:%M:%S")
                    if result.get("first_seen")
                    else "Unknown"
                ),
            }

            # Set inactive start/end times
            if result["status"] == "Inactive":
                device_data["inactive_start"] = latest_time.strftime(
                    "%Y-%m-%d %H:%M"
                )  # noqa
                device_data["inactive_end"] = "Ongoing"

                # Calculate how long it's been inactive
                if hours_since_last < 24:
                    device_data["inactive_duration"] = (
                        f"{round(hours_since_last, 1)} hours"
                    )
                else:
                    days = round(hours_since_last / 24, 1)
                    device_data["inactive_duration"] = f"{days} days"
            else:
                device_data["inactive_start"] = "-"
                device_data["inactive_end"] = "-"
                device_data["inactive_duration"] = "-"

            formatted_results.append(device_data)

        # Cache the results
        _device_status_cache["data"] = formatted_results
        _device_status_cache["timestamp"] = current_time

        active_count = len(
            [d for d in formatted_results if d["status"] == "Active"]
        )  # noqa
        inactive_count = len(formatted_results) - active_count

        logging.info(
            f"Successfully fetched ALL {len(formatted_results)} devices: {active_count} active, {inactive_count} inactive"  # noqa
        )
        return formatted_results

    except Exception as e:
        logging.error(f"Device status error: {e}")
        return []


# API to get active/inactive status and intervals
@app.get("/api/all-device-status")
async def get_all_device_status():
    try:
        start_time = time.time()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _thread_pool, _get_all_device_status_sync
        )  # noqa

        end_time = time.time()
        execution_time = end_time - start_time

        logging.info(
            f"Device status API completed in {execution_time:.2f} seconds"
        )  # noqa

        return JSONResponse(content=jsonable_encoder(result))

    except Exception as e:
        logging.error(f"All device status API error: {e}")
        return JSONResponse(content=[])


@app.post("/api/clear-device-status-cache")
async def clear_device_status_cache():
    """Clear the device status cache to force fresh data"""
    global _device_status_cache
    _device_status_cache = {"data": None, "timestamp": 0}
    return JSONResponse(content={"message": "Cache cleared successfully"})


# ============================================================================
# EMAIL SCHEDULING FUNCTIONS (Integrated from main.py)
# ============================================================================
matplotlib.use("Agg")  # Use non-interactive backend


def fetch_data_for_email(device_id):
    """Fetch last 24 hours of data for email reports"""
    try:
        client = get_mongo_client()
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Calculate time range (last 24 hours)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        # Convert device_id to binary UUID for querying
        device_uuid = uuid.UUID(device_id)
        device_id_binary = Binary.from_uuid(
            device_uuid, UuidRepresentation.STANDARD
        )  # noqa

        # Query for the device data
        query = {
            "deviceid": device_id_binary,
            "devicetime": {"$gte": start_time, "$lte": end_time},
        }

        # Fetch records
        cursor = collection.find(query).sort("devicetime", 1)
        records = list(cursor)

        logging.info(f"Fetched {len(records)} records for device {device_id}")
        return records

    except Exception as e:
        logging.error(f"Error fetching data for device {device_id}: {e}")
        return []


def get_battery_status_for_email(records):
    """Extract battery status information from records"""
    if not records:
        return {"status": "No data", "voltage": "N/A", "power_on": "N/A"}

    # Get the latest battery info
    latest_record = max(
        records, key=lambda x: x.get("devicetime", datetime.min)
    )  # noqa
    binfo = latest_record.get("data", {}).get("binfo", {})

    voltage = binfo.get("bvt", 0)
    power_on = binfo.get("bpon", 0)

    # Determine battery status based on voltage
    if voltage >= 3.7:
        status = "Good"
        status_color = "green"
    elif voltage >= 3.4:
        status = "Low"
        status_color = "orange"
    elif voltage > 0:
        status = "Critical"
        status_color = "red"
    else:
        status = "Unknown"
        status_color = "gray"

    return {
        "status": status,
        "voltage": f"{voltage:.2f}V" if voltage > 0 else "N/A",
        "power_on": "Yes" if power_on else "No",
        "status_color": status_color,
    }


def generate_chart_for_email(records, device_id):
    """Generate chart for email reports"""
    try:
        df = pd.DataFrame(records)
        if df.empty:
            return None

        df["devicetime"] = pd.to_datetime(df["devicetime"], errors="coerce")
        df = df.dropna(subset=["devicetime"])
        df["hour"] = df["devicetime"].dt.floor("h")
        df["csm"] = df["data"].apply(
            lambda x: (
                x.get("evt", {}).get("csm", 0) if isinstance(x, dict) else 0
            )  # noqa
        )

        hourly = df.groupby("hour")["csm"].sum().reset_index()

        # Create figure with subplots for consumption and battery info
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

        # Consumption chart
        ax1.bar(
            hourly["hour"].dt.strftime("%H:%M"), hourly["csm"], color="skyblue"
        )  # noqa
        ax1.set_title(f"Hourly Consumption - {device_id}", fontsize=11)
        ax1.set_xlabel("Hour")
        ax1.set_ylabel("Total CSM")
        ax1.tick_params(axis="x", rotation=45)

        # Battery status chart
        battery_info = get_battery_status_for_email(records)
        df["bvt"] = df["data"].apply(
            lambda x: (
                x.get("binfo", {}).get("bvt", 0) if isinstance(x, dict) else 0
            )  # noqa
        )

        # Plot battery voltage over time (hourly average)
        battery_hourly = df.groupby("hour")["bvt"].mean().reset_index()
        if not battery_hourly.empty:
            ax2.plot(
                battery_hourly["hour"].dt.strftime("%H:%M"),
                battery_hourly["bvt"],
                color="green",
                marker="o",
                linewidth=2,
            )
            ax2.set_title(
                f"Battery Voltage Over Time - {device_id}", fontsize=11
            )  # noqa
            ax2.set_xlabel("Hour")
            ax2.set_ylabel("Voltage (V)")
            ax2.tick_params(axis="x", rotation=45)
            ax2.grid(True, alpha=0.3)

            # Add battery status text
            ax2.text(
                0.02,
                0.98,
                f"Current Status: {battery_info['status']} ({battery_info['voltage']})",  # noqa
                transform=ax2.transAxes,
                verticalalignment="top",
                bbox=dict(
                    boxstyle="round",
                    facecolor=battery_info["status_color"],
                    alpha=0.3,  # noqa
                ),
            )

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=CHART_DPI, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)  # Close the figure to free memory
        return buf

    except Exception as e:
        logging.error(f"Error generating chart: {e}")
        return None


def generate_csv_for_email(records):
    """Generate CSV data for email attachment"""
    try:
        if not records:
            return None

        # Convert to DataFrame and format for CSV
        # df = pd.DataFrame(records)

        # Select and rename columns for CSV
        csv_data = []
        for record in records:
            row = {
                "devicetime": record.get("devicetime", ""),
                "device_id": record.get("deviceid", ""),
                "etm": record.get("data", {}).get("evt", {}).get("etm", ""),
                "csm": record.get("data", {}).get("evt", {}).get("csm", ""),
                "battery_voltage": record.get("data", {})
                .get("binfo", {})
                .get("bvt", ""),
                "battery_power": record.get("data", {})
                .get("binfo", {})
                .get("bpon", ""),
            }
            csv_data.append(row)

        # Convert to CSV
        df_csv = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        df_csv.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        return csv_buffer

    except Exception as e:
        logging.error(f"Error generating CSV: {e}")
        return None


def send_email_report(
    to_email, device_id, chart_buf, csv_buf=None, battery_info=None
):  # noqa
    """Send email report with chart and data"""
    try:
        logging.info(f"📧 Preparing email for {device_id} to {to_email}")

        msg = EmailMessage()
        msg["Subject"] = (
            f"Daily Report for Device {device_id} - {datetime.now().strftime('%Y-%m-%d')}"  # noqa
        )
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email

        logging.info(f"📧 Email headers set for {device_id}")

        # Enhanced email content with battery status
        battery_section = ""
        if battery_info:
            battery_section = f"""

        BATTERY STATUS:
        - Status: {battery_info['status']}
        - Voltage: {battery_info['voltage']}
        - Power On: {battery_info['power_on']}
        """

        email_content = f"""
        Daily Device Report - {datetime.now().strftime('%Y-%m-%d')}

        Device ID: {device_id}
        Report Period: Last 24 hours
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        {battery_section}

        Please find attached:
        - Hourly consumption and battery voltage chart (PNG)
        - Raw data export including battery info (CSV)

        This is an automated report sent every 24 hours.

        Best regards,
        Aquesa Data Monitor System
        """

        msg.set_content(email_content)
        logging.info(f"📧 Email content set for {device_id}")

        # Attach chart image
        if chart_buf:
            try:
                chart_data = chart_buf.read()
                chart_filename = (
                    f"chart_{device_id}_{datetime.now().strftime('%Y%m%d')}.png"  # noqa
                )
                msg.add_attachment(
                    chart_data,
                    maintype="image",
                    subtype="png",
                    filename=chart_filename,  # noqa
                )
                chart_buf.seek(0)
                logging.info(
                    f"📊 Chart attached for {device_id} ({len(chart_data)} bytes)"  # noqa
                )
            except Exception as e:
                logging.error(f"❌ Failed to attach chart for {device_id}: {e}")

        # Attach CSV if provided
        if csv_buf:
            try:
                csv_data = csv_buf.getvalue()  # Use getvalue() for StringIO
                csv_filename = (
                    f"data_{device_id}_{datetime.now().strftime('%Y%m%d')}.csv"
                )
                msg.add_attachment(
                    csv_data.encode("utf-8"),
                    maintype="text",
                    subtype="csv",
                    filename=csv_filename,
                )
                csv_buf.seek(0)
                logging.info(
                    f"📄 CSV attached for {device_id} ({len(csv_data)} chars)"
                )  # noqa
            except Exception as e:
                logging.error(f"❌ Failed to attach CSV for {device_id}: {e}")

        # Send email
        logging.info(f"📤 Connecting to SMTP server for {device_id}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            logging.info(f"🔐 SMTP TLS started for {device_id}")
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            logging.info(f"🔑 SMTP login successful for {device_id}")
            smtp.send_message(msg)
            logging.info(f"📨 Email message sent for {device_id}")

        logging.info(
            f"✅ Email sent successfully to {to_email} for device {device_id}"
        )  # noqa
        return True

    except Exception as e:
        logging.error(
            f"❌ Failed to send email to {to_email} for device {device_id}: {e}"
        )
        logging.error(f"❌ Error type: {type(e).__name__}")
        import traceback

        logging.error(f"❌ Full traceback: {traceback.format_exc()}")
        return False


def process_and_send_emails():
    """Process and send emails for all configured devices"""
    logging.info(f"⏰ Running scheduled email at {datetime.now()}")

    for device_id, email in DEVICE_EMAIL_MAP.items():
        try:
            logging.info(f"📧 Processing device: {device_id}")

            # Fetch data
            records = fetch_data_for_email(device_id)
            if not records:
                logging.warning(f"⚠️ No data found for {device_id}")
                continue

            # Generate chart
            chart = generate_chart_for_email(records, device_id)
            if not chart:
                logging.warning(f"⚠️ No chart generated for {device_id}")
                continue

            # Generate CSV
            csv_data = generate_csv_for_email(records)

            # Get battery info
            battery_info = get_battery_status_for_email(records)

            # Send email
            if send_email_report(
                email, device_id, chart, csv_data, battery_info
            ):  # noqa
                logging.info(
                    f"✅ Report sent for {device_id} - Battery: {battery_info['status']} ({battery_info['voltage']})"  # noqa
                )
            else:
                logging.error(f"❌ Failed to send report for {device_id}")

        except Exception as e:
            logging.error(f"❌ Error processing device {device_id}: {e}")


def run_email_scheduler():
    """Background thread function to run the email scheduler"""
    # Schedule daily reports
    schedule.every().day.at(SCHEDULE_TIME).do(process_and_send_emails)

    logging.info(
        f"📅 Email scheduler started - reports will be sent daily at {SCHEDULE_TIME}"  # noqa
    )
    logging.info(f"📋 Configured devices: {list(DEVICE_EMAIL_MAP.keys())}")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


# ============================================================================
# EMAIL SCHEDULER API ENDPOINTS
# ============================================================================


@app.get("/api/email-scheduler-status")
async def get_email_scheduler_status():
    """Get the status of the email scheduler"""
    global _scheduler_thread

    is_running = _scheduler_thread is not None and _scheduler_thread.is_alive()
    next_run = None

    # Get next scheduled run time
    jobs = schedule.jobs
    if jobs:
        next_run = min(job.next_run for job in jobs).isoformat()

    return JSONResponse(
        content={
            "scheduler_running": is_running,
            "next_scheduled_run": next_run,
            "schedule_time": SCHEDULE_TIME,
            "configured_devices": len(DEVICE_EMAIL_MAP),
            "device_list": list(DEVICE_EMAIL_MAP.keys()),
        }
    )


@app.post("/api/send-test-email")
async def send_test_email(device_id: str = None):
    """Manually trigger email sending for testing"""
    try:
        if not device_id:
            # Send to all devices
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_thread_pool, process_and_send_emails)
            return JSONResponse(
                content={
                    "message": "Test emails sent to all configured devices",
                    "devices_processed": len(DEVICE_EMAIL_MAP),
                }
            )
        else:
            # Send to specific device
            if device_id not in DEVICE_EMAIL_MAP:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found in email configuration",  # noqa
                )

            email = DEVICE_EMAIL_MAP[device_id]

            def send_single_test_email():
                records = fetch_data_for_email(device_id)
                if not records:
                    return False

                chart = generate_chart_for_email(records, device_id)
                csv_data = generate_csv_for_email(records)
                battery_info = get_battery_status_for_email(records)

                return send_email_report(
                    email, device_id, chart, csv_data, battery_info
                )

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                _thread_pool, send_single_test_email
            )  # noqa

            if success:
                return JSONResponse(
                    content={
                        "message": f"Test email sent successfully to {email}",
                        "device_id": device_id,
                    }
                )
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to send test email"
                )  # noqa

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Test email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


logging.basicConfig(level=logging.INFO)


# Pydantic Response Schema
class DeviceStatusResponse(BaseModel):
    device_id: str
    status: str
    last_seen: datetime
    inactive_since: datetime | None = None


def _check_single_device_status_sync(device_id: str):
    """Synchronous single device status check"""
    try:
        client = get_mongo_client()
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Convert device_id to proper format for querying
        try:
            device_uuid = uuid.UUID(device_id)
            device_id_binary = Binary.from_uuid(
                device_uuid, UuidRepresentation.STANDARD
            )
        except ValueError:
            # If not a valid UUID, try searching by data.devId string field
            device_id_binary = None

        # Try both query methods to find the device
        query_options = []

        if device_id_binary:
            # Query by deviceid (binary UUID)
            query_options.append({"deviceid": device_id_binary})

        # Query by data.devId (string)
        query_options.append({"data.devId": device_id})

        latest = None
        for query in query_options:
            latest = collection.find_one(query, sort=[("devicetime", -1)])
            if latest:
                break

        if not latest:
            logging.warning(f"No data found for device ID: {device_id}")
            return None

        last_seen = latest["devicetime"]
        now = datetime.utcnow()

        # Determine if inactive for more than 1 hour (more reasonable threshold) # noqa
        if now - last_seen > timedelta(hours=1):
            logging.info(
                f"[INACTIVE] Device {device_id} last seen at {last_seen}"
            )  # noqa
            return {
                "device_id": device_id,
                "status": "inactive",
                "last_seen": last_seen,
                "inactive_since": last_seen,
            }
        else:
            logging.info(
                f"[ACTIVE] Device {device_id} last seen at {last_seen}"
            )  # noqa
            return {
                "device_id": device_id,
                "status": "active",
                "last_seen": last_seen,
                "inactive_since": None,
            }

    except Exception as e:
        logging.error(f"❌ Error checking device status for {device_id}: {e}")
        return None


@app.get("/api/device-status", response_model=DeviceStatusResponse)
async def check_device_status(device_id: str):
    try:
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _thread_pool, _check_single_device_status_sync, device_id
        )

        if result is None:
            raise HTTPException(
                status_code=404, detail="No data found for device"
            )  # noqa

        return result

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logging.error(f"❌ Device status API error for {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def _get_battery_status_sync(device_id):
    """Synchronous battery status check for thread pool execution"""
    try:
        client = get_mongo_client()
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        device_id_uuid = uuid.UUID(device_id)
        device_id_binary = Binary.from_uuid(
            device_id_uuid, UuidRepresentation.STANDARD
        )  # noqa

        # Get the most recent record with battery info
        latest = collection.find_one(
            {"deviceid": device_id_binary},
            {"data.binfo.bvt": 1, "data.binfo.bpon": 1, "devicetime": 1},
            sort=[("devicetime", -1)],
        )

        if not latest:
            return None

        binfo = latest.get("data", {}).get("binfo", {})
        voltage = binfo.get("bvt", 0)
        power_on = binfo.get("bpon", 0)
        last_update = latest.get("devicetime")

        # Determine battery status based on voltage
        if voltage >= 3.7:
            status = "Good"
            status_color = "#28a745"  # Green
        elif voltage >= 3.4:
            status = "Low"
            status_color = "#ffc107"  # Yellow/Orange
        elif voltage > 0:
            status = "Critical"
            status_color = "#dc3545"  # Red
        else:
            status = "Unknown"
            status_color = "#6c757d"  # Gray

        return {
            "device_id": device_id,
            "battery_status": status,
            "voltage": f"{voltage:.2f}V" if voltage > 0 else "N/A",
            "power_on": bool(power_on),
            "status_color": status_color,
            "last_update": last_update.isoformat() if last_update else None,
        }

    except Exception as e:
        logging.error(f"Battery status sync error: {e}")
        return None


@app.get("/api/battery-status")
async def get_battery_status(device_id: str = Query(...)):
    """Get battery status for a specific device"""
    try:
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _thread_pool, _get_battery_status_sync, device_id
        )

        if result is None:
            raise HTTPException(
                status_code=404, detail="No data found for device"
            )  # noqa

        return JSONResponse(content=result)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Error getting battery status for {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
