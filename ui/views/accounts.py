"""
Chart of Accounts View
"""
import tkinter as tk
from tkinter import ttk, messagebox

from ui.styles import COLORS, FONTS, SPACING, ICONS
from ui.components import DataTable, SearchBar, Toolbar, FormField, ConfirmDialog
from core.account_service import AccountService


class AccountsView(ttk.Frame):
    """Chart of Accounts management view"""
    
    def __init__(self, parent, db, license_manager):
        super().__init__(parent)
        
        self.db = db
        self.license_manager = license_manager
        self.account_service = AccountService(db)
        
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['lg'])
        
        title = ttk.Label(
            header,
            text=f"{ICONS['accounts']} Chart of Accounts",
            font=FONTS['heading']
        )
        title.pack(side=tk.LEFT)
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['sm'])
        
        # Add button
        add_btn = ttk.Button(
            toolbar,
            text=f"{ICONS['add']} Add Account",
            command=self._show_add_dialog
        )
        add_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        # Edit button
        edit_btn = ttk.Button(
            toolbar,
            text=f"{ICONS['edit']} Edit",
            command=self._show_edit_dialog
        )
        edit_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        # Delete button
        delete_btn = ttk.Button(
            toolbar,
            text=f"{ICONS['delete']} Deactivate",
            command=self._deactivate_account
        )
        delete_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        # Search
        self.search_bar = SearchBar(toolbar, placeholder="Search accounts...", on_search=self._search)
        self.search_bar.pack(side=tk.RIGHT)
        
        # Filter by type
        ttk.Label(toolbar, text="Filter:").pack(side=tk.RIGHT, padx=(SPACING['md'], SPACING['xs']))
        self.type_filter = ttk.Combobox(
            toolbar,
            values=['All', 'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE'],
            state='readonly',
            width=12
        )
        self.type_filter.set('All')
        self.type_filter.pack(side=tk.RIGHT, padx=(0, SPACING['md']))
        self.type_filter.bind('<<ComboboxSelected>>', lambda e: self._load_data())
        
        # Accounts table
        columns = [
            {'key': 'code', 'label': 'Code', 'width': 80},
            {'key': 'name', 'label': 'Account Name', 'width': 250},
            {'key': 'type', 'label': 'Type', 'width': 100},
            {'key': 'sub_type', 'label': 'Sub Type', 'width': 100},
            {'key': 'opening_balance', 'label': 'Opening Bal', 'width': 100, 'anchor': 'e'},
            {'key': 'balance', 'label': 'Current Bal', 'width': 120, 'anchor': 'e'},
            {'key': 'gst_applicable', 'label': 'GST', 'width': 60, 'anchor': 'center'},
        ]
        
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['xl'], pady=SPACING['md'])
        
        self.accounts_table = DataTable(
            table_frame,
            columns,
            height=20,
            on_double_click=self._show_ledger
        )
        self.accounts_table.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=SPACING['xl'], pady=SPACING['sm'])
        
        self.count_label = ttk.Label(status_frame, text="0 accounts", font=FONTS['body_small'])
        self.count_label.pack(side=tk.LEFT)
        
        ttk.Label(
            status_frame,
            text="Double-click to view ledger",
            font=FONTS['body_small'],
            foreground=COLORS['text_muted']
        ).pack(side=tk.RIGHT)
    
    def _load_data(self):
        """Load accounts data"""
        filter_type = self.type_filter.get()
        
        if filter_type == 'All':
            accounts = self.account_service.get_all_accounts()
        else:
            accounts = self.account_service.get_accounts_by_type(filter_type)
        
        # Calculate balances
        for acc in accounts:
            acc['balance'] = f"₹ {self.account_service.get_account_balance(acc['id']):,.2f}"
            acc['opening_balance'] = f"₹ {acc['opening_balance']:,.2f}"
            acc['gst_applicable'] = '✓' if acc['gst_applicable'] else ''
        
        self.accounts_table.load_data(accounts)
        self.count_label.configure(text=f"{len(accounts)} accounts")
    
    def _search(self, term: str):
        """Search accounts"""
        if not term:
            self._load_data()
            return
        
        accounts = self.account_service.search_accounts(term)
        for acc in accounts:
            acc['balance'] = f"₹ {self.account_service.get_account_balance(acc['id']):,.2f}"
            acc['opening_balance'] = f"₹ {acc['opening_balance']:,.2f}"
            acc['gst_applicable'] = '✓' if acc['gst_applicable'] else ''
        
        self.accounts_table.load_data(accounts)
        self.count_label.configure(text=f"{len(accounts)} accounts found")
    
    def _show_add_dialog(self):
        """Show dialog to add new account"""
        dialog = AccountDialog(self, self.account_service, mode='add')
        self.wait_window(dialog)
        self._load_data()
    
    def _show_edit_dialog(self):
        """Show dialog to edit selected account"""
        selected = self.accounts_table.get_selected()
        if not selected:
            messagebox.showwarning("Select Account", "Please select an account to edit")
            return
        
        dialog = AccountDialog(self, self.account_service, mode='edit', account=selected)
        self.wait_window(dialog)
        self._load_data()
    
    def _deactivate_account(self):
        """Deactivate selected account"""
        selected = self.accounts_table.get_selected()
        if not selected:
            messagebox.showwarning("Select Account", "Please select an account to deactivate")
            return
        
        if not ConfirmDialog.ask("Confirm", f"Deactivate account '{selected['name']}'?"):
            return
        
        success, message = self.account_service.deactivate_account(selected['id'])
        if success:
            messagebox.showinfo("Success", message)
            self._load_data()
        else:
            messagebox.showerror("Error", message)
    
    def _show_ledger(self, account):
        """Show ledger for selected account"""
        from ui.views.ledger import LedgerDialog
        dialog = LedgerDialog(self, self.db, account)
        self.wait_window(dialog)


