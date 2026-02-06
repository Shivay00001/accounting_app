"""
UI Styles and Theming
Modern dark theme configuration using ttkbootstrap
"""

# Color Palette - Modern Dark Theme
COLORS = {
    # Primary colors
    'primary': '#3498db',
    'primary_dark': '#2980b9',
    'primary_light': '#5dade2',
    
    # Secondary colors
    'secondary': '#9b59b6',
    'accent': '#1abc9c',
    
    # Status colors
    'success': '#27ae60',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'info': '#3498db',
    
    # Neutral colors
    'bg_dark': '#1a1a2e',
    'bg_medium': '#16213e',
    'bg_light': '#0f3460',
    'bg_card': '#1f2940',
    
    # Text colors
    'text_primary': '#ffffff',
    'text_secondary': '#b0b8c4',
    'text_muted': '#6c757d',
    
    # Border colors
    'border': '#2d3748',
    'border_light': '#4a5568',
    
    # Special
    'sidebar_bg': '#0d1b2a',
    'sidebar_active': '#1b263b',
    'header_bg': '#1b263b',
    
    # Financial
    'profit': '#00b894',
    'loss': '#d63031',
    'debit': '#74b9ff',
    'credit': '#fd79a8',
}

# Font configuration
FONTS = {
    'heading_large': ('Segoe UI', 24, 'bold'),
    'heading': ('Segoe UI', 18, 'bold'),
    'heading_small': ('Segoe UI', 14, 'bold'),
    'body': ('Segoe UI', 11),
    'body_small': ('Segoe UI', 10),
    'button': ('Segoe UI', 11, 'bold'),
    'monospace': ('Consolas', 11),
    'sidebar': ('Segoe UI', 12),
    'sidebar_active': ('Segoe UI', 12, 'bold'),
    'table_header': ('Segoe UI', 10, 'bold'),
    'table_body': ('Segoe UI', 10),
    'stat_value': ('Segoe UI', 28, 'bold'),
    'stat_label': ('Segoe UI', 10),
}

# Padding and spacing
SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 12,
    'lg': 16,
    'xl': 24,
    'xxl': 32,
}

# Icon emojis for sidebar navigation
ICONS = {
    'dashboard': '📊',
    'accounts': '📋',
    'journal': '📝',
    'expenses': '💸',
    'cashbook': '💰',
    'bankbook': '🏦',
    'reports': '📈',
    'settings': '⚙️',
    'license': '🔑',
    'backup': '💾',
    'export': '📤',
    'help': '❓',
    'exit': '🚪',
    'add': '➕',
    'edit': '✏️',
    'delete': '🗑️',
    'search': '🔍',
    'filter': '🔽',
    'refresh': '🔄',
    'trial': '⏳',
    'active': '✅',
    'locked': '🔒',
}
