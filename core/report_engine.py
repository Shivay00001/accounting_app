"""
Report Engine - Financial Statements Generation
"""
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from decimal import Decimal


class ReportEngine:
    """Generate financial reports: P&L, Balance Sheet, GST Summary"""
    
    def __init__(self, db):
        self.db = db
    
    def get_trial_balance(self, as_of_date: str = None) -> Dict:
        """Generate Trial Balance"""
        if not as_of_date:
            as_of_date = datetime.now().strftime("%Y-%m-%d")
        
        accounts = self.db.execute("""
            SELECT a.id, a.code, a.name, a.type, a.opening_balance,
                   COALESCE(SUM(tl.debit), 0) as total_debit,
                   COALESCE(SUM(tl.credit), 0) as total_credit
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id 
                AND t.is_posted = 1 AND t.date <= ?
            WHERE a.is_active = 1
            GROUP BY a.id
            ORDER BY a.code
        """, (as_of_date,))
        
        trial_balance = []
        total_debit = 0
        total_credit = 0
        
        for acc in accounts:
            acc = dict(acc)
            opening = acc['opening_balance'] or 0
            debits = acc['total_debit'] or 0
            credits = acc['total_credit'] or 0
            
            # Calculate closing balance based on account type
            if acc['type'] in ['ASSET', 'EXPENSE']:
                balance = opening + debits - credits
                if balance >= 0:
                    acc['debit_balance'] = balance
                    acc['credit_balance'] = 0
                    total_debit += balance
                else:
                    acc['debit_balance'] = 0
                    acc['credit_balance'] = abs(balance)
                    total_credit += abs(balance)
            else:  # LIABILITY, EQUITY, INCOME
                balance = opening + credits - debits
                if balance >= 0:
                    acc['credit_balance'] = balance
                    acc['debit_balance'] = 0
                    total_credit += balance
                else:
                    acc['credit_balance'] = 0
                    acc['debit_balance'] = abs(balance)
                    total_debit += abs(balance)
            
            if acc['debit_balance'] != 0 or acc['credit_balance'] != 0:
                trial_balance.append(acc)
        
        return {
            'as_of_date': as_of_date,
            'accounts': trial_balance,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'is_balanced': abs(total_debit - total_credit) < 0.01
        }
    
    def get_profit_and_loss(self, start_date: str, end_date: str) -> Dict:
        """Generate Profit & Loss Statement"""
        
        # Get Income accounts totals
        income_accounts = self.db.execute("""
            SELECT a.id, a.code, a.name,
                   COALESCE(SUM(tl.credit), 0) - COALESCE(SUM(tl.debit), 0) as amount
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id 
                AND t.is_posted = 1 AND t.date >= ? AND t.date <= ?
            WHERE a.type = 'INCOME' AND a.is_active = 1
            GROUP BY a.id
            HAVING amount != 0
            ORDER BY a.code
        """, (start_date, end_date))
        
        # Get Expense accounts totals
        expense_accounts = self.db.execute("""
            SELECT a.id, a.code, a.name,
                   COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as amount
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id 
                AND t.is_posted = 1 AND t.date >= ? AND t.date <= ?
            WHERE a.type = 'EXPENSE' AND a.is_active = 1
            GROUP BY a.id
            HAVING amount != 0
            ORDER BY a.code
        """, (start_date, end_date))
        
        income_list = [dict(a) for a in income_accounts]
        expense_list = [dict(a) for a in expense_accounts]
        
        total_income = sum(a['amount'] for a in income_list)
        total_expense = sum(a['amount'] for a in expense_list)
        net_profit = total_income - total_expense
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'income': income_list,
            'expenses': expense_list,
            'total_income': total_income,
            'total_expenses': total_expense,
            'net_profit': net_profit,
            'is_profit': net_profit >= 0
        }
    
    def get_balance_sheet(self, as_of_date: str = None) -> Dict:
        """Generate Balance Sheet"""
        if not as_of_date:
            as_of_date = datetime.now().strftime("%Y-%m-%d")
        
        def get_accounts_by_type(acc_type: str, is_debit_normal: bool) -> Tuple[List[Dict], float]:
            accounts = self.db.execute("""
                SELECT a.id, a.code, a.name, a.opening_balance,
                       COALESCE(SUM(tl.debit), 0) as total_debit,
                       COALESCE(SUM(tl.credit), 0) as total_credit
                FROM accounts a
                LEFT JOIN transaction_lines tl ON a.id = tl.account_id
                LEFT JOIN transactions t ON tl.transaction_id = t.id 
                    AND t.is_posted = 1 AND t.date <= ?
                WHERE a.type = ? AND a.is_active = 1
                GROUP BY a.id
                ORDER BY a.code
            """, (as_of_date, acc_type))
            
            result = []
            total = 0
            
            for acc in accounts:
                acc = dict(acc)
                opening = acc['opening_balance'] or 0
                debits = acc['total_debit'] or 0
                credits = acc['total_credit'] or 0
                
                if is_debit_normal:
                    balance = opening + debits - credits
                else:
                    balance = opening + credits - debits
                
                if abs(balance) > 0.01:
                    acc['balance'] = balance
                    result.append(acc)
                    total += balance
            
            return result, total
        
        # Assets
        assets, total_assets = get_accounts_by_type('ASSET', True)
        
        # Liabilities
        liabilities, total_liabilities = get_accounts_by_type('LIABILITY', False)
        
        # Equity
        equity, total_equity = get_accounts_by_type('EQUITY', False)
        
        # Calculate retained earnings (P&L till date)
        # For simplicity, we'll calculate from the start of financial year
        fy_start = self._get_financial_year_start(as_of_date)
        pnl = self.get_profit_and_loss(fy_start, as_of_date)
        retained_earnings = pnl['net_profit']
        
        total_equity_with_retained = total_equity + retained_earnings
        total_liabilities_and_equity = total_liabilities + total_equity_with_retained
        
        return {
            'as_of_date': as_of_date,
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'retained_earnings': retained_earnings,
            'total_liabilities_and_equity': total_liabilities_and_equity,
            'is_balanced': abs(total_assets - total_liabilities_and_equity) < 0.01
        }
    
    def _get_financial_year_start(self, date_str: str) -> str:
        """Get financial year start date (April 1st for India)"""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        fy_start_month = int(self.db.get_setting('financial_year_start', '04'))
        
        if date.month >= fy_start_month:
            fy_year = date.year
        else:
            fy_year = date.year - 1
        
        return f"{fy_year}-{fy_start_month:02d}-01"
    
    def get_gst_summary(self, start_date: str, end_date: str) -> Dict:
        """
        Generate GST Summary Report
        Shows GST collected (output) and GST paid (input)
        """
        # GST Output (Sales - credit to GST Payable)
        gst_output = self.db.execute("""
            SELECT COALESCE(SUM(tl.credit), 0) - COALESCE(SUM(tl.debit), 0) as amount
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            JOIN accounts a ON tl.account_id = a.id
            WHERE a.code = '2201' AND t.is_posted = 1
            AND t.date >= ? AND t.date <= ?
        """, (start_date, end_date))
        
        # GST Input (Purchases - debit to GST Input Credit)
        gst_input = self.db.execute("""
            SELECT COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as amount
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            JOIN accounts a ON tl.account_id = a.id
            WHERE a.code = '2202' AND t.is_posted = 1
            AND t.date >= ? AND t.date <= ?
        """, (start_date, end_date))
        
        output_gst = gst_output[0]['amount'] if gst_output else 0
        input_gst = gst_input[0]['amount'] if gst_input else 0
        net_gst = output_gst - input_gst
        
        # Get sales and purchase totals
        sales = self.db.execute("""
            SELECT COALESCE(SUM(tl.credit), 0) - COALESCE(SUM(tl.debit), 0) as amount
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            JOIN accounts a ON tl.account_id = a.id
            WHERE a.type = 'INCOME' AND t.is_posted = 1
            AND t.date >= ? AND t.date <= ?
        """, (start_date, end_date))
        
        purchases = self.db.execute("""
            SELECT COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as amount
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            JOIN accounts a ON tl.account_id = a.id
            WHERE a.code LIKE '500%' AND t.is_posted = 1
            AND t.date >= ? AND t.date <= ?
        """, (start_date, end_date))
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'total_sales': sales[0]['amount'] if sales else 0,
            'total_purchases': purchases[0]['amount'] if purchases else 0,
            'gst_collected': output_gst,
            'gst_input_credit': input_gst,
            'net_gst_payable': net_gst if net_gst > 0 else 0,
            'net_gst_refundable': abs(net_gst) if net_gst < 0 else 0
        }
    
    def get_expense_summary(self, start_date: str, end_date: str) -> Dict:
        """Get expense breakdown by category"""
        expenses = self.db.execute("""
            SELECT a.code, a.name, 
                   COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as amount
            FROM accounts a
            JOIN transaction_lines tl ON a.id = tl.account_id
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE a.type = 'EXPENSE' AND t.is_posted = 1
            AND t.date >= ? AND t.date <= ?
            GROUP BY a.id
            HAVING amount > 0
            ORDER BY amount DESC
        """, (start_date, end_date))
        
        expense_list = [dict(e) for e in expenses]
        total = sum(e['amount'] for e in expense_list)
        
        # Calculate percentages
        for exp in expense_list:
            exp['percentage'] = (exp['amount'] / total * 100) if total > 0 else 0
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'expenses': expense_list,
            'total': total
        }
    
    def get_receivables_summary(self) -> Dict:
        """Get accounts receivable summary"""
        receivables = self.db.execute("""
            SELECT a.code, a.name, a.opening_balance,
                   COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as net_movement
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id AND t.is_posted = 1
            WHERE a.code LIKE '120%' AND a.is_active = 1
            GROUP BY a.id
            ORDER BY a.code
        """)
        
        result = []
        total = 0
        
        for acc in receivables:
            acc = dict(acc)
            balance = (acc['opening_balance'] or 0) + (acc['net_movement'] or 0)
            if abs(balance) > 0.01:
                acc['balance'] = balance
                result.append(acc)
                total += balance
        
        return {'accounts': result, 'total': total}
    
    def get_payables_summary(self) -> Dict:
        """Get accounts payable summary"""
        payables = self.db.execute("""
            SELECT a.code, a.name, a.opening_balance,
                   COALESCE(SUM(tl.credit), 0) - COALESCE(SUM(tl.debit), 0) as net_movement
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id AND t.is_posted = 1
            WHERE a.code LIKE '200%' AND a.is_active = 1
            GROUP BY a.id
            ORDER BY a.code
        """)
        
        result = []
        total = 0
        
        for acc in payables:
            acc = dict(acc)
            balance = (acc['opening_balance'] or 0) + (acc['net_movement'] or 0)
            if abs(balance) > 0.01:
                acc['balance'] = balance
                result.append(acc)
                total += balance
        
        return {'accounts': result, 'total': total}
    
    def get_dashboard_summary(self) -> Dict:
        """Get summary data for dashboard"""
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        fy_start = self._get_financial_year_start(today)
        
        # Monthly P&L
        monthly_pnl = self.get_profit_and_loss(month_start, today)
        
        # YTD P&L
        ytd_pnl = self.get_profit_and_loss(fy_start, today)
        
        # Cash balance
        cash_balance = self.db.execute("""
            SELECT a.opening_balance + 
                   COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as balance
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id AND t.is_posted = 1
            WHERE a.code IN ('1001', '1002')
            GROUP BY a.id
        """)
        
        total_cash = sum(c['balance'] for c in cash_balance) if cash_balance else 0
        
        # Bank balance
        bank_balance = self.db.execute("""
            SELECT a.opening_balance + 
                   COALESCE(SUM(tl.debit), 0) - COALESCE(SUM(tl.credit), 0) as balance
            FROM accounts a
            LEFT JOIN transaction_lines tl ON a.id = tl.account_id
            LEFT JOIN transactions t ON tl.transaction_id = t.id AND t.is_posted = 1
            WHERE a.code LIKE '110%'
            GROUP BY a.id
        """)
        
        total_bank = sum(b['balance'] for b in bank_balance) if bank_balance else 0
        
        # Recent transactions count
        recent_count = self.db.execute("""
            SELECT COUNT(*) as count FROM transactions 
            WHERE date >= ? AND is_posted = 1
        """, (month_start,))
        
        receivables = self.get_receivables_summary()
        payables = self.get_payables_summary()
        
        return {
            'monthly_income': monthly_pnl['total_income'],
            'monthly_expenses': monthly_pnl['total_expenses'],
            'monthly_profit': monthly_pnl['net_profit'],
            'ytd_income': ytd_pnl['total_income'],
            'ytd_expenses': ytd_pnl['total_expenses'],
            'ytd_profit': ytd_pnl['net_profit'],
            'cash_balance': total_cash,
            'bank_balance': total_bank,
            'total_receivables': receivables['total'],
            'total_payables': payables['total'],
            'monthly_transactions': recent_count[0]['count'] if recent_count else 0,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
