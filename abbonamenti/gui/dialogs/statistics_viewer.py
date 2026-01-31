"""
Statistics viewer dialog with payment analytics and charts
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt5.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QProgressDialog,
)

from abbonamenti.database.manager import DatabaseManager
from abbonamenti.gui.styles import get_stylesheet, get_color


class StatisticsLoaderThread(QThread):
    """Background thread for loading statistics"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, db_manager: DatabaseManager, year: Optional[int], month: Optional[int]):
        super().__init__()
        self.db_manager = db_manager
        self.year = year
        self.month = month
    
    def run(self):
        """Load statistics in background"""
        try:
            stats = {
                "payment_stats": self.db_manager.get_payment_statistics(self.year, self.month),
                "monthly_revenue": self.db_manager.get_monthly_revenue(self.year, self.month),
                "methods_breakdown": self.db_manager.get_payment_methods_breakdown(self.year, self.month),
                "trend": self.db_manager.get_revenue_trend(self.year, self.month),
                "subscriptions": self.db_manager.get_subscriptions_per_month(self.year, self.month),
            }
            self.finished.emit(stats)
        except Exception as e:
            self.error.emit(str(e))


class StatCard(QWidget):
    """Widget for displaying a single statistic"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #757575; font-size: 11px;")
        layout.addWidget(title_label)
        
        # Value - store reference for updates
        self.value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {get_color('primary')};")
        layout.addWidget(self.value_label)
        
        # Subtitle - store reference for updates
        self.subtitle_label = None
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet("color: #9E9E9E; font-size: 10px;")
            layout.addWidget(self.subtitle_label)
        
        # Styling
        self.setStyleSheet(
            f"""
            StatCard {{
                background-color: {get_color('card_bg')};
                border: 1px solid {get_color('border')};
                border-radius: 8px;
            }}
            StatCard:hover {{
                border: 1px solid {get_color('primary')};
            }}
            """
        )
    
    def update_value(self, value: str):
        """Update the value displayed in the card"""
        self.value_label.setText(value)
    
    def update_subtitle(self, subtitle: str):
        """Update the subtitle if it exists"""
        if self.subtitle_label:
            self.subtitle_label.setText(subtitle)


class ChartWidget(QWidget):
    """Widget for displaying matplotlib charts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor=get_color("card_bg"))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setAutoFillBackground(False)
    
    def clear(self):
        """Clear the figure"""
        self.figure.clear()
    
    def draw(self):
        """Redraw the canvas"""
        self.canvas.draw()

    def style_axes(self, ax):
        """Apply theme-aware colors to axes"""
        ax.set_facecolor(get_color("surface"))
        ax.tick_params(colors=get_color("text_primary"))
        for spine in ax.spines.values():
            spine.set_color(get_color("border"))
        ax.xaxis.label.set_color(get_color("text_primary"))
        ax.yaxis.label.set_color(get_color("text_primary"))
        ax.title.set_color(get_color("text_primary"))

    def style_grid(self, ax):
        grid_color = get_color("border")
        ax.grid(True, alpha=0.3, linestyle="--", color=grid_color)


