"""
Configuration Settings for Accounting App
"""
import os
import sys

# App Info
APP_NAME = "AccuBooks Pro"
APP_VERSION = "1.0.0"
COMPANY_NAME = "VisionQuantech"

# Paths
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "accubooks.db")
LICENSE_FILE = os.path.join(DATA_DIR, "license.key")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# License Settings
LICENSE_SERVER_URL = "https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/licenses.json"
# ^^^ Replace with your actual Gist URL after creating it
TRIAL_ENTRY_LIMIT = 30
LICENSE_CHECK_INTERVAL_HOURS = 24
GRACE_PERIOD_DAYS = 7  # Allow offline usage for 7 days before blocking

# Database Settings
DB_BACKUP_COUNT = 5  # Keep last 5 backups

# UI Settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 850
SIDEBAR_WIDTH = 220
