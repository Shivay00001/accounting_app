"""
Export Utilities - CSV and PDF Generation
"""
import csv
import os
from datetime import datetime
from typing import List, Dict, Any

# PDF generation with reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

import config


class CSVExporter:
    """Export data to CSV format"""
    
    @staticmethod
    def export_to_csv(data: List[Dict], filepath: str, headers: List[str] = None) -> bool:
        """
        Export list of dictionaries to CSV file.
        
        Args:
            data: List of dictionaries to export
            filepath: Output file path
            headers: Optional list of column headers (uses dict keys if not provided)
        
        Returns:
            True if successful
        """
        if not data:
            return False
        
        try:
            # Use provided headers or extract from first row
            if not headers:
                headers = list(data[0].keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)
            
            return True
        except Exception as e:
            print(f"CSV Export Error: {e}")
            return False
    
    @staticmethod
    def export_trial_balance(trial_balance: Dict, filepath: str) -> bool:
        """Export trial balance to CSV"""
        data = []
        for acc in trial_balance['accounts']:
            data.append({
                'Code': acc['code'],
                'Account Name': acc['name'],
                'Type': acc['type'],
                'Debit': acc.get('debit_balance', 0),
                'Credit': acc.get('credit_balance', 0)
            })
        
        # Add totals row
        data.append({
            'Code': '',
            'Account Name': 'TOTAL',
            'Type': '',
            'Debit': trial_balance['total_debit'],
            'Credit': trial_balance['total_credit']
        })
        
        return CSVExporter.export_to_csv(data, filepath, ['Code', 'Account Name', 'Type', 'Debit', 'Credit'])
    
    @staticmethod
    def export_ledger(ledger: List[Dict], account_name: str, filepath: str) -> bool:
        """Export ledger entries to CSV"""
        data = []
        for entry in ledger:
            data.append({
                'Date': entry['date'],
                'Voucher': entry['voucher_number'],
                'Type': entry['voucher_type'],
                'Particulars': entry.get('particulars', entry.get('narration', '')),
                'Debit': entry.get('debit', 0),
                'Credit': entry.get('credit', 0),
                'Balance': entry.get('balance', 0)
            })
        
        return CSVExporter.export_to_csv(
            data, filepath, 
            ['Date', 'Voucher', 'Type', 'Particulars', 'Debit', 'Credit', 'Balance']
        )
    
    @staticmethod
    def export_profit_loss(pnl: Dict, filepath: str) -> bool:
        """Export P&L to CSV"""
        data = []
        
        # Income section
        data.append({'Category': 'INCOME', 'Account': '', 'Amount': ''})
        for inc in pnl['income']:
            data.append({
                'Category': '',
                'Account': f"{inc['code']} - {inc['name']}",
                'Amount': inc['amount']
            })
        data.append({'Category': '', 'Account': 'Total Income', 'Amount': pnl['total_income']})
        
        data.append({'Category': '', 'Account': '', 'Amount': ''})
        
        # Expense section
        data.append({'Category': 'EXPENSES', 'Account': '', 'Amount': ''})
        for exp in pnl['expenses']:
            data.append({
                'Category': '',
                'Account': f"{exp['code']} - {exp['name']}",
                'Amount': exp['amount']
            })
        data.append({'Category': '', 'Account': 'Total Expenses', 'Amount': pnl['total_expenses']})
        
        data.append({'Category': '', 'Account': '', 'Amount': ''})
        data.append({
            'Category': 'NET ' + ('PROFIT' if pnl['is_profit'] else 'LOSS'),
            'Account': '',
            'Amount': pnl['net_profit']
        })
        
        return CSVExporter.export_to_csv(data, filepath, ['Category', 'Account', 'Amount'])


