"""
Reusable UI Components
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Callable, Any, Optional

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False
    ttkb = ttk

from ui.styles import COLORS, FONTS, SPACING, ICONS


class SearchableCombobox(ttk.Frame):
    """Combobox with search/filter functionality"""
    
    def __init__(self, parent, values: List[str] = None, on_select: Callable = None, **kwargs):
        super().__init__(parent)
        
        self.all_values = values or []
        self.on_select = on_select
        
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, **kwargs)
        self.entry.pack(fill=tk.X)
        
        self.listbox_frame = None
        self.listbox = None
        
        self.entry.bind('<KeyRelease>', self._on_key)
        self.entry.bind('<FocusIn>', self._show_dropdown)
        self.entry.bind('<FocusOut>', self._delayed_hide)
        self.entry.bind('<Return>', self._select_first)
    
    def _on_key(self, event):
        search = self.var.get().lower()
        if not search:
            self._update_listbox(self.all_values)
        else:
            filtered = [v for v in self.all_values if search in v.lower()]
            self._update_listbox(filtered)
    
    def _show_dropdown(self, event=None):
        if self.listbox_frame:
            return
        
        self.listbox_frame = tk.Toplevel(self)
        self.listbox_frame.wm_overrideredirect(True)
        
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        
        self.listbox_frame.geometry(f"{width}x150+{x}+{y}")
        
        scrollbar = ttk.Scrollbar(self.listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(
            self.listbox_frame,
            yscrollcommand=scrollbar.set,
            font=FONTS['body']
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        self.listbox.bind('<Double-Button-1>', self._on_listbox_select)
        self.listbox.bind('<Return>', self._on_listbox_select)
        
        self._update_listbox(self.all_values)
    
    def _update_listbox(self, values):
        if not self.listbox:
            return
        self.listbox.delete(0, tk.END)
        for value in values:
            self.listbox.insert(tk.END, value)
    
    def _on_listbox_select(self, event):
        if not self.listbox:
            return
        selection = self.listbox.curselection()
        if selection:
            value = self.listbox.get(selection[0])
            self.var.set(value)
            self._hide_dropdown()
            if self.on_select:
                self.on_select(value)
    
    def _select_first(self, event):
        if self.listbox and self.listbox.size() > 0:
            value = self.listbox.get(0)
            self.var.set(value)
            self._hide_dropdown()
            if self.on_select:
                self.on_select(value)
    
    def _delayed_hide(self, event):
        self.after(200, self._hide_dropdown)
    
    def _hide_dropdown(self):
        if self.listbox_frame:
            self.listbox_frame.destroy()
            self.listbox_frame = None
            self.listbox = None
    
    def set_values(self, values: List[str]):
        self.all_values = values
        if self.listbox:
            self._update_listbox(values)
    
    def get(self) -> str:
        return self.var.get()
    
    def set(self, value: str):
        self.var.set(value)


class DataTable(ttk.Frame):
    """Sortable, searchable data table with pagination"""
    
    def __init__(self, parent, columns: List[Dict], height: int = 15, 
                 on_select: Callable = None, on_double_click: Callable = None, **kwargs):
        """
        columns: [{'key': 'id', 'label': 'ID', 'width': 50, 'anchor': 'center'}, ...]
        """
        super().__init__(parent, **kwargs)
        
        self.columns = columns
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.data = []
        self._sort_reverse = {}
        
        self._create_widgets(height)
    
    def _create_widgets(self, height):
        # Treeview with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Vertical scrollbar
        y_scroll = ttk.Scrollbar(tree_frame)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        x_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        column_ids = [col['key'] for col in self.columns]
        self.tree = ttk.Treeview(
            tree_frame,
            columns=column_ids,
            show='headings',
            height=height,
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)
        
        # Configure columns
        for col in self.columns:
            self.tree.heading(
                col['key'],
                text=col['label'],
                command=lambda c=col['key']: self._sort_by_column(c)
            )
            self.tree.column(
                col['key'],
                width=col.get('width', 100),
                anchor=col.get('anchor', 'w'),
                minwidth=50
            )
        
        # Bindings
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-Button-1>', self._on_double_click)
        
        # Alternating row colors
        self.tree.tag_configure('oddrow', background='#1f2940')
        self.tree.tag_configure('evenrow', background='#16213e')
    
    def load_data(self, data: List[Dict]):
        """Load data into the table"""
        self.data = data
        self._refresh_display()
    
    def _refresh_display(self):
        """Refresh the tree display"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Insert new data
        for i, row in enumerate(self.data):
            values = [row.get(col['key'], '') for col in self.columns]
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert('', tk.END, values=values, tags=(tag,), iid=str(i))
    
    def _sort_by_column(self, column):
        """Sort table by column"""
        reverse = self._sort_reverse.get(column, False)
        
        try:
            # Try numeric sort
            self.data.sort(key=lambda x: float(x.get(column, 0) or 0), reverse=reverse)
        except (ValueError, TypeError):
            # Fall back to string sort
            self.data.sort(key=lambda x: str(x.get(column, '')).lower(), reverse=reverse)
        
        self._sort_reverse[column] = not reverse
        self._refresh_display()
    
    def _on_select(self, event):
        if self.on_select:
            selected = self.get_selected()
            if selected:
                self.on_select(selected)
    
    def _on_double_click(self, event):
        if self.on_double_click:
            selected = self.get_selected()
            if selected:
                self.on_double_click(selected)
    
    def get_selected(self) -> Optional[Dict]:
        """Get currently selected row data"""
        selection = self.tree.selection()
        if selection:
            idx = int(selection[0])
            if 0 <= idx < len(self.data):
                return self.data[idx]
        return None
    
    def clear(self):
        """Clear all data"""
        self.data = []
        for item in self.tree.get_children():
            self.tree.delete(item)