class StatisticsViewer(QDialog):
    """Dialog for viewing payment statistics and charts"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.loader_thread = None
        self.progress_dialog = None
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        self.setWindowTitle("📊 Statistiche Pagamenti")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(get_stylesheet())
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Header with filters
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        filter_label = QLabel("Filtri:")
        filter_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(filter_label)
        
        # Year filter
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(100)
        current_year = datetime.now().year
        years = ["Tutti"] + [str(y) for y in range(current_year, current_year - 5, -1)]
        self.year_combo.addItems(years)
        self.year_combo.currentTextChanged.connect(self.on_filter_changed)
        header_layout.addWidget(QLabel("Anno:"))
        header_layout.addWidget(self.year_combo)
        
        # Month filter
        self.month_combo = QComboBox()
        self.month_combo.setMinimumWidth(120)
        months = ["Tutti", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                  "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        self.month_combo.addItems(months)
        self.month_combo.currentTextChanged.connect(self.on_filter_changed)
        header_layout.addWidget(QLabel("Mese:"))
        header_layout.addWidget(self.month_combo)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Aggiorna")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.clicked.connect(self.load_statistics)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Statistics cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        
        self.total_card = StatCard("Totale Incassi", "€ 0.00", "")
        self.count_card = StatCard("N° Abbonamenti", "0", "")
        self.average_card = StatCard("Media per Abbonamento", "€ 0.00", "")
        self.methods_card = StatCard("Metodi Pagamento", "0 / 0", "POS / Bollettino")
        
        cards_layout.addWidget(self.total_card)
        cards_layout.addWidget(self.count_card)
        cards_layout.addWidget(self.average_card)
        cards_layout.addWidget(self.methods_card)
        
        main_layout.addLayout(cards_layout)
        
        # Tabs for different charts
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {get_color('border')};
                background-color: {get_color('card_bg')};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                padding: 8px 16px;
                margin-right: 2px;
                background: {get_color('surface')};
                color: {get_color('text_primary')};
            }}
            QTabBar::tab:selected {{
                background-color: {get_color('primary')};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {get_color('light')};
            }}
            """
        )
        
        # Monthly revenue chart
        self.monthly_chart = ChartWidget()
        self.tabs.addTab(self.monthly_chart, "📊 Incassi Mensili")
        
        # Payment methods chart
        self.methods_chart = ChartWidget()
        self.tabs.addTab(self.methods_chart, "🥧 Metodi di Pagamento")
        
        # Trend chart
        self.trend_chart = ChartWidget()
        self.tabs.addTab(self.trend_chart, "📈 Trend Temporale")
        
        # Subscriptions chart
        self.subscriptions_chart = ChartWidget()
        self.tabs.addTab(self.subscriptions_chart, "📅 Abbonamenti per Mese")
        
        main_layout.addWidget(self.tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Chiudi")
        close_btn.setMinimumHeight(36)
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    @pyqtSlot()
    def on_filter_changed(self):
        """Handle filter changes"""
        self.load_statistics()
    
    def get_filter_dates(self) -> Tuple[Optional[int], Optional[int]]:
        """Get year and month from filters"""
        year_text = self.year_combo.currentText()
        month_text = self.month_combo.currentText()
        
        year = int(year_text) if year_text != "Tutti" else None
        month = self.month_combo.currentIndex() if month_text != "Tutti" else None
        
        return year, month
    
    def show_loading(self):
        """Show loading progress dialog"""
        if self.progress_dialog is None:
            self.progress_dialog = QProgressDialog(
                "Elaborating data...", None, 0, 0, self
            )
            self.progress_dialog.setWindowTitle("Caricamento Dati")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumWidth(300)
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.setStyleSheet(get_stylesheet())
        self.progress_dialog.show()
    
    def hide_loading(self):
        """Hide loading progress dialog"""
        if self.progress_dialog:
            self.progress_dialog.close()
    
    def on_statistics_loaded(self, stats: dict):
        """Handle loaded statistics"""
        self.hide_loading()
        
        # Update cards
        total = stats["payment_stats"].get("total_revenue", 0.0)
        count = stats["payment_stats"].get("subscription_count", 0)
        average = stats["payment_stats"].get("average_payment", 0.0)
        pos_count = stats["payment_stats"].get("pos_count", 0)
        bollettino_count = stats["payment_stats"].get("bollettino_count", 0)
        
        self.total_card.update_value(f"€ {total:,.2f}")
        self.count_card.update_value(str(count))
        self.average_card.update_value(f"€ {average:,.2f}")
        self.methods_card.update_value(f"{pos_count} / {bollettino_count}")
        
        # Update charts
        self.update_monthly_chart_with_data(stats["monthly_revenue"])
        self.update_methods_chart_with_data(stats["methods_breakdown"])
        self.update_trend_chart_with_data(stats["trend"])
        self.update_subscriptions_chart_with_data(stats["subscriptions"])
    
    def on_statistics_error(self, error: str):
        """Handle statistics loading error"""
        self.hide_loading()
        print(f"Error loading statistics: {error}")
    
    def load_statistics(self):
        """Load statistics in background thread"""
        # Stop previous thread if running
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait()
        
        year, month = self.get_filter_dates()
        
        # Show loading dialog
        self.show_loading()
        
        # Create and start loader thread
        self.loader_thread = StatisticsLoaderThread(self.db_manager, year, month)
        self.loader_thread.finished.connect(self.on_statistics_loaded)
        self.loader_thread.error.connect(self.on_statistics_error)
        self.loader_thread.start()
    
    def update_monthly_chart_with_data(self, monthly_data: List[Tuple[str, float]]):
        """Update monthly revenue bar chart with provided data"""
        
        self.monthly_chart.clear()
        ax = self.monthly_chart.figure.add_subplot(111)
        
        if monthly_data:
            months = [data[0] for data in monthly_data]
            revenues = [data[1] for data in monthly_data]

            x_positions = list(range(len(months)))
            colors = [get_color('primary') if r > 0 else '#BDBDBD' for r in revenues]
            bars = ax.bar(x_positions, revenues, color=colors, alpha=0.8)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'€{height:,.0f}',
                           ha='center', va='bottom', fontsize=9)
            
            # Thin x-axis labels to avoid overcrowding (aim for <= 10 labels)
            max_labels = 10
            step = max(1, len(months) // max_labels + (1 if len(months) % max_labels else 0))
            tick_idx = list(range(0, len(months), step))
            if tick_idx and tick_idx[-1] != len(months) - 1:
                tick_idx.append(len(months) - 1)
            ax.set_xticks(tick_idx)
            ax.set_xticklabels([months[i] for i in tick_idx], rotation=45, ha='right')

            ax.set_xlabel('Mese', fontsize=11, fontweight='bold')
            ax.set_ylabel('Incassi (€)', fontsize=11, fontweight='bold')
            ax.set_title('Incassi Mensili', fontsize=13, fontweight='bold', pad=15)
            self.monthly_chart.style_grid(ax)
            ax.set_axisbelow(True)
        else:
            ax.text(0.5, 0.5, 'Nessun dato disponibile', 
                   ha='center', va='center', fontsize=14, color='#757575',
                   transform=ax.transAxes)
        
        self.monthly_chart.style_axes(ax)
        self.monthly_chart.figure.tight_layout()
        self.monthly_chart.draw()
    
    def update_methods_chart_with_data(self, methods_data: Dict[str, int]):
        """Update payment methods pie chart with provided data"""
        
        self.methods_chart.clear()
        ax = self.methods_chart.figure.add_subplot(111)
        
        if methods_data and any(v > 0 for v in methods_data.values()):
            labels = list(methods_data.keys())
            sizes = list(methods_data.values())
            colors = [get_color('primary'), get_color('warning')]
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                               colors=colors, startangle=90,
                                               textprops={'fontsize': 11})
            
            # Make percentage text bold
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title('Distribuzione Metodi di Pagamento', fontsize=13, 
                        fontweight='bold', pad=15)
        else:
            ax.text(0.5, 0.5, 'Nessun dato disponibile', 
                   ha='center', va='center', fontsize=14, color='#757575',
                   transform=ax.transAxes)
        
        self.methods_chart.style_axes(ax)
        self.methods_chart.figure.tight_layout()
        self.methods_chart.draw()
    
    def update_trend_chart_with_data(self, trend_data: List[Tuple[str, float]]):
        """Update revenue trend line chart with provided data"""
        
        self.trend_chart.clear()
        ax = self.trend_chart.figure.add_subplot(111)
        
        if trend_data and len(trend_data) > 1:
            dates = [data[0] for data in trend_data]
            revenues = [data[1] for data in trend_data]

            # Use numeric x positions to control tick density
            x_positions = list(range(len(dates)))
            ax.plot(x_positions, revenues, marker='o', linewidth=2,
                   markersize=6, color=get_color('primary'), label='Incassi')
            ax.fill_between(x_positions, revenues, alpha=0.3, color=get_color('primary'))

            # Thin x-axis labels to avoid overcrowding (aim for <= 10 labels)
            max_labels = 10
            step = max(1, len(dates) // max_labels + (1 if len(dates) % max_labels else 0))
            tick_idx = list(range(0, len(dates), step))
            if tick_idx[-1] != len(dates) - 1:
                tick_idx.append(len(dates) - 1)
            ax.set_xticks(tick_idx)
            ax.set_xticklabels([dates[i] for i in tick_idx], rotation=45, ha='right')
            
            ax.set_xlabel('Periodo', fontsize=11, fontweight='bold')
            ax.set_ylabel('Incassi Cumulativi (€)', fontsize=11, fontweight='bold')
            ax.set_title('Trend Incassi nel Tempo', fontsize=13, fontweight='bold', pad=15)
            self.trend_chart.style_grid(ax)
            ax.set_axisbelow(True)
            ax.legend()
        else:
            ax.text(0.5, 0.5, 'Nessun dato disponibile', 
                   ha='center', va='center', fontsize=14, color='#757575',
                   transform=ax.transAxes)
        
        self.trend_chart.style_axes(ax)
        self.trend_chart.figure.tight_layout()
        self.trend_chart.draw()
    
    def update_subscriptions_chart_with_data(self, subs_data: List[Tuple[str, int]]):
        """Update subscriptions per month chart with provided data"""
        
        self.subscriptions_chart.clear()
        ax = self.subscriptions_chart.figure.add_subplot(111)
        
        if subs_data:
            months = [data[0] for data in subs_data]
            counts = [data[1] for data in subs_data]

            x_positions = list(range(len(months)))
            bars = ax.bar(x_positions, counts, color=get_color('success'), alpha=0.8)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}',
                           ha='center', va='bottom', fontsize=9)
            
            # Thin x-axis labels to avoid overcrowding (aim for <= 10 labels)
            max_labels = 10
            step = max(1, len(months) // max_labels + (1 if len(months) % max_labels else 0))
            tick_idx = list(range(0, len(months), step))
            if tick_idx and tick_idx[-1] != len(months) - 1:
                tick_idx.append(len(months) - 1)
            ax.set_xticks(tick_idx)
            ax.set_xticklabels([months[i] for i in tick_idx], rotation=45, ha='right')

            ax.set_xlabel('Mese', fontsize=11, fontweight='bold')
            ax.set_ylabel('Numero Abbonamenti', fontsize=11, fontweight='bold')
            ax.set_title('Abbonamenti Creati per Mese', fontsize=13, 
                        fontweight='bold', pad=15)
            self.subscriptions_chart.style_grid(ax)
            ax.set_axisbelow(True)
        else:
            ax.text(0.5, 0.5, 'Nessun dato disponibile', 
                   ha='center', va='center', fontsize=14, color='#757575',
                   transform=ax.transAxes)
        
        self.subscriptions_chart.style_axes(ax)
        self.subscriptions_chart.figure.tight_layout()
        self.subscriptions_chart.draw()
