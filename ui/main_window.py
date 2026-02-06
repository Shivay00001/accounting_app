"""
Main Application Window
Modern dark themed window with sidebar navigation
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False
    ttkb = None

import config
from ui.styles import COLORS, FONTS, SPACING, ICONS
from database.db_manager import get_db
from core.license_manager import LicenseManager, LicenseStatus

# Import views
from ui.views.dashboard import DashboardView
from ui.views.accounts import AccountsView
from ui.views.journal import JournalView
from ui.views.expenses import ExpensesView
from ui.views.cashbook import CashBookView
from ui.views.bankbook import BankBookView
from ui.views.reports import ReportsView
from ui.views.settings import SettingsView
from ui.views.license_view import LicenseView


class MainWindow:
    """Main application window with sidebar navigation"""
    
    def __init__(self):
        self.db = get_db()
        self.license_manager = LicenseManager(self.db)
        
        # Check if app is blocked
        blocked, message = self.license_manager.is_app_blocked()
        if blocked:
            self._show_blocked_screen(message)
            return
        
        self._create_window()
        self._create_styles()
        self._create_layout()
        self._create_sidebar()
        self._create_content_area()
        self._create_status_bar()
        
        # Load default view
        self._show_view('dashboard')
        
        # Update license status
        self._update_license_status()
    
    def _show_blocked_screen(self, message):
        """Show blocked/revoked license screen"""
        if HAS_TTKBOOTSTRAP:
            root = ttkb.Window(themename="darkly")
        else:
            root = tk.Tk()
        
        root.title(f"{config.APP_NAME} - License Required")
        root.geometry("500x300")
        root.resizable(False, False)
        
        frame = ttk.Frame(root, padding=40)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Lock icon
        lock_label = ttk.Label(
            frame, 
            text="🔒",
            font=('Segoe UI Emoji', 48)
        )
        lock_label.pack(pady=(0, 20))
        
        # Message
        msg_label = ttk.Label(
            frame,
            text=message,
            font=FONTS['heading_small'],
            wraplength=400,
            justify='center'
        )
        msg_label.pack(pady=10)
        
        # Machine ID
        machine_id = self.license_manager.get_machine_id()
        id_label = ttk.Label(
            frame,
            text=f"Machine ID: {machine_id}",
            font=FONTS['monospace']
        )
        id_label.pack(pady=10)
        
        # Copy button
        def copy_id():
            root.clipboard_clear()
            root.clipboard_append(machine_id)
            messagebox.showinfo("Copied", "Machine ID copied to clipboard")
        
        copy_btn = ttk.Button(frame, text="Copy Machine ID", command=copy_id)
        copy_btn.pack(pady=10)
        
        # Contact info
        contact = ttk.Label(
            frame,
            text="Contact support to activate your license",
            font=FONTS['body_small']
        )
        contact.pack(pady=5)
        
        root.mainloop()
        sys.exit(0)
    
    def _create_window(self):
        """Create the main window"""
        if HAS_TTKBOOTSTRAP:
            self.root = ttkb.Window(themename="darkly")
        else:
            self.root = tk.Tk()
        
        self.root.title(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.root.minsize(1200, 700)
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')
        
        # Icon (if available)
        icon_path = os.path.join(config.BASE_DIR, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass
        
        # Protocol handlers
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Keyboard shortcuts
        self.root.bind('<Control-q>', lambda e: self._on_close())
        self.root.bind('<Control-b>', lambda e: self._backup_database())
        self.root.bind('<F5>', lambda e: self._refresh_current_view())
    
    def _create_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        
        if not HAS_TTKBOOTSTRAP:
            # Configure basic dark theme styles
            style.configure('TFrame', background=COLORS['bg_dark'])
            style.configure('TLabel', background=COLORS['bg_dark'], foreground=COLORS['text_primary'])
            style.configure('TButton', font=FONTS['button'])
        
        # Sidebar styles
        style.configure(
            'Sidebar.TFrame',
            background=COLORS['sidebar_bg']
        )
        
        style.configure(
            'SidebarItem.TButton',
            font=FONTS['sidebar'],
            padding=(15, 12)
        )
        
        style.configure(
            'SidebarItemActive.TButton',
            font=FONTS['sidebar_active'],
            padding=(15, 12)
        )
        
        # Card style
        style.configure(
            'Card.TFrame',
            background=COLORS['bg_card'],
            relief='flat'
        )
        
        # Header style
        style.configure(
            'Header.TFrame',
            background=COLORS['header_bg']
        )
    
    def _create_layout(self):
        """Create main layout containers"""
        # Main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid
        self.main_container.columnconfigure(1, weight=1)
        self.main_container.rowconfigure(0, weight=1)
    
    def _create_sidebar(self):
        """Create sidebar navigation"""
        self.sidebar = ttk.Frame(
            self.main_container,
            style='Sidebar.TFrame',
            width=config.SIDEBAR_WIDTH
        )
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)
        
        # App logo/title
        logo_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        logo_frame.pack(fill=tk.X, pady=(SPACING['lg'], SPACING['xl']))
        
        logo_label = ttk.Label(
            logo_frame,
            text=f"💼 {config.APP_NAME}",
            font=FONTS['heading_small'],
            foreground=COLORS['primary']
        )
        logo_label.pack(padx=SPACING['md'])
        
        version_label = ttk.Label(
            logo_frame,
            text=f"v{config.APP_VERSION}",
            font=FONTS['body_small'],
            foreground=COLORS['text_muted']
        )
        version_label.pack(padx=SPACING['md'])
        
        # Navigation items
        self.nav_items = [
            ('dashboard', ICONS['dashboard'], 'Dashboard'),
            ('accounts', ICONS['accounts'], 'Chart of Accounts'),
            ('journal', ICONS['journal'], 'Journal Entry'),
            ('expenses', ICONS['expenses'], 'Expenses'),
            ('cashbook', ICONS['cashbook'], 'Cash Book'),
            ('bankbook', ICONS['bankbook'], 'Bank Book'),
            ('reports', ICONS['reports'], 'Reports'),
            None,  # Separator
            ('settings', ICONS['settings'], 'Settings'),
            ('license', ICONS['license'], 'License'),
        ]
        
        self.nav_buttons = {}
        
        for item in self.nav_items:
            if item is None:
                # Separator
                sep = ttk.Separator(self.sidebar, orient='horizontal')
                sep.pack(fill=tk.X, padx=SPACING['md'], pady=SPACING['md'])
                continue
            
            key, icon, label = item
            
            btn_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
            btn_frame.pack(fill=tk.X)
            
            btn = tk.Button(
                btn_frame,
                text=f"  {icon}  {label}",
                font=FONTS['sidebar'],
                anchor='w',
                bg=COLORS['sidebar_bg'],
                fg=COLORS['text_secondary'],
                activebackground=COLORS['sidebar_active'],
                activeforeground=COLORS['text_primary'],
                bd=0,
                padx=SPACING['lg'],
                pady=SPACING['md'],
                cursor='hand2',
                command=lambda k=key: self._show_view(k)
            )
            btn.pack(fill=tk.X)
            
            self.nav_buttons[key] = btn
            
            # Hover effects
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=COLORS['sidebar_active']))
            btn.bind('<Leave>', lambda e, b=btn, k=key: self._reset_button_bg(b, k))
        
        # Spacer
        spacer = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        spacer.pack(fill=tk.BOTH, expand=True)
        
        # Exit button at bottom
        exit_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        exit_frame.pack(fill=tk.X, pady=SPACING['md'])
        
        exit_btn = tk.Button(
            exit_frame,
            text=f"  {ICONS['exit']}  Exit",
            font=FONTS['sidebar'],
            anchor='w',
            bg=COLORS['sidebar_bg'],
            fg=COLORS['danger'],
            activebackground=COLORS['sidebar_active'],
            activeforeground=COLORS['danger'],
            bd=0,
            padx=SPACING['lg'],
            pady=SPACING['md'],
            cursor='hand2',
            command=self._on_close
        )
        exit_btn.pack(fill=tk.X)
    
    def _reset_button_bg(self, btn, key):
        """Reset button background when mouse leaves"""
        if self.current_view != key:
            btn.configure(bg=COLORS['sidebar_bg'])
    
    def _create_content_area(self):
        """Create main content area"""
        self.content_frame = ttk.Frame(self.main_container)
        self.content_frame.grid(row=0, column=1, sticky='nsew')
        
        # Store view instances
        self.views = {}
        self.current_view = None
    
    def _create_status_bar(self):
        """Create status bar at bottom"""
        self.status_bar = ttk.Frame(self.root, style='Header.TFrame')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # License status
        self.license_status_var = tk.StringVar(value="Checking license...")
        license_label = ttk.Label(
            self.status_bar,
            textvariable=self.license_status_var,
            font=FONTS['body_small']
        )
        license_label.pack(side=tk.LEFT, padx=SPACING['md'], pady=SPACING['xs'])
        
        # Company name
        company = self.db.get_setting('company_name', 'My Company')
        company_label = ttk.Label(
            self.status_bar,
            text=company,
            font=FONTS['body_small'],
            foreground=COLORS['text_muted']
        )
        company_label.pack(side=tk.RIGHT, padx=SPACING['md'], pady=SPACING['xs'])
        
        # Backup button
        backup_btn = ttk.Button(
            self.status_bar,
            text=f"{ICONS['backup']} Backup",
            command=self._backup_database
        )
        backup_btn.pack(side=tk.RIGHT, padx=SPACING['sm'], pady=SPACING['xs'])
    
    def _show_view(self, view_name: str):
        """Switch to a different view"""
        # Update sidebar highlighting
        for key, btn in self.nav_buttons.items():
            if key == view_name:
                btn.configure(bg=COLORS['sidebar_active'], fg=COLORS['text_primary'])
            else:
                btn.configure(bg=COLORS['sidebar_bg'], fg=COLORS['text_secondary'])
        
        self.current_view = view_name
        
        # Clear current content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create view if not cached
        view_map = {
            'dashboard': lambda: DashboardView(self.content_frame, self.db, self.license_manager),
            'accounts': lambda: AccountsView(self.content_frame, self.db, self.license_manager),
            'journal': lambda: JournalView(self.content_frame, self.db, self.license_manager),
            'expenses': lambda: ExpensesView(self.content_frame, self.db, self.license_manager),
            'cashbook': lambda: CashBookView(self.content_frame, self.db, self.license_manager),
            'bankbook': lambda: BankBookView(self.content_frame, self.db, self.license_manager),
            'reports': lambda: ReportsView(self.content_frame, self.db, self.license_manager),
            'settings': lambda: SettingsView(self.content_frame, self.db, self.license_manager),
            'license': lambda: LicenseView(self.content_frame, self.db, self.license_manager, self._update_license_status),
        }
        
        if view_name in view_map:
            view = view_map[view_name]()
            view.pack(fill=tk.BOTH, expand=True)
    
    def _refresh_current_view(self):
        """Refresh the current view"""
        if self.current_view:
            self._show_view(self.current_view)
    
    def _update_license_status(self):
        """Update license status in status bar"""
        status, details = self.license_manager.get_current_status()
        
        if status == LicenseStatus.TRIAL:
            entries = details.get('entries_used', 0)
            limit = details.get('entries_limit', 30)
            text = f"{ICONS['trial']} Trial: {entries}/{limit} entries"
            color = COLORS['warning']
        elif status == LicenseStatus.ACTIVE:
            text = f"{ICONS['active']} License Active"
            color = COLORS['success']
        else:
            text = f"{ICONS['locked']} {details.get('message', 'License Issue')}"
            color = COLORS['danger']
        
        self.license_status_var.set(text)
    
    def _backup_database(self):
        """Create database backup"""
        backup_path = self.db.backup_database()
        if backup_path:
            messagebox.showinfo("Backup Created", f"Database backed up to:\n{backup_path}")
        else:
            messagebox.showerror("Backup Failed", "Could not create backup")
    
    def _on_close(self):
        """Handle window close"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            # Create backup on exit
            self.db.backup_database()
            self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()