class StatCard(ttk.Frame):
    """Dashboard stat card widget"""
    
    def __init__(self, parent, title: str, value: str = "0", 
                 icon: str = "", color: str = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(style='Card.TFrame')
        
        # Icon and title row
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=SPACING['md'], pady=(SPACING['md'], SPACING['xs']))
        
        if icon:
            icon_label = ttk.Label(header, text=icon, font=('Segoe UI Emoji', 16))
            icon_label.pack(side=tk.LEFT)
        
        title_label = ttk.Label(
            header, 
            text=title, 
            font=FONTS['body_small'],
            foreground=COLORS['text_secondary']
        )
        title_label.pack(side=tk.LEFT, padx=(SPACING['xs'], 0))
        
        # Value
        self.value_var = tk.StringVar(value=value)
        value_label = ttk.Label(
            self,
            textvariable=self.value_var,
            font=FONTS['stat_value'],
            foreground=color or COLORS['text_primary']
        )
        value_label.pack(padx=SPACING['md'], pady=(0, SPACING['md']))
    
    def set_value(self, value: str):
        self.value_var.set(value)


class FormField(ttk.Frame):
    """Labeled form field"""
    
    def __init__(self, parent, label: str, field_type: str = 'entry',
                 values: List = None, required: bool = False, **kwargs):
        super().__init__(parent)
        
        # Label
        label_text = f"{label} *" if required else label
        lbl = ttk.Label(self, text=label_text, font=FONTS['body_small'])
        lbl.pack(anchor='w')
        
        # Field
        if field_type == 'entry':
            self.var = tk.StringVar()
            self.field = ttk.Entry(self, textvariable=self.var, **kwargs)
        elif field_type == 'combobox':
            self.var = tk.StringVar()
            self.field = ttk.Combobox(self, textvariable=self.var, values=values or [], **kwargs)
        elif field_type == 'date':
            self.var = tk.StringVar()
            self.field = ttk.Entry(self, textvariable=self.var, **kwargs)
            self.field.insert(0, 'YYYY-MM-DD')
        elif field_type == 'text':
            self.field = tk.Text(self, height=kwargs.get('height', 3), **{k: v for k, v in kwargs.items() if k != 'height'})
            self.var = None
        elif field_type == 'spinbox':
            self.var = tk.StringVar()
            self.field = ttk.Spinbox(self, textvariable=self.var, **kwargs)
        else:
            self.var = tk.StringVar()
            self.field = ttk.Entry(self, textvariable=self.var, **kwargs)
        
        self.field.pack(fill=tk.X, pady=(SPACING['xs'], 0))
    
    def get(self) -> str:
        if self.var:
            return self.var.get()
        elif hasattr(self.field, 'get'):
            return self.field.get('1.0', tk.END).strip()
        return ''
    
    def set(self, value: str):
        if self.var:
            self.var.set(value)
        elif hasattr(self.field, 'delete'):
            self.field.delete('1.0', tk.END)
            self.field.insert('1.0', value)
    
    def clear(self):
        self.set('')