class AccountDialog(tk.Toplevel):
    """Dialog for adding/editing accounts"""
    
    def __init__(self, parent, account_service, mode='add', account=None):
        super().__init__(parent)
        
        self.account_service = account_service
        self.mode = mode
        self.account = account
        
        self.title("Add Account" if mode == 'add' else "Edit Account")
        self.geometry("500x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        
        if mode == 'edit' and account:
            self._load_account_data()
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=SPACING['lg'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Code
        self.code_field = FormField(main_frame, "Account Code", required=True, width=20)
        self.code_field.pack(fill=tk.X, pady=SPACING['xs'])
        
        # Name
        self.name_field = FormField(main_frame, "Account Name", required=True)
        self.name_field.pack(fill=tk.X, pady=SPACING['xs'])
        
        # Type
        self.type_field = FormField(
            main_frame, "Account Type", 'combobox', 
            values=['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE'],
            required=True
        )
        self.type_field.pack(fill=tk.X, pady=SPACING['xs'])
        
        # Sub Type
        self.subtype_field = FormField(
            main_frame, "Sub Type", 'combobox',
            values=['CURRENT', 'FIXED', 'LONG_TERM', '']
        )
        self.subtype_field.pack(fill=tk.X, pady=SPACING['xs'])
        
        # Opening Balance
        self.balance_field = FormField(main_frame, "Opening Balance", width=20)
        self.balance_field.pack(fill=tk.X, pady=SPACING['xs'])
        self.balance_field.set("0")
        
        # GST Applicable
        self.gst_var = tk.BooleanVar()
        gst_check = ttk.Checkbutton(
            main_frame, 
            text="GST Applicable",
            variable=self.gst_var
        )
        gst_check.pack(anchor='w', pady=SPACING['xs'])
        
        # HSN Code
        self.hsn_field = FormField(main_frame, "HSN/SAC Code", width=20)
        self.hsn_field.pack(fill=tk.X, pady=SPACING['xs'])
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=SPACING['lg'])
        
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=SPACING['xs'])
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT)
    
    def _load_account_data(self):
        """Load existing account data for editing"""
        self.code_field.set(self.account['code'])
        self.name_field.set(self.account['name'])
        self.type_field.set(self.account['type'])
        self.subtype_field.set(self.account.get('sub_type', '') or '')
        self.balance_field.set(str(self.account.get('opening_balance', 0)).replace('₹ ', '').replace(',', ''))
        self.gst_var.set(bool(self.account.get('gst_applicable')))
        self.hsn_field.set(self.account.get('hsn_code', '') or '')
    
    def _save(self):
        """Save account"""
        code = self.code_field.get().strip()
        name = self.name_field.get().strip()
        acc_type = self.type_field.get()
        sub_type = self.subtype_field.get() or None
        
        try:
            opening_balance = float(self.balance_field.get().replace(',', '') or 0)
        except ValueError:
            messagebox.showerror("Error", "Invalid opening balance")
            return
        
        gst_applicable = self.gst_var.get()
        hsn_code = self.hsn_field.get().strip() or None
        
        if not code or not name or not acc_type:
            messagebox.showerror("Error", "Please fill all required fields")
            return
        
        if self.mode == 'add':
            success, message, _ = self.account_service.create_account(
                code, name, acc_type, sub_type, None, opening_balance, gst_applicable, hsn_code
            )
        else:
            success, message = self.account_service.update_account(
                self.account['id'],
                code=code,
                name=name,
                type=acc_type,
                sub_type=sub_type,
                opening_balance=opening_balance,
                gst_applicable=1 if gst_applicable else 0,
                hsn_code=hsn_code
            )
        
        if success:
            messagebox.showinfo("Success", message)
            self.destroy()
        else:
            messagebox.showerror("Error", message)
