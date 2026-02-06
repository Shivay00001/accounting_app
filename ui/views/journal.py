"""
Journal Entry View
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from ui.styles import COLORS, FONTS, SPACING, ICONS
from ui.components import DataTable, FormField
from core.account_service import AccountService
from core.transaction_service import TransactionService


class JournalView(ttk.Frame):
    """Journal Entry view for creating vouchers"""
    
    def __init__(self, parent, db, license_manager):
        super().__init__(parent)
        
        self.db = db
        self.license_manager = license_manager
        self.account_service = AccountService(db)
        self.transaction_service = TransactionService(db, license_manager)
        
        self._create_widgets()
        self._load_accounts()
        self._load_recent_entries()
    
    def _create_widgets(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['lg'])
        
        title = ttk.Label(
            header,
            text=f"{ICONS['journal']} Journal Entry",
            font=FONTS['heading']
        )
        title.pack(side=tk.LEFT)
        
        # License check warning
        can_create, msg = self.license_manager.can_create_entry()
        if not can_create:
            warning = ttk.Label(
                header,
                text=f"⚠️ {msg}",
                font=FONTS['body'],
                foreground=COLORS['danger']
            )
            warning.pack(side=tk.RIGHT)
        
        # Main content - split into entry form and recent entries
        content = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING['xl'], pady=SPACING['md'])
        
        # Left: Entry Form
        form_frame = ttk.LabelFrame(content, text="New Entry", padding=SPACING['md'])
        content.add(form_frame, weight=1)
        
        # Voucher type
        type_frame = ttk.Frame(form_frame)
        type_frame.pack(fill=tk.X, pady=SPACING['xs'])
        
        ttk.Label(type_frame, text="Voucher Type:", font=FONTS['body']).pack(side=tk.LEFT)
        self.voucher_type = ttk.Combobox(
            type_frame,
            values=['JOURNAL', 'PAYMENT', 'RECEIPT', 'CONTRA', 'PURCHASE', 'SALES'],
            state='readonly',
            width=15
        )
        self.voucher_type.set('JOURNAL')
        self.voucher_type.pack(side=tk.LEFT, padx=SPACING['md'])
        
        # Date
        ttk.Label(type_frame, text="Date:", font=FONTS['body']).pack(side=tk.LEFT, padx=(SPACING['lg'], 0))
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.date_entry = ttk.Entry(type_frame, textvariable=self.date_var, width=12)
        self.date_entry.pack(side=tk.LEFT, padx=SPACING['xs'])
        
        # Reference
        ttk.Label(type_frame, text="Ref:", font=FONTS['body']).pack(side=tk.LEFT, padx=(SPACING['lg'], 0))
        self.ref_var = tk.StringVar()
        self.ref_entry = ttk.Entry(type_frame, textvariable=self.ref_var, width=15)
        self.ref_entry.pack(side=tk.LEFT, padx=SPACING['xs'])
        
        # Entry lines
        lines_frame = ttk.LabelFrame(form_frame, text="Entry Lines", padding=SPACING['sm'])
        lines_frame.pack(fill=tk.BOTH, expand=True, pady=SPACING['md'])
        
        # Lines header
        lines_header = ttk.Frame(lines_frame)
        lines_header.pack(fill=tk.X)
        
        ttk.Label(lines_header, text="Account", width=30).pack(side=tk.LEFT, padx=2)
        ttk.Label(lines_header, text="Debit (₹)", width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(lines_header, text="Credit (₹)", width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(lines_header, text="Particulars", width=20).pack(side=tk.LEFT, padx=2)
        
        # Lines container (scrollable)
        lines_canvas = tk.Canvas(lines_frame, height=200)
        lines_scrollbar = ttk.Scrollbar(lines_frame, orient="vertical", command=lines_canvas.yview)
        self.lines_container = ttk.Frame(lines_canvas)
        
        lines_canvas.configure(yscrollcommand=lines_scrollbar.set)
        lines_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lines_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_frame = lines_canvas.create_window((0, 0), window=self.lines_container, anchor="nw")
        
        self.lines_container.bind("<Configure>", lambda e: lines_canvas.configure(scrollregion=lines_canvas.bbox("all")))
        lines_canvas.bind("<Configure>", lambda e: lines_canvas.itemconfig(canvas_frame, width=e.width))
        
        self.entry_lines = []
        for _ in range(5):  # Start with 5 lines
            self._add_entry_line()
        
        # Add more lines button
        add_line_btn = ttk.Button(form_frame, text="+ Add More Lines", command=self._add_entry_line)
        add_line_btn.pack(pady=SPACING['xs'])
        
        # Narration
        narration_frame = ttk.Frame(form_frame)
        narration_frame.pack(fill=tk.X, pady=SPACING['xs'])
        
        ttk.Label(narration_frame, text="Narration:", font=FONTS['body']).pack(side=tk.LEFT)
        self.narration_var = tk.StringVar()
        self.narration_entry = ttk.Entry(narration_frame, textvariable=self.narration_var, width=60)
        self.narration_entry.pack(side=tk.LEFT, padx=SPACING['md'], fill=tk.X, expand=True)
        
        # Totals
        totals_frame = ttk.Frame(form_frame)
        totals_frame.pack(fill=tk.X, pady=SPACING['md'])
        
        ttk.Label(totals_frame, text="Total Debit:", font=FONTS['body_small']).pack(side=tk.LEFT)
        self.total_debit_var = tk.StringVar(value="₹ 0.00")
        ttk.Label(totals_frame, textvariable=self.total_debit_var, font=FONTS['body'], 
                  foreground=COLORS['debit']).pack(side=tk.LEFT, padx=SPACING['md'])
        
        ttk.Label(totals_frame, text="Total Credit:", font=FONTS['body_small']).pack(side=tk.LEFT, padx=(SPACING['lg'], 0))
        self.total_credit_var = tk.StringVar(value="₹ 0.00")
        ttk.Label(totals_frame, textvariable=self.total_credit_var, font=FONTS['body'],
                  foreground=COLORS['credit']).pack(side=tk.LEFT, padx=SPACING['md'])
        
        self.balance_label = ttk.Label(totals_frame, text="", font=FONTS['body'])
        self.balance_label.pack(side=tk.RIGHT)
        
        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.pack(fill=tk.X, pady=SPACING['md'])
        
        ttk.Button(btn_frame, text="Clear", command=self._clear_form).pack(side=tk.LEFT, padx=SPACING['xs'])
        ttk.Button(btn_frame, text="Save Entry", command=self._save_entry).pack(side=tk.RIGHT)
        
        # Right: Recent Entries
        recent_frame = ttk.LabelFrame(content, text="Recent Entries", padding=SPACING['md'])
        content.add(recent_frame, weight=1)
        
        columns = [
            {'key': 'date', 'label': 'Date', 'width': 80},
            {'key': 'voucher_number', 'label': 'Voucher #', 'width': 100},
            {'key': 'voucher_type', 'label': 'Type', 'width': 70},
            {'key': 'narration', 'label': 'Narration', 'width': 200},
            {'key': 'total_amount', 'label': 'Amount', 'width': 80, 'anchor': 'e'},
        ]
        
        self.recent_table = DataTable(recent_frame, columns, height=15)
        self.recent_table.pack(fill=tk.BOTH, expand=True)
    
    def _add_entry_line(self):
        """Add a new entry line"""
        line_frame = ttk.Frame(self.lines_container)
        line_frame.pack(fill=tk.X, pady=2)
        
        # Account combobox
        account_var = tk.StringVar()
        account_combo = ttk.Combobox(line_frame, textvariable=account_var, width=28)
        account_combo.pack(side=tk.LEFT, padx=2)
        
        # Debit entry
        debit_var = tk.StringVar()
        debit_entry = ttk.Entry(line_frame, textvariable=debit_var, width=12)
        debit_entry.pack(side=tk.LEFT, padx=2)
        debit_var.trace_add('write', lambda *args: self._update_totals())
        
        # Credit entry
        credit_var = tk.StringVar()
        credit_entry = ttk.Entry(line_frame, textvariable=credit_var, width=12)
        credit_entry.pack(side=tk.LEFT, padx=2)
        credit_var.trace_add('write', lambda *args: self._update_totals())
        
        # Particulars
        particulars_var = tk.StringVar()
        particulars_entry = ttk.Entry(line_frame, textvariable=particulars_var, width=20)
        particulars_entry.pack(side=tk.LEFT, padx=2)
        
        self.entry_lines.append({
            'frame': line_frame,
            'account': account_combo,
            'account_var': account_var,
            'debit': debit_var,
            'credit': credit_var,
            'particulars': particulars_var
        })
    
    def _load_accounts(self):
        """Load accounts for comboboxes"""
        accounts = self.account_service.get_all_accounts()
        account_values = [f"{acc['code']} - {acc['name']}" for acc in accounts]
        self.accounts_map = {f"{acc['code']} - {acc['name']}": acc['id'] for acc in accounts}
        
        for line in self.entry_lines:
            line['account']['values'] = account_values
    
    def _load_recent_entries(self):
        """Load recent entries"""
        recent = self.transaction_service.get_transactions(limit=20)
        for txn in recent:
            txn['total_amount'] = f"₹ {txn['total_amount']:,.2f}"
        self.recent_table.load_data(recent)
    
    def _update_totals(self):
        """Update debit/credit totals"""
        total_debit = 0
        total_credit = 0
        
        for line in self.entry_lines:
            try:
                debit = float(line['debit'].get() or 0)
                total_debit += debit
            except ValueError:
                pass
            
            try:
                credit = float(line['credit'].get() or 0)
                total_credit += credit
            except ValueError:
                pass
        
        self.total_debit_var.set(f"₹ {total_debit:,.2f}")
        self.total_credit_var.set(f"₹ {total_credit:,.2f}")
        
        diff = total_debit - total_credit
        if abs(diff) < 0.01:
            self.balance_label.configure(text="✓ Balanced", foreground=COLORS['success'])
        else:
            self.balance_label.configure(text=f"Difference: ₹ {abs(diff):,.2f}", foreground=COLORS['danger'])
    
    def _clear_form(self):
        """Clear the entry form"""
        self.voucher_type.set('JOURNAL')
        self.date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.ref_var.set('')
        self.narration_var.set('')
        
        for line in self.entry_lines:
            line['account_var'].set('')
            line['debit'].set('')
            line['credit'].set('')
            line['particulars'].set('')
        
        self._update_totals()
    
    def _save_entry(self):
        """Save the journal entry"""
        # Check license
        can_create, msg = self.license_manager.can_create_entry()
        if not can_create:
            messagebox.showerror("License Limit", msg)
            return
        
        # Validate date
        date = self.date_var.get()
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return
        
        # Collect lines
        lines = []
        for line in self.entry_lines:
            account_str = line['account_var'].get()
            if not account_str:
                continue
            
            account_id = self.accounts_map.get(account_str)
            if not account_id:
                messagebox.showerror("Error", f"Invalid account: {account_str}")
                return
            
            try:
                debit = float(line['debit'].get() or 0)
                credit = float(line['credit'].get() or 0)
            except ValueError:
                messagebox.showerror("Error", "Invalid amount in entry line")
                return
            
            if debit > 0 or credit > 0:
                lines.append({
                    'account_id': account_id,
                    'debit': debit,
                    'credit': credit,
                    'particulars': line['particulars'].get()
                })
        
        if len(lines) < 2:
            messagebox.showerror("Error", "Journal entry must have at least 2 lines")
            return
        
        # Save
        success, message, txn_id = self.transaction_service.create_journal_entry(
            date=date,
            narration=self.narration_var.get(),
            lines=lines,
            voucher_type=self.voucher_type.get(),
            reference=self.ref_var.get() or None
        )
        
        if success:
            messagebox.showinfo("Success", message)
            self._clear_form()
            self._load_recent_entries()
        else:
            messagebox.showerror("Error", message)
