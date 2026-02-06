"""
Transaction Service - Journal Entries and Vouchers
"""
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class TransactionService:
    """Manage Journal Entries and Vouchers"""
    
    VOUCHER_TYPES = ['JOURNAL', 'PAYMENT', 'RECEIPT', 'CONTRA', 'PURCHASE', 'SALES']
    
    def __init__(self, db, license_manager):
        self.db = db
        self.license_manager = license_manager
    
    def get_next_voucher_number(self, voucher_type: str) -> str:
        """Generate next voucher number"""
        prefix_map = {
            'JOURNAL': 'JV',
            'PAYMENT': 'PAY',
            'RECEIPT': 'REC',
            'CONTRA': 'CON',
            'PURCHASE': 'PUR',
            'SALES': 'SAL'
        }
        
        prefix = prefix_map.get(voucher_type, 'VCH')
        year = datetime.now().strftime("%y")
        
        # Get last voucher number for this type
        result = self.db.execute("""
            SELECT voucher_number FROM transactions 
            WHERE voucher_type = ? 
            ORDER BY id DESC LIMIT 1
        """, (voucher_type,))
        
        if result:
            last_num = result[0]['voucher_number']
            # Extract number part
            try:
                num_part = int(last_num.split('-')[-1])
                next_num = num_part + 1
            except:
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}-{year}-{next_num:05d}"
    
    def create_journal_entry(self, date: str, narration: str, 
                             lines: List[Dict], voucher_type: str = 'JOURNAL',
                             reference: str = None) -> Tuple[bool, str, int]:
        """
        Create a journal entry (voucher).
        
        lines: [{'account_id': int, 'debit': float, 'credit': float, 'particulars': str}, ...]
        
        Returns: (success, message, transaction_id)
        """
        # Check license
        can_create, msg = self.license_manager.can_create_entry()
        if not can_create:
            return False, msg, 0
        
        # Validate voucher type
        if voucher_type not in self.VOUCHER_TYPES:
            return False, f"Invalid voucher type. Must be one of: {', '.join(self.VOUCHER_TYPES)}", 0
        
        # Validate lines
        if len(lines) < 2:
            return False, "Journal entry must have at least 2 lines (one debit, one credit)", 0
        
        # Validate debit = credit
        total_debit = sum(line.get('debit', 0) or 0 for line in lines)
        total_credit = sum(line.get('credit', 0) or 0 for line in lines)
        
        if abs(total_debit - total_credit) > 0.01:  # Allow small rounding difference
            return False, f"Debits (₹{total_debit:,.2f}) must equal Credits (₹{total_credit:,.2f})", 0
        
        # Validate accounts exist
        for line in lines:
            result = self.db.execute("SELECT id FROM accounts WHERE id = ?", (line['account_id'],))
            if not result:
                return False, f"Account ID {line['account_id']} not found", 0
        
        try:
            voucher_number = self.get_next_voucher_number(voucher_type)
            
            # Create transaction header
            transaction_id = self.db.insert("""
                INSERT INTO transactions (voucher_number, voucher_type, date, narration, reference, total_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (voucher_number, voucher_type, date, narration, reference, total_debit))
            
            # Create transaction lines
            for line in lines:
                self.db.execute("""
                    INSERT INTO transaction_lines (transaction_id, account_id, debit, credit, particulars)
                    VALUES (?, ?, ?, ?, ?)
                """, (transaction_id, line['account_id'], 
                      line.get('debit', 0) or 0, 
                      line.get('credit', 0) or 0,
                      line.get('particulars', '')))
            
            return True, f"Voucher {voucher_number} created successfully", transaction_id
            
        except Exception as e:
            return False, str(e), 0
    
    def get_transaction(self, transaction_id: int) -> Optional[Dict]:
        """Get transaction with all its lines"""
        # Get header
        result = self.db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        )
        if not result:
            return None
        
        transaction = dict(result[0])
        
        # Get lines with account info
        lines = self.db.execute("""
            SELECT tl.*, a.name as account_name, a.code as account_code
            FROM transaction_lines tl
            JOIN accounts a ON tl.account_id = a.id
            WHERE tl.transaction_id = ?
        """, (transaction_id,))
        
        transaction['lines'] = [dict(line) for line in lines]
        return transaction
    
    def get_transactions(self, start_date: str = None, end_date: str = None,
                         voucher_type: str = None, limit: int = 100) -> List[Dict]:
        """Get list of transactions with filters"""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        if voucher_type:
            query += " AND voucher_type = ?"
            params.append(voucher_type)
        
        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)
        
        results = self.db.execute(query, params)
        return [dict(row) for row in results]
    
    def update_transaction(self, transaction_id: int, date: str = None,
                          narration: str = None, reference: str = None,
                          lines: List[Dict] = None) -> Tuple[bool, str]:
        """Update an existing transaction"""
        transaction = self.get_transaction(transaction_id)
        if not transaction:
            return False, "Transaction not found"
        
        try:
            # Update header fields if provided
            update_fields = []
            update_values = []
            
            if date is not None:
                update_fields.append("date = ?")
                update_values.append(date)
            
            if narration is not None:
                update_fields.append("narration = ?")
                update_values.append(narration)
            
            if reference is not None:
                update_fields.append("reference = ?")
                update_values.append(reference)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())
                update_values.append(transaction_id)
                
                self.db.execute(
                    f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ?",
                    update_values
                )
            
            # Update lines if provided
            if lines is not None:
                # Validate debit = credit
                total_debit = sum(line.get('debit', 0) or 0 for line in lines)
                total_credit = sum(line.get('credit', 0) or 0 for line in lines)
                
                if abs(total_debit - total_credit) > 0.01:
                    return False, f"Debits must equal Credits"
                
                # Delete existing lines
                self.db.execute(
                    "DELETE FROM transaction_lines WHERE transaction_id = ?",
                    (transaction_id,)
                )
                
                # Insert new lines
                for line in lines:
                    self.db.execute("""
                        INSERT INTO transaction_lines (transaction_id, account_id, debit, credit, particulars)
                        VALUES (?, ?, ?, ?, ?)
                    """, (transaction_id, line['account_id'],
                          line.get('debit', 0) or 0,
                          line.get('credit', 0) or 0,
                          line.get('particulars', '')))
                
                # Update total amount
                self.db.execute(
                    "UPDATE transactions SET total_amount = ?, updated_at = ? WHERE id = ?",
                    (total_debit, datetime.now().isoformat(), transaction_id)
                )
            
            return True, "Transaction updated successfully"
            
        except Exception as e:
            return False, str(e)
    
    def delete_transaction(self, transaction_id: int) -> Tuple[bool, str]:
        """Delete a transaction (soft delete by unposting)"""
        transaction = self.get_transaction(transaction_id)
        if not transaction:
            return False, "Transaction not found"
        
        try:
            # Soft delete - just unpost
            self.db.execute(
                "UPDATE transactions SET is_posted = 0, updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), transaction_id)
            )
            return True, "Transaction deleted"
        except Exception as e:
            return False, str(e)
    
    def search_transactions(self, search_term: str) -> List[Dict]:
        """Search transactions by voucher number or narration"""
        search_pattern = f"%{search_term}%"
        results = self.db.execute("""
            SELECT * FROM transactions 
            WHERE (voucher_number LIKE ? OR narration LIKE ? OR reference LIKE ?)
            AND is_posted = 1
            ORDER BY date DESC, id DESC
            LIMIT 50
        """, (search_pattern, search_pattern, search_pattern))
        return [dict(row) for row in results]
    
    def get_day_book(self, date: str) -> List[Dict]:
        """Get all transactions for a specific date"""
        results = self.db.execute("""
            SELECT t.*, 
                   GROUP_CONCAT(a.name, ', ') as accounts
            FROM transactions t
            LEFT JOIN transaction_lines tl ON t.id = tl.transaction_id
            LEFT JOIN accounts a ON tl.account_id = a.id
            WHERE t.date = ? AND t.is_posted = 1
            GROUP BY t.id
            ORDER BY t.id
        """, (date,))
        return [dict(row) for row in results]
    
    def get_cash_book(self, start_date: str, end_date: str) -> List[Dict]:
        """Get cash book entries (transactions involving cash accounts)"""
        # Get cash account IDs
        cash_accounts = self.db.execute(
            "SELECT id FROM accounts WHERE code LIKE '100%' OR code LIKE '1001' OR name LIKE '%Cash%'"
        )
        cash_ids = [a['id'] for a in cash_accounts]
        
        if not cash_ids:
            return []
        
        placeholders = ','.join('?' * len(cash_ids))
        results = self.db.execute(f"""
            SELECT t.date, t.voucher_number, t.narration, tl.debit, tl.credit,
                   a.name as account_name
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            JOIN accounts a ON tl.account_id = a.id
            WHERE tl.account_id IN ({placeholders})
            AND t.date >= ? AND t.date <= ? AND t.is_posted = 1
            ORDER BY t.date, t.id
        """, (*cash_ids, start_date, end_date))
        
        return [dict(row) for row in results]
    
    def get_bank_book(self, start_date: str, end_date: str) -> List[Dict]:
        """Get bank book entries"""
        # Get bank account IDs
        bank_accounts = self.db.execute(
            "SELECT id FROM accounts WHERE code LIKE '110%' OR name LIKE '%Bank%'"
        )
        bank_ids = [a['id'] for a in bank_accounts]
        
        if not bank_ids:
            return []
        
        placeholders = ','.join('?' * len(bank_ids))
        results = self.db.execute(f"""
            SELECT t.date, t.voucher_number, t.narration, tl.debit, tl.credit,
                   a.name as account_name
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            JOIN accounts a ON tl.account_id = a.id
            WHERE tl.account_id IN ({placeholders})
            AND t.date >= ? AND t.date <= ? AND t.is_posted = 1
            ORDER BY t.date, t.id
        """, (*bank_ids, start_date, end_date))
        
        return [dict(row) for row in results]