class Toolbar(ttk.Frame):
    """Action toolbar with buttons"""
    
    def __init__(self, parent, buttons: List[Dict], **kwargs):
        """
        buttons: [{'text': 'Add', 'icon': '➕', 'command': func, 'style': 'success'}, ...]
        """
        super().__init__(parent, **kwargs)
        
        for btn_config in buttons:
            text = f"{btn_config.get('icon', '')} {btn_config.get('text', '')}".strip()
            style = btn_config.get('style', 'primary')
            
            if HAS_TTKBOOTSTRAP:
                btn = ttkb.Button(
                    self,
                    text=text,
                    command=btn_config.get('command'),
                    bootstyle=style
                )
            else:
                btn = ttk.Button(
                    self,
                    text=text,
                    command=btn_config.get('command')
                )
            
            btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))


class SearchBar(ttk.Frame):
    """Search bar with entry and button"""
    
    def __init__(self, parent, placeholder: str = "Search...", 
                 on_search: Callable = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_search = on_search
        
        self.search_var = tk.StringVar()
        
        # Search icon/label
        icon = ttk.Label(self, text=ICONS['search'], font=('Segoe UI Emoji', 12))
        icon.pack(side=tk.LEFT, padx=(0, SPACING['xs']))
        
        # Entry
        self.entry = ttk.Entry(self, textvariable=self.search_var, width=30)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.insert(0, placeholder)
        
        self.entry.bind('<FocusIn>', lambda e: self._clear_placeholder())
        self.entry.bind('<FocusOut>', lambda e: self._restore_placeholder(placeholder))
        self.entry.bind('<Return>', lambda e: self._trigger_search())
        self.entry.bind('<KeyRelease>', lambda e: self._trigger_search())
        
        self._placeholder = placeholder
        self._showing_placeholder = True
    
    def _clear_placeholder(self):
        if self._showing_placeholder:
            self.search_var.set('')
            self._showing_placeholder = False
    
    def _restore_placeholder(self, placeholder):
        if not self.search_var.get():
            self.search_var.set(placeholder)
            self._showing_placeholder = True
    
    def _trigger_search(self):
        if self.on_search and not self._showing_placeholder:
            self.on_search(self.search_var.get())
    
    def get(self) -> str:
        if self._showing_placeholder:
            return ''
        return self.search_var.get()
    
    def clear(self):
        self.search_var.set('')
        self._restore_placeholder(self._placeholder)


class ConfirmDialog:
    """Simple confirmation dialog"""
    
    @staticmethod
    def ask(title: str, message: str) -> bool:
        return messagebox.askyesno(title, message)
    
    @staticmethod
    def show_info(title: str, message: str):
        messagebox.showinfo(title, message)
    
    @staticmethod
    def show_error(title: str, message: str):
        messagebox.showerror(title, message)
    
    @staticmethod
    def show_warning(title: str, message: str):
        messagebox.showwarning(title, message)