class PDFExporter:
    """Export reports to PDF format"""
    
    def __init__(self):
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required for PDF export. Install it with: pip install reportlab")
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontSize=18,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=11,
            fontName='Helvetica-Bold',
            spaceBefore=12,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='TableTotal',
            fontSize=10,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))
    
    def _get_company_header(self, db) -> List:
        """Get company header elements"""
        company_name = db.get_setting('company_name', 'My Company')
        company_address = db.get_setting('company_address', '')
        company_gstin = db.get_setting('company_gstin', '')
        
        elements = [
            Paragraph(company_name, self.styles['CompanyName'])
        ]
        
        if company_address:
            elements.append(Paragraph(company_address, self.styles['Normal']))
        
        if company_gstin:
            elements.append(Paragraph(f"GSTIN: {company_gstin}", self.styles['Normal']))
        
        return elements
    
    def export_trial_balance(self, trial_balance: Dict, filepath: str, db) -> bool:
        """Export trial balance to PDF"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            
            # Header
            elements.extend(self._get_company_header(db))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("TRIAL BALANCE", self.styles['ReportTitle']))
            elements.append(Paragraph(f"As on {trial_balance['as_of_date']}", self.styles['ReportSubtitle']))
            
            # Table data
            table_data = [['Code', 'Account Name', 'Debit (₹)', 'Credit (₹)']]
            
            for acc in trial_balance['accounts']:
                table_data.append([
                    acc['code'],
                    acc['name'],
                    f"{acc.get('debit_balance', 0):,.2f}" if acc.get('debit_balance', 0) else '',
                    f"{acc.get('credit_balance', 0):,.2f}" if acc.get('credit_balance', 0) else ''
                ])
            
            # Totals row
            table_data.append([
                '', 'TOTAL',
                f"{trial_balance['total_debit']:,.2f}",
                f"{trial_balance['total_credit']:,.2f}"
            ])
            
            # Create table
            table = Table(table_data, colWidths=[60, 250, 90, 90])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            elements.append(table)
            
            # Balance status
            status = "✓ Balanced" if trial_balance['is_balanced'] else "✗ Not Balanced"
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Status: {status}", self.styles['Normal']))
            
            doc.build(elements)
            return True
            
        except Exception as e:
            print(f"PDF Export Error: {e}")
            return False
    
    def export_profit_loss(self, pnl: Dict, filepath: str, db) -> bool:
        """Export P&L Statement to PDF"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            
            # Header
            elements.extend(self._get_company_header(db))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("PROFIT & LOSS STATEMENT", self.styles['ReportTitle']))
            elements.append(Paragraph(
                f"For the period {pnl['period']['start']} to {pnl['period']['end']}",
                self.styles['ReportSubtitle']
            ))
            
            # Income section
            elements.append(Paragraph("INCOME", self.styles['SectionHeader']))
            
            if pnl['income']:
                income_data = [['Account', 'Amount (₹)']]
                for inc in pnl['income']:
                    income_data.append([
                        f"{inc['code']} - {inc['name']}",
                        f"{inc['amount']:,.2f}"
                    ])
                income_data.append(['Total Income', f"{pnl['total_income']:,.2f}"])
                
                income_table = Table(income_data, colWidths=[350, 100])
                income_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d5f5e3')),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(income_table)
            
            elements.append(Spacer(1, 12))
            
            # Expenses section
            elements.append(Paragraph("EXPENSES", self.styles['SectionHeader']))
            
            if pnl['expenses']:
                expense_data = [['Account', 'Amount (₹)']]
                for exp in pnl['expenses']:
                    expense_data.append([
                        f"{exp['code']} - {exp['name']}",
                        f"{exp['amount']:,.2f}"
                    ])
                expense_data.append(['Total Expenses', f"{pnl['total_expenses']:,.2f}"])
                
                expense_table = Table(expense_data, colWidths=[350, 100])
                expense_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fadbd8')),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(expense_table)
            
            elements.append(Spacer(1, 20))
            
            # Net Profit/Loss
            net_label = "NET PROFIT" if pnl['is_profit'] else "NET LOSS"
            net_color = colors.HexColor('#27ae60') if pnl['is_profit'] else colors.HexColor('#e74c3c')
            
            net_data = [[net_label, f"₹ {abs(pnl['net_profit']):,.2f}"]]
            net_table = Table(net_data, colWidths=[350, 100])
            net_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TEXTCOLOR', (0, 0), (-1, -1), net_color),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('BOX', (0, 0), (-1, -1), 2, net_color),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(net_table)
            
            doc.build(elements)
            return True
            
        except Exception as e:
            print(f"PDF Export Error: {e}")
            return False
    
    def export_balance_sheet(self, bs: Dict, filepath: str, db) -> bool:
        """Export Balance Sheet to PDF"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            
            # Header
            elements.extend(self._get_company_header(db))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("BALANCE SHEET", self.styles['ReportTitle']))
            elements.append(Paragraph(f"As on {bs['as_of_date']}", self.styles['ReportSubtitle']))
            
            # Assets
            elements.append(Paragraph("ASSETS", self.styles['SectionHeader']))
            if bs['assets']:
                asset_data = [['Account', 'Amount (₹)']]
                for asset in bs['assets']:
                    asset_data.append([
                        f"{asset['code']} - {asset['name']}",
                        f"{asset['balance']:,.2f}"
                    ])
                asset_data.append(['Total Assets', f"{bs['total_assets']:,.2f}"])
                
                asset_table = Table(asset_data, colWidths=[350, 100])
                asset_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d6eaf8')),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(asset_table)
            
            elements.append(Spacer(1, 12))
            
            # Liabilities
            elements.append(Paragraph("LIABILITIES", self.styles['SectionHeader']))
            if bs['liabilities']:
                liab_data = [['Account', 'Amount (₹)']]
                for liab in bs['liabilities']:
                    liab_data.append([
                        f"{liab['code']} - {liab['name']}",
                        f"{liab['balance']:,.2f}"
                    ])
                liab_data.append(['Total Liabilities', f"{bs['total_liabilities']:,.2f}"])
                
                liab_table = Table(liab_data, colWidths=[350, 100])
                liab_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5eef8')),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(liab_table)
            
            elements.append(Spacer(1, 12))
            
            # Equity
            elements.append(Paragraph("EQUITY", self.styles['SectionHeader']))
            equity_data = [['Account', 'Amount (₹)']]
            for eq in bs['equity']:
                equity_data.append([
                    f"{eq['code']} - {eq['name']}",
                    f"{eq['balance']:,.2f}"
                ])
            if bs['retained_earnings'] != 0:
                equity_data.append(['Retained Earnings (Current P&L)', f"{bs['retained_earnings']:,.2f}"])
            total_eq = bs['total_equity'] + bs['retained_earnings']
            equity_data.append(['Total Equity', f"{total_eq:,.2f}"])
            
            equity_table = Table(equity_data, colWidths=[350, 100])
            equity_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fdebd0')),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(equity_table)
            
            elements.append(Spacer(1, 20))
            
            # Summary
            summary_data = [
                ['Total Liabilities + Equity', f"₹ {bs['total_liabilities_and_equity']:,.2f}"]
            ]
            summary_table = Table(summary_data, colWidths=[350, 100])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2c3e50')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(summary_table)
            
            # Balance status
            status = "✓ Balanced" if bs['is_balanced'] else "✗ Not Balanced"
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Status: {status}", self.styles['Normal']))
            
            doc.build(elements)
            return True
            
        except Exception as e:
            print(f"PDF Export Error: {e}")
            return False
    
    def export_ledger(self, ledger: List[Dict], account_name: str, 
                      period: Dict, filepath: str, db) -> bool:
        """Export ledger to PDF"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
            elements = []
            
            # Header
            elements.extend(self._get_company_header(db))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"LEDGER: {account_name}", self.styles['ReportTitle']))
            elements.append(Paragraph(
                f"For the period {period.get('start', '')} to {period.get('end', '')}",
                self.styles['ReportSubtitle']
            ))
            
            # Table
            table_data = [['Date', 'Voucher', 'Type', 'Particulars', 'Debit (₹)', 'Credit (₹)', 'Balance (₹)']]
            
            for entry in ledger:
                table_data.append([
                    entry['date'],
                    entry['voucher_number'],
                    entry['voucher_type'],
                    entry.get('particulars', entry.get('narration', ''))[:40],
                    f"{entry.get('debit', 0):,.2f}" if entry.get('debit') else '',
                    f"{entry.get('credit', 0):,.2f}" if entry.get('credit') else '',
                    f"{entry.get('balance', 0):,.2f}"
                ])
            
            table = Table(table_data, colWidths=[70, 80, 60, 200, 80, 80, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            elements.append(table)
            
            doc.build(elements)
            return True
            
        except Exception as e:
            print(f"PDF Export Error: {e}")
            return False


def get_export_filepath(base_name: str, extension: str) -> str:
    """Generate export file path with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}.{extension}"
    return os.path.join(config.DATA_DIR, filename)
