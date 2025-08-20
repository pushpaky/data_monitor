#!/usr/bin/env python3
"""
⚠️  DEPRECATED - Email Scheduler (Standalone)

This file is no longer needed! Email scheduling has been integrated
into the web application.

To run the complete system (web app + email scheduler), use:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

This will start both the web interface AND the email scheduler automatically.
"""

print("⚠️  DEPRECATED: Email scheduling is now integrated into the web application!")
print("🚀 To run the complete system, use:")
print("   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
print("")
print("This will start both the web interface AND email scheduler automatically.")
exit(1)

import schedule
import time
import uuid
import os
import pytz
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.binary import Binary, UuidRepresentation
import pandas as pd
import matplotlib.pyplot as plt
import io
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
from app.config import (
    MONGO_URI, DB_NAME, COLLECTION_NAME, EMAIL_ADDRESS, EMAIL_PASSWORD,
    SMTP_SERVER, SMTP_PORT, DEVICE_EMAIL_MAP, SCHEDULE_TIME, TIMEZONE,
    MONGO_MAX_POOL_SIZE, MONGO_MIN_POOL_SIZE, CHART_DPI
)


def fetch_data(device_id):
    try:
        client = MongoClient(MONGO_URI, uuidRepresentation="standard")
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        device_id_uuid = uuid.UUID(device_id)
        device_id_binary = Binary.from_uuid(device_id_uuid, UuidRepresentation.STANDARD) # noqa

        # Last 24 hours
        end = datetime.utcnow()
        start = end - timedelta(days=1)

        query = {
            "deviceid": device_id_binary,
            "devicetime": {"$gte": start, "$lte": end},
        }

        projection = {
            "_id": 0,
            "deviceid": 1,
            "devicetime": 1,
            "data.evt.etm": 1,
            "data.evt.csm": 1,
            "data.binfo.bvt": 1,
            "data.binfo.bpon": 1,
        }

        results = list(collection.find(query, projection))
        return results

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []


def get_battery_status(records):
    """Extract battery status information from records"""
    if not records:
        return {"status": "No data", "voltage": "N/A", "power_on": "N/A"}

    # Get the latest battery info
    latest_record = max(records, key=lambda x: x.get("devicetime", datetime.min))
    binfo = latest_record.get("data", {}).get("binfo", {})

    voltage = binfo.get("bvt", 0)
    power_on = binfo.get("bpon", 0)

    # Determine battery status based on voltage (typical Li-ion battery ranges)
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
        "status_color": status_color
    }


def generate_chart(records, device_id):
    try:
        df = pd.DataFrame(records)
        if df.empty:
            return None

        df["devicetime"] = pd.to_datetime(df["devicetime"], errors="coerce")
        df = df.dropna(subset=["devicetime"])
        df["hour"] = df["devicetime"].dt.floor("h")
        df["csm"] = df["data"].apply(
            lambda x: x.get("evt", {}).get("csm", 0) if isinstance(x, dict) else 0
        )

        hourly = df.groupby("hour")["csm"].sum().reset_index()

        # Use smaller figure size and lower DPI for faster generation
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

        # Consumption chart
        ax1.bar(hourly["hour"].dt.strftime("%H:%M"), hourly["csm"], color="skyblue")
        ax1.set_title(f"Hourly Consumption - {device_id}", fontsize=11)
        ax1.set_xlabel("Hour")
        ax1.set_ylabel("Total CSM")
        ax1.tick_params(axis="x", rotation=45)

        # Battery status chart
        battery_info = get_battery_status(records)
        df["bvt"] = df["data"].apply(
            lambda x: x.get("binfo", {}).get("bvt", 0) if isinstance(x, dict) else 0
        )

        # Plot battery voltage over time (hourly average)
        battery_hourly = df.groupby("hour")["bvt"].mean().reset_index()
        if not battery_hourly.empty:
            ax2.plot(battery_hourly["hour"].dt.strftime("%H:%M"), battery_hourly["bvt"],
                     color="green", marker="o", linewidth=2)
            ax2.set_title(f"Battery Voltage Over Time - {device_id}", fontsize=11)
            ax2.set_xlabel("Hour")
            ax2.set_ylabel("Voltage (V)")
            ax2.tick_params(axis="x", rotation=45)
            ax2.grid(True, alpha=0.3)

            # Add battery status text
            ax2.text(0.02, 0.98, f"Current Status: {battery_info['status']} ({battery_info['voltage']})",
                     transform=ax2.transAxes, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor=battery_info['status_color'], alpha=0.3))

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=200, bbox_inches='tight')  # Lower DPI for speed
        buf.seek(0)
        plt.close(fig)  # Close the figure to free memory
        return buf

    except Exception as e:
        print(f"Error generating chart: {e}")
        return None


def generate_csv(records):
    csv_buf = io.StringIO()
    csv_buf.write("deviceid,devicetime,etm,csm,bvt,bpon\n")
    for rec in records:
        deviceid = rec.get("deviceid", "")
        devicetime = rec.get("devicetime", "")
        etm = rec.get("data", {}).get("evt", {}).get("etm", "")
        csm = rec.get("data", {}).get("evt", {}).get("csm", "")
        bvt = rec.get("data", {}).get("binfo", {}).get("bvt", "")
        bpon = rec.get("data", {}).get("binfo", {}).get("bpon", "")
        csv_buf.write(f"{deviceid},{devicetime},{etm},{csm},{bvt},{bpon}\n")

    return io.BytesIO(csv_buf.getvalue().encode())


def send_email(to_email, device_id, chart_buf, csv_buf=None, battery_info=None):
    msg = EmailMessage()
    msg["Subject"] = f"Daily Report for Device {device_id} - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

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

    # Attach chart image
    if chart_buf:
        msg.add_attachment(
            chart_buf.read(), maintype="image", subtype="png",
            filename=f"chart_{device_id}_{datetime.now().strftime('%Y%m%d')}.png"
        )
        chart_buf.seek(0)

    # Attach CSV if provided
    if csv_buf:
        msg.add_attachment(
            csv_buf.read(), maintype="text", subtype="csv",
            filename=f"data_{device_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        csv_buf.seek(0)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"✅ Email sent to {to_email} for device {device_id}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email} for device {device_id}: {e}")


def process_and_send():
    print(f"⏰ Running scheduled email at {datetime.now()}")
    for device_id, email in DEVICE_EMAIL_MAP.items():
        print(f"📧 Processing device: {device_id}")
        records = fetch_data(device_id)
        if not records:
            print(f"⚠️ No data found for {device_id}")
            continue

        chart = generate_chart(records, device_id)
        csv_data = generate_csv(records)
        battery_info = get_battery_status(records)

        if chart:
            send_email(email, device_id, chart, csv_data, battery_info)
            print(f"✅ Report sent for {device_id} - Battery: {battery_info['status']} ({battery_info['voltage']})")
        else:
            print(f"⚠️ No chart generated for {device_id}")



# Schedule daily reports using dynamic configuration
schedule.every().day.at(SCHEDULE_TIME).do(process_and_send)

print("📅 Daily email scheduler started...")
print(f"📧 Reports will be sent every 24 hours at {SCHEDULE_TIME}")
print(f"🌍 Timezone: {TIMEZONE}")
print(f"📋 Configured devices: {list(DEVICE_EMAIL_MAP.keys())}")
print("Press Ctrl+C to stop the scheduler")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
