"""
Account Service - Chart of Accounts Management
"""
from datetime import datetime
from typing import List, Optional, Dict, Tuple


class AccountService:
    """Manage Chart of Accounts"""
    
    def __init__(self, db):
        self.db = db
    
    def get_all_accounts(self, include_inactive: bool = False) -> List[Dict]:
        """Get all accounts"""
        query = "SELECT * FROM accounts"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY code"
        
        results = self.db.execute(query)
        return [dict(row) for row in results]
    
    def get_accounts_by_type(self, acc_type: str) -> List[Dict]:
        """Get accounts filtered by type"""
        results = self.db.execute(
            "SELECT * FROM accounts WHERE type = ? AND is_active = 1 ORDER BY code",
            (acc_type,)
        )
        return [dict(row) for row in results]
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict]:
        """Get single account by ID"""
        results = self.db.execute(
            "SELECT * FROM accounts WHERE id = ?",
            (account_id,)
        )
        return dict(results[0]) if results else None
    
    def get_account_by_code(self, code: str) -> Optional[Dict]:
        """Get single account by code"""
        results = self.db.execute(
            "SELECT * FROM accounts WHERE code = ?",
            (code,)
        )
        return dict(results[0]) if results else None
    
    def create_account(self, code: str, name: str, acc_type: str, 
                       sub_type: str = None, parent_id: int = None,
                       opening_balance: float = 0, gst_applicable: bool = False,
                       hsn_code: str = None) -> Tuple[bool, str, int]:
        """
        Create a new account.
        Returns: (success, message, account_id)
        """
        # Validate code uniqueness
        existing = self.get_account_by_code(code)
        if existing:
            return False, f"Account code '{code}' already exists", 0
        
        # Validate type
        valid_types = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE']
        if acc_type not in valid_types:
            return False, f"Invalid account type. Must be one of: {', '.join(valid_types)}", 0
        
        try:
            account_id = self.db.insert("""
                INSERT INTO accounts (code, name, type, sub_type, parent_id, 
                                      opening_balance, gst_applicable, hsn_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, acc_type, sub_type, parent_id, 
                  opening_balance, 1 if gst_applicable else 0, hsn_code))
            
            return True, "Account created successfully", account_id
        except Exception as e:
            return False, str(e), 0
    
    def update_account(self, account_id: int, **kwargs) -> Tuple[bool, str]:
        """Update account details"""
        account = self.get_account_by_id(account_id)
        if not account:
            return False, "Account not found"
        
        if account['is_system']:
            # Allow only name change for system accounts
            allowed = ['name']
            kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        
        # Validate code uniqueness if changing
        if 'code' in kwargs:
            existing = self.get_account_by_code(kwargs['code'])
            if existing and existing['id'] != account_id:
                return False, f"Account code '{kwargs['code']}' already exists"
        
        if not kwargs:
            return True, "No changes made"
        
        # Build update query
        set_clause = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [datetime.now().isoformat(), account_id]
        
        try:
            self.db.execute(
                f"UPDATE accounts SET {set_clause}, updated_at = ? WHERE id = ?",
                values
            )
            return True, "Account updated successfully"
        except Exception as e:
            return False, str(e)
    
    def deactivate_account(self, account_id: int) -> Tuple[bool, str]:
        """Soft delete (deactivate) an account"""
        account = self.get_account_by_id(account_id)
        if not account:
            return False, "Account not found"
        
        if account['is_system']:
            return False, "Cannot deactivate system accounts"
        
        # Check if account has transactions
        result = self.db.execute(
            "SELECT COUNT(*) FROM transaction_lines WHERE account_id = ?",
            (account_id,)
        )
        if result[0][0] > 0:
            return False, "Cannot deactivate account with transactions. Make it inactive instead."
        
        self.db.execute(
            "UPDATE accounts SET is_active = 0, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), account_id)
        )
        return True, "Account deactivated"
    
    def get_account_balance(self, account_id: int, as_of_date: str = None) -> float:
        """Calculate current balance of an account"""
        account = self.get_account_by_id(account_id)
        if not account:
            return 0.0
        
        query = """
            SELECT COALESCE(SUM(debit), 0) as total_debit, 
                   COALESCE(SUM(credit), 0) as total_credit
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE tl.account_id = ? AND t.is_posted = 1
        """
        params = [account_id]
        
        if as_of_date:
            query += " AND t.date <= ?"
            params.append(as_of_date)
        
        result = self.db.execute(query, params)
        if not result:
            return account['opening_balance']
        
        total_debit = result[0]['total_debit'] or 0
        total_credit = result[0]['total_credit'] or 0
        
        # Calculate balance based on account type
        # Assets & Expenses: Debit increases balance
        # Liabilities, Equity, Income: Credit increases balance
        if account['type'] in ['ASSET', 'EXPENSE']:
            balance = account['opening_balance'] + total_debit - total_credit
        else:
            balance = account['opening_balance'] + total_credit - total_debit
        
        return balance
    
    def get_ledger(self, account_id: int, start_date: str = None, 
                   end_date: str = None) -> List[Dict]:
        """Get ledger entries for an account"""
        query = """
            SELECT t.id as transaction_id, t.voucher_number, t.voucher_type,
                   t.date, t.narration, tl.debit, tl.credit, tl.particulars
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE tl.account_id = ? AND t.is_posted = 1
        """
        params = [account_id]
        
        if start_date:
            query += " AND t.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND t.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY t.date, t.id"
        
        results = self.db.execute(query, params)
        
        # Calculate running balance
        account = self.get_account_by_id(account_id)
        running_balance = account['opening_balance'] if account else 0
        
        ledger = []
        for row in results:
            entry = dict(row)
            if account['type'] in ['ASSET', 'EXPENSE']:
                running_balance += (entry['debit'] or 0) - (entry['credit'] or 0)
            else:
                running_balance += (entry['credit'] or 0) - (entry['debit'] or 0)
            entry['balance'] = running_balance
            ledger.append(entry)
        
        return ledger
    
    def search_accounts(self, search_term: str) -> List[Dict]:
        """Search accounts by name or code"""
        search_pattern = f"%{search_term}%"
        results = self.db.execute("""
            SELECT * FROM accounts 
            WHERE (name LIKE ? OR code LIKE ?) AND is_active = 1
            ORDER BY code
        """, (search_pattern, search_pattern))
        return [dict(row) for row in results]
    
    def get_account_tree(self) -> List[Dict]:
        """Get hierarchical account tree"""
        accounts = self.get_all_accounts()
        
        # Build parent-child relationships
        account_map = {a['id']: a for a in accounts}
        root_accounts = []
        
        for account in accounts:
            account['children'] = []
            parent_id = account['parent_id']
            
            if parent_id and parent_id in account_map:
                account_map[parent_id]['children'].append(account)
            else:
                root_accounts.append(account)
        
        return root_accounts
