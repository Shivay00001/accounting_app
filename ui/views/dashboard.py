"""
Dashboard View - Financial Overview
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False

from ui.styles import COLORS, FONTS, SPACING, ICONS
from ui.components import StatCard, DataTable
from core.report_engine import ReportEngine


class DashboardView(ttk.Frame):
    """Main dashboard with financial overview"""
    
    def __init__(self, parent, db, license_manager):
        super().__init__(parent)
        
        self.db = db
        self.license_manager = license_manager
        self.report_engine = ReportEngine(db)
        
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['lg'])
        
        title = ttk.Label(
            header,
            text=f"{ICONS['dashboard']} Dashboard",
            font=FONTS['heading']
        )
        title.pack(side=tk.LEFT)
        
        # Refresh button
        refresh_btn = ttk.Button(
            header,
            text=f"{ICONS['refresh']} Refresh",
            command=self._load_data
        )
        refresh_btn.pack(side=tk.RIGHT)
        
        # Date info
        today = datetime.now().strftime("%d %B %Y")
        date_label = ttk.Label(
            header,
            text=today,
            font=FONTS['body'],
            foreground=COLORS['text_secondary']
        )
        date_label.pack(side=tk.RIGHT, padx=SPACING['lg'])
        
        # Stats cards row 1
        stats_frame1 = ttk.Frame(self)
        stats_frame1.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['md'])
        
        self.cards = {}
        
        card_configs = [
            ('monthly_income', 'Monthly Income', ICONS['dashboard'], COLORS['success']),
            ('monthly_expenses', 'Monthly Expenses', '💸', COLORS['danger']),
            ('monthly_profit', 'Monthly Profit', '📈', COLORS['primary']),
            ('cash_balance', 'Cash Balance', '💰', COLORS['warning']),
        ]
        
        for key, title, icon, color in card_configs:
            card_frame = ttk.Frame(stats_frame1, style='Card.TFrame')
            card_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=SPACING['sm'])
            
            # Icon and title
            header_frame = ttk.Frame(card_frame)
            header_frame.pack(fill=tk.X, padx=SPACING['md'], pady=(SPACING['md'], SPACING['xs']))
            
            icon_lbl = ttk.Label(header_frame, text=icon, font=('Segoe UI Emoji', 16))
            icon_lbl.pack(side=tk.LEFT)
            
            title_lbl = ttk.Label(
                header_frame,
                text=title,
                font=FONTS['body_small'],
                foreground=COLORS['text_secondary']
            )
            title_lbl.pack(side=tk.LEFT, padx=SPACING['xs'])
            
            # Value
            value_var = tk.StringVar(value="₹ 0")
            value_lbl = ttk.Label(
                card_frame,
                textvariable=value_var,
                font=FONTS['stat_value'],
                foreground=color
            )
            value_lbl.pack(padx=SPACING['md'], pady=(0, SPACING['md']))
            
            self.cards[key] = value_var
        
        # Stats cards row 2
        stats_frame2 = ttk.Frame(self)
        stats_frame2.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['md'])
        
        card_configs2 = [
            ('bank_balance', 'Bank Balance', '🏦', COLORS['info']),
            ('total_receivables', 'Receivables', '📥', COLORS['warning']),
            ('total_payables', 'Payables', '📤', COLORS['danger']),
            ('monthly_transactions', 'This Month Txns', '📝', COLORS['secondary']),
        ]
        
        for key, title, icon, color in card_configs2:
            card_frame = ttk.Frame(stats_frame2, style='Card.TFrame')
            card_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=SPACING['sm'])
            
            header_frame = ttk.Frame(card_frame)
            header_frame.pack(fill=tk.X, padx=SPACING['md'], pady=(SPACING['md'], SPACING['xs']))
            
            icon_lbl = ttk.Label(header_frame, text=icon, font=('Segoe UI Emoji', 16))
            icon_lbl.pack(side=tk.LEFT)
            
            title_lbl = ttk.Label(
                header_frame,
                text=title,
                font=FONTS['body_small'],
                foreground=COLORS['text_secondary']
            )
            title_lbl.pack(side=tk.LEFT, padx=SPACING['xs'])
            
            value_var = tk.StringVar(value="₹ 0")
            value_lbl = ttk.Label(
                card_frame,
                textvariable=value_var,
                font=FONTS['stat_value'],
                foreground=color
            )
            value_lbl.pack(padx=SPACING['md'], pady=(0, SPACING['md']))
            
            self.cards[key] = value_var
        
        # YTD Summary
        ytd_frame = ttk.LabelFrame(self, text="Year-to-Date Summary", padding=SPACING['md'])
        ytd_frame.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['md'])
        
        ytd_cards_frame = ttk.Frame(ytd_frame)
        ytd_cards_frame.pack(fill=tk.X)
        
        ytd_configs = [
            ('ytd_income', 'YTD Income', COLORS['success']),
            ('ytd_expenses', 'YTD Expenses', COLORS['danger']),
            ('ytd_profit', 'YTD Profit/Loss', COLORS['primary']),
        ]
        
        for key, title, color in ytd_configs:
            frame = ttk.Frame(ytd_cards_frame)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=SPACING['md'])
            
            ttk.Label(frame, text=title, font=FONTS['body_small'], foreground=COLORS['text_secondary']).pack()
            
            value_var = tk.StringVar(value="₹ 0")
            ttk.Label(frame, textvariable=value_var, font=FONTS['heading'], foreground=color).pack()
            
            self.cards[key] = value_var
        
        # Recent Transactions
        recent_frame = ttk.LabelFrame(self, text="Recent Transactions", padding=SPACING['md'])
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['xl'], pady=SPACING['md'])
        
        columns = [
            {'key': 'date', 'label': 'Date', 'width': 100},
            {'key': 'voucher_number', 'label': 'Voucher #', 'width': 120},
            {'key': 'voucher_type', 'label': 'Type', 'width': 80},
            {'key': 'narration', 'label': 'Narration', 'width': 300},
            {'key': 'total_amount', 'label': 'Amount (₹)', 'width': 120, 'anchor': 'e'},
        ]
        
        self.recent_table = DataTable(recent_frame, columns, height=8)
        self.recent_table.pack(fill=tk.BOTH, expand=True)
        
        # License warning (if trial)
        status, details = self.license_manager.get_current_status()
        if status == 'TRIAL':
            warning_frame = ttk.Frame(self)
            warning_frame.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['sm'])
            
            entries = details.get('entries_used', 0)
            limit = details.get('entries_limit', 30)
            remaining = limit - entries
            
            warning_label = ttk.Label(
                warning_frame,
                text=f"⚠️ Trial Mode: {remaining} entries remaining. Purchase a license for unlimited access.",
                font=FONTS['body'],
                foreground=COLORS['warning']
            )
            warning_label.pack()
    
    def _load_data(self):
        """Load dashboard data"""
        try:
            summary = self.report_engine.get_dashboard_summary()
            
            # Update cards
            self.cards['monthly_income'].set(f"₹ {summary['monthly_income']:,.0f}")
            self.cards['monthly_expenses'].set(f"₹ {summary['monthly_expenses']:,.0f}")
            self.cards['monthly_profit'].set(f"₹ {summary['monthly_profit']:,.0f}")
            self.cards['cash_balance'].set(f"₹ {summary['cash_balance']:,.0f}")
            self.cards['bank_balance'].set(f"₹ {summary['bank_balance']:,.0f}")
            self.cards['total_receivables'].set(f"₹ {summary['total_receivables']:,.0f}")
            self.cards['total_payables'].set(f"₹ {summary['total_payables']:,.0f}")
            self.cards['monthly_transactions'].set(str(summary['monthly_transactions']))
            
            self.cards['ytd_income'].set(f"₹ {summary['ytd_income']:,.0f}")
            self.cards['ytd_expenses'].set(f"₹ {summary['ytd_expenses']:,.0f}")
            self.cards['ytd_profit'].set(f"₹ {summary['ytd_profit']:,.0f}")
            
            # Load recent transactions
            from core.transaction_service import TransactionService
            txn_service = TransactionService(self.db, self.license_manager)
            recent = txn_service.get_transactions(limit=10)
            self.recent_table.load_data(recent)
            
        except Exception as e:
            print(f"Dashboard load error: {e}")
