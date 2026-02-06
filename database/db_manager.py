"""
Database Manager with WAL Mode for Data Safety
Handles all database connections and ensures no data loss
"""
import sqlite3
import threading
import shutil
import os
from datetime import datetime
from contextlib import contextmanager

import config

class DatabaseManager:
    """Thread-safe SQLite database manager with WAL mode"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                config.DB_PATH,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency and crash recovery
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection.execute("PRAGMA busy_timeout=30000")
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations with auto-commit"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def execute(self, query, params=None):
        """Execute a query and return cursor"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_many(self, query, params_list):
        """Execute many queries"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
    
    def insert(self, query, params=None):
        """Insert and return last row id"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.lastrowid
    
    def _init_database(self):
        """Initialize database with all tables"""
        self._create_tables()
        self._seed_default_data()
    
    def _create_tables(self):
        """Create all required tables"""
        with self.get_cursor() as cursor:
            # License table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license (
                    id INTEGER PRIMARY KEY,
                    license_key TEXT,
                    machine_id TEXT,
                    status TEXT DEFAULT 'TRIAL',
                    activation_date TEXT,
                    last_validated TEXT,
                    last_validation_result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Accounts (Chart of Accounts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE')),
                    sub_type TEXT,
                    parent_id INTEGER REFERENCES accounts(id),
                    opening_balance REAL DEFAULT 0,
                    is_system INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    gst_applicable INTEGER DEFAULT 0,
                    hsn_code TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transactions (Journal/Voucher Headers)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_number TEXT UNIQUE NOT NULL,
                    voucher_type TEXT NOT NULL CHECK(voucher_type IN ('JOURNAL', 'PAYMENT', 'RECEIPT', 'CONTRA', 'PURCHASE', 'SALES')),
                    date TEXT NOT NULL,
                    narration TEXT,
                    reference TEXT,
                    total_amount REAL DEFAULT 0,
                    is_posted INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transaction Lines (Journal Entries)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transaction_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    debit REAL DEFAULT 0,
                    credit REAL DEFAULT 0,
                    particulars TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Expenses tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    account_id INTEGER REFERENCES accounts(id),
                    amount REAL NOT NULL,
                    category TEXT,
                    description TEXT,
                    payment_mode TEXT,
                    reference TEXT,
                    gst_amount REAL DEFAULT 0,
                    transaction_id INTEGER REFERENCES transactions(id),
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Audit Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT,
                    record_id INTEGER,
                    action TEXT,
                    old_data TEXT,
                    new_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transaction_lines_txn ON transaction_lines(transaction_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transaction_lines_account ON transaction_lines(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type)")
    
    def _seed_default_data(self):
        """Seed default Chart of Accounts if empty"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM accounts")
            if cursor.fetchone()[0] > 0:
                return  # Already has data
            
            # Default Indian Chart of Accounts
            default_accounts = [
                # Assets
                ('1000', 'Cash', 'ASSET', 'CURRENT', None, 1),
                ('1001', 'Cash in Hand', 'ASSET', 'CURRENT', 1, 0),
                ('1002', 'Petty Cash', 'ASSET', 'CURRENT', 1, 0),
                ('1100', 'Bank Accounts', 'ASSET', 'CURRENT', None, 1),
                ('1101', 'Bank - Primary', 'ASSET', 'CURRENT', 4, 0),
                ('1102', 'Bank - Savings', 'ASSET', 'CURRENT', 4, 0),
                ('1200', 'Accounts Receivable', 'ASSET', 'CURRENT', None, 1),
                ('1201', 'Sundry Debtors', 'ASSET', 'CURRENT', 7, 0),
                ('1300', 'Inventory', 'ASSET', 'CURRENT', None, 1),
                ('1400', 'Fixed Assets', 'ASSET', 'FIXED', None, 1),
                ('1401', 'Furniture & Fixtures', 'ASSET', 'FIXED', 10, 0),
                ('1402', 'Computer Equipment', 'ASSET', 'FIXED', 10, 0),
                
                # Liabilities
                ('2000', 'Accounts Payable', 'LIABILITY', 'CURRENT', None, 1),
                ('2001', 'Sundry Creditors', 'LIABILITY', 'CURRENT', 13, 0),
                ('2100', 'Loans', 'LIABILITY', 'LONG_TERM', None, 1),
                ('2200', 'Duties & Taxes', 'LIABILITY', 'CURRENT', None, 1),
                ('2201', 'GST Payable', 'LIABILITY', 'CURRENT', 16, 1),
                ('2202', 'GST Input Credit', 'ASSET', 'CURRENT', None, 1),
                ('2203', 'TDS Payable', 'LIABILITY', 'CURRENT', 16, 1),
                
                # Equity
                ('3000', 'Capital Account', 'EQUITY', None, None, 1),
                ('3001', 'Owner Capital', 'EQUITY', None, 20, 0),
                ('3100', 'Retained Earnings', 'EQUITY', None, None, 1),
                
                # Income
                ('4000', 'Sales', 'INCOME', None, None, 1),
                ('4001', 'Sales - Goods', 'INCOME', None, 23, 0),
                ('4002', 'Sales - Services', 'INCOME', None, 23, 0),
                ('4100', 'Other Income', 'INCOME', None, None, 1),
                ('4101', 'Interest Received', 'INCOME', None, 26, 0),
                ('4102', 'Discount Received', 'INCOME', None, 26, 0),
                
                # Expenses
                ('5000', 'Cost of Goods Sold', 'EXPENSE', None, None, 1),
                ('5001', 'Purchases', 'EXPENSE', None, 29, 0),
                ('5100', 'Operating Expenses', 'EXPENSE', None, None, 1),
                ('5101', 'Salaries & Wages', 'EXPENSE', None, 31, 0),
                ('5102', 'Rent', 'EXPENSE', None, 31, 0),
                ('5103', 'Utilities', 'EXPENSE', None, 31, 0),
                ('5104', 'Office Expenses', 'EXPENSE', None, 31, 0),
                ('5105', 'Travel & Conveyance', 'EXPENSE', None, 31, 0),
                ('5106', 'Telephone & Internet', 'EXPENSE', None, 31, 0),
                ('5107', 'Professional Fees', 'EXPENSE', None, 31, 0),
                ('5108', 'Bank Charges', 'EXPENSE', None, 31, 0),
                ('5109', 'Depreciation', 'EXPENSE', None, 31, 1),
                ('5110', 'Miscellaneous Expenses', 'EXPENSE', None, 31, 0),
            ]
            
            for code, name, acc_type, sub_type, parent_id, is_system in default_accounts:
                cursor.execute("""
                    INSERT INTO accounts (code, name, type, sub_type, parent_id, is_system)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code, name, acc_type, sub_type, parent_id, is_system))
            
            # Default settings
            default_settings = [
                ('company_name', 'My Company'),
                ('company_address', ''),
                ('company_gstin', ''),
                ('company_pan', ''),
                ('financial_year_start', '04'),  # April
                ('currency_symbol', '₹'),
                ('date_format', 'DD-MM-YYYY'),
                ('voucher_prefix', 'VCH'),
            ]
            
            for key, value in default_settings:
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value)
                )
    
    def backup_database(self):
        """Create a backup of the database"""
        if not os.path.exists(config.DB_PATH):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"accubooks_backup_{timestamp}.db"
        backup_path = os.path.join(config.BACKUP_DIR, backup_name)
        
        # Checkpoint WAL before backup
        with self.get_cursor() as cursor:
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        shutil.copy2(config.DB_PATH, backup_path)
        
        # Cleanup old backups
        self._cleanup_old_backups()
        
        return backup_path
    
    def _cleanup_old_backups(self):
        """Keep only the last N backups"""
        backups = []
        for f in os.listdir(config.BACKUP_DIR):
            if f.startswith("accubooks_backup_") and f.endswith(".db"):
                path = os.path.join(config.BACKUP_DIR, f)
                backups.append((path, os.path.getmtime(path)))
        
        # Sort by modification time, newest first
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old backups
        for path, _ in backups[config.DB_BACKUP_COUNT:]:
            try:
                os.remove(path)
            except:
                pass
    
    def get_entry_count(self):
        """Get total number of transactions (for license check)"""
        result = self.execute("SELECT COUNT(*) FROM transactions")
        return result[0][0] if result else 0
    
    def get_setting(self, key, default=None):
        """Get a setting value"""
        result = self.execute("SELECT value FROM settings WHERE key = ?", (key,))
        return result[0][0] if result else default
    
    def set_setting(self, key, value):
        """Set a setting value"""
        self.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, value)
        )


# Singleton accessor
def get_db():
    return DatabaseManager()
