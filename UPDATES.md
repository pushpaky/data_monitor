# Aquesa Data Monitor - Recent Updates

## Summary of Changes

This document outlines the recent updates made to the Aquesa Data Monitor application based on user requirements.

## 🔧 Changes Made

### 1. Fixed Navigation Issues
- **Problem**: Navigation links were opening in new tabs (`target="_blank"`)
- **Solution**: Removed `target="_blank"` attributes from all navigation links
- **Files Updated**: All HTML templates in `app/templates/`
- **Result**: All navigation now stays within the same tab

### 2. Enhanced Email Scheduling System
- **Problem**: Email reports needed to be sent every 24 hours for respective device IDs
- **Solution**: 
  - Improved the scheduling system in `main.py`
  - Set daily reports to run at 8:00 AM every day
  - Enhanced email content with battery status information
  - Added individual device report processing capability
- **Files Updated**: `main.py`
- **Features Added**:
  - Automated daily reports at 8:00 AM
  - Enhanced email content with battery status
  - Better error handling and logging
  - CSV data attachment (re-enabled)

### 3. Updated Battery Status Colors
- **Problem**: Battery status colors needed improvement (red to green theme)
- **Solution**: Updated color scheme for better visibility and consistency
- **Files Updated**: 
  - `static/js/script_all_status.js`
  - `static/js/script_status.js`
- **New Color Scheme**:
  - Active/Good: `#28a745` (Green)
  - Inactive/Low: `#ffc107` (Yellow/Orange)
  - Critical: `#dc3545` (Red)
  - Unknown: `#6c757d` (Gray)

### 4. Added Battery Status Monitoring
- **New Feature**: Dedicated battery status page and API
- **Files Added**:
  - `app/templates/battery_status.html`
  - `static/js/script_battery.js`
- **Files Updated**: `app/main.py`
- **Features**:
  - Real-time battery voltage monitoring
  - Visual battery level indicator
  - Battery status classification (Good/Low/Critical)
  - Power-on status display
  - Last update timestamp

### 5. Enhanced Charts and Reports
- **Improvement**: Charts now include both consumption and battery voltage data
- **Files Updated**: `main.py`
- **Features**:
  - Dual-panel charts (consumption + battery voltage)
  - Battery status information in email reports
  - Higher resolution chart exports (300 DPI)
  - Better memory management (plt.close())

## 📧 Email Report Features

### Automated Scheduling
- Reports sent daily at 8:00 AM
- Covers last 24 hours of data
- Individual processing for each device ID

### Email Content Includes
- Device ID and report period
- Battery status summary (voltage, power status)
- Hourly consumption chart with battery voltage overlay
- Raw data CSV export
- Professional formatting

### Device Configuration
Current configured devices in `DEVICE_EMAIL_MAP`:
- `6eb8e219-36ba-496e-b0a1-91577cee61bf` → `pushpakallesh23@gmail.com`
- `b175f67b-e665-49fc-b215-8d5bcb9d1597` → `pushpaky8@gmail.com`

## 🔋 Battery Status Features

### Web Interface
- New "Battery Status" page accessible from navigation
- Real-time battery information lookup
- Visual battery level indicator
- Color-coded status display

### API Endpoint
- `GET /api/battery-status?device_id={id}`
- Returns JSON with battery voltage, status, and power information
- Proper error handling for invalid device IDs

### Battery Status Classification
- **Good** (≥3.7V): Green color, optimal battery level
- **Low** (3.4V-3.6V): Yellow/Orange color, battery needs attention
- **Critical** (<3.4V): Red color, immediate attention required
- **Unknown** (0V): Gray color, no battery data available

## 🎨 UI/UX Improvements

### Navigation
- Consistent navigation across all pages
- Single-tab browsing experience
- Added "Battery Status" to all navigation menus

### Color Scheme
- Professional color palette
- Consistent status indicators
- Better accessibility with high contrast colors

### Dashboard Updates
- Added information about automated email reports
- Enhanced description of application features
- Visual indicators for new features

## 🚀 How to Use

### Running the Email Scheduler
```bash
python main.py
```
This will start the daily email scheduler that runs continuously.

### Running the Web Application
```bash
# Start the FastAPI application
uvicorn app.main:app --reload
```

### Accessing Features
1. **Dashboard**: `http://localhost:8000/`
2. **Battery Status**: `http://localhost:8000/battery-status`
3. **All Device Status**: `http://localhost:8000/all-device-status`
4. **Other features**: Available through navigation menu

## 📝 Configuration

### Email Settings
Update the following in `main.py`:
```python
EMAIL_ADDRESS = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"
```

### Device Mapping
Add or modify devices in `DEVICE_EMAIL_MAP`:
```python
DEVICE_EMAIL_MAP = {
    "device-uuid": "recipient@email.com",
    # Add more devices as needed
}
```

### Schedule Timing
Modify the schedule time in `main.py`:
```python
schedule.every().day.at("08:00").do(process_and_send)  # Change time as needed
```

## 📋 Production Ready

The application is now configured for production use with:
- Daily email reports at 8:00 AM
- Optimized performance
- Professional email formatting
- Battery monitoring and alerts
- Single-tab navigation
- Enhanced color schemes
