"""PyQt5 Weather Application with asynchronous API processing and unit conversions."""

from datetime import datetime
import os
import sys
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api_client import WeatherAPIClient, WeatherAPIError


# -------------------------------------------------------------------
# Multithreading / Worker Setup
# -------------------------------------------------------------------
class WeatherWorker(QThread):
    """Worker thread to fetch weather data without blocking the GUI."""

    data_fetched = pyqtSignal(dict, dict, list)  # current_data, forecast_data, icon_bytes_list
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client: WeatherAPIClient, query: Optional[str] = None, auto_detect: bool = False):
        super().__init__()
        self.api_client = api_client
        self.query = query
        self.auto_detect = auto_detect

    def run(self) -> None:
        """Execute network tasks off the main thread."""
        try:
            search_query = self.query
            if self.auto_detect:
                city, country = self.api_client.get_auto_location()
                if not city:
                    raise WeatherAPIError("Could not determine automatic location.")
                search_query = f"{city},{country}" if country else city

            if not search_query:
                raise WeatherAPIError("Search query cannot be empty.")

            current_data = self.api_client.fetch_current_weather(search_query)
            forecast_data = self.api_client.fetch_forecast(search_query)

            # Pre-fetch main icon + hourly icons asynchronously
            icons: List[bytes] = []
            main_icon_code = current_data["weather"][0]["icon"]
            icons.append(self.api_client.fetch_icon_bytes(main_icon_code))

            # Fetch icons for next 6 hourly forecast slots
            for item in forecast_data.get("list", [])[:6]:
                icon_code = item["weather"][0]["icon"]
                icons.append(self.api_client.fetch_icon_bytes(icon_code))

            self.data_fetched.emit(current_data, forecast_data, icons)

        except WeatherAPIError as err:
            self.error_occurred.emit(str(err))
        except Exception as e:
            self.error_occurred.emit(f"An unexpected error occurred: {str(e)}")


# -------------------------------------------------------------------
# Main UI Window
# -------------------------------------------------------------------
class WeatherAppUI(QWidget):
    """Main PyQt5 Weather Dashboard Interface."""

    def __init__(self):
        super().__init__()
        # Retrieve API Key safely
        api_key = os.getenv("OPENWEATHER_API_KEY", "")
        if not api_key:
            QMessageBox.critical(
                self,
                "API Key Missing",
                "Environment variable OPENWEATHER_API_KEY is missing.\n"
                "Please export your key and restart the application."
            )

        self.api_client = WeatherAPIClient(api_key=api_key or "DUMMY_KEY")
        self.current_unit = "C"  # 'C' or 'F'
        self.cached_current_data: Optional[Dict[str, Any]] = None
        self.cached_forecast_data: Optional[Dict[str, Any]] = None
        self.cached_icons: List[bytes] = []

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize and assemble GUI elements."""
        self.setWindowTitle("Professional Python Weather Dashboard")
        self.setFixedSize(700, 750)
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475A;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #CDD6F4;
            }
            QPushButton {
                background-color: #89B4FA;
                color: #11111B;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #B4BEFE;
            }
            QPushButton:disabled {
                background-color: #45475A;
                color: #A6ADC8;
            }
            QFrame {
                background-color: #181825;
                border-radius: 12px;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Search Bar & Controls
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter City or ZIP Code (e.g. London, 10001)...")
        self.search_input.returnPressed.connect(self.handle_search)

        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.handle_search)

        self.btn_auto_loc = QPushButton("📍 Auto")
        self.btn_auto_loc.setToolTip("Detect Location via IP")
        self.btn_auto_loc.clicked.connect(self.handle_auto_location)

        self.btn_unit_toggle = QPushButton("°C / °F")
        self.btn_unit_toggle.setCheckable(True)
        self.btn_unit_toggle.clicked.connect(self.toggle_units)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_search)
        search_layout.addWidget(self.btn_auto_loc)
        search_layout.addWidget(self.btn_unit_toggle)

        # 2. Current Weather Panel
        self.current_frame = QFrame()
        current_layout = QVBoxLayout()
        current_layout.setContentsMargins(20, 20, 20, 20)

        self.lbl_city = QLabel("Search a city or use Auto-location")
        self.lbl_city.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_city.setAlignment(Qt.AlignCenter)

        middle_current_layout = QHBoxLayout()
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(100, 100)
        self.lbl_icon.setScaledContents(True)

        self.lbl_temp = QLabel("-- °C")
        self.lbl_temp.setFont(QFont("Segoe UI", 36, QFont.Bold))

        middle_current_layout.addStretch()
        middle_current_layout.addWidget(self.lbl_icon)
        middle_current_layout.addWidget(self.lbl_temp)
        middle_current_layout.addStretch()

        self.lbl_details = QLabel("Condition: -- | Humidity: --% | Wind: -- m/s")
        self.lbl_details.setFont(QFont("Segoe UI", 11))
        self.lbl_details.setAlignment(Qt.AlignCenter)

        current_layout.addWidget(self.lbl_city)
        current_layout.addLayout(middle_current_layout)
        current_layout.addWidget(self.lbl_details)
        self.current_frame.setLayout(current_layout)

        # 3. Hourly Forecast Panel (Next 6 periods)
        self.hourly_frame = QFrame()
        hourly_vlayout = QVBoxLayout()
        hourly_title = QLabel("Hourly Forecast (Next 18 Hours)")
        hourly_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hourly_vlayout.addWidget(hourly_title)

        self.hourly_hlayout = QHBoxLayout()
        self.hourly_widgets: List[Dict[str, QLabel]] = []

        for _ in range(6):
            card = QFrame()
            card.setStyleSheet("background-color: #313244;")
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(5, 5, 5, 5)

            lbl_time = QLabel("--:--")
            lbl_time.setAlignment(Qt.AlignCenter)
            lbl_ico = QLabel()
            lbl_ico.setFixedSize(40, 40)
            lbl_ico.setScaledContents(True)
            lbl_ico.setAlignment(Qt.AlignCenter)
            lbl_tmp = QLabel("--°")
            lbl_tmp.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(lbl_time)
            card_layout.addWidget(lbl_ico, alignment=Qt.AlignCenter)
            card_layout.addWidget(lbl_tmp)
            card.setLayout(card_layout)

            self.hourly_hlayout.addWidget(card)
            self.hourly_widgets.append({"time": lbl_time, "icon": lbl_ico, "temp": lbl_tmp})

        hourly_vlayout.addLayout(self.hourly_hlayout)
        self.hourly_frame.setLayout(hourly_vlayout)

        # 4. Daily Forecast Panel (5 Days)
        self.daily_frame = QFrame()
        daily_vlayout = QVBoxLayout()
        daily_title = QLabel("5-Day Daily Outlook")
        daily_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        daily_vlayout.addWidget(daily_title)

        self.daily_widgets: List[Dict[str, QLabel]] = []
        for _ in range(5):
            row = QHBoxLayout()
            lbl_day = QLabel("---")
            lbl_desc = QLabel("---")
            lbl_desc.setAlignment(Qt.AlignCenter)
            lbl_temp_range = QLabel("--° / --°")
            lbl_temp_range.setAlignment(Qt.AlignRight)

            row.addWidget(lbl_day, stretch=2)
            row.addWidget(lbl_desc, stretch=3)
            row.addWidget(lbl_temp_range, stretch=2)

            daily_vlayout.addLayout(row)
            self.daily_widgets.append({"day": lbl_day, "desc": lbl_desc, "temp": lbl_temp_range})

        self.daily_frame.setLayout(daily_vlayout)

        # Build Main Layout
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.current_frame)
        main_layout.addWidget(self.hourly_frame)
        main_layout.addWidget(self.daily_frame)
        self.setLayout(main_layout)

    # -------------------------------------------------------------------
    # Unit Helper Functions
    # -------------------------------------------------------------------
    def _convert_temp(self, celsius_val: float) -> float:
        """Convert Celsius to Fahrenheit if unit is F, else return C."""
        if self.current_unit == "F":
            return (celsius_val * 9 / 5) + 32
        return celsius_val

    def toggle_units(self) -> None:
        """Dynamically convert temperature labels without re-fetching API data."""
        self.current_unit = "F" if self.btn_unit_toggle.isChecked() else "C"
        if self.cached_current_data and self.cached_forecast_data:
            self.render_weather(self.cached_current_data, self.cached_forecast_data, self.cached_icons)

    # -------------------------------------------------------------------
    # Event Handlers & Async Threading Trigger
    # -------------------------------------------------------------------
    def handle_search(self) -> None:
        """Trigger search on user input."""
        query = self.search_input.text().strip()
        if not query:
            self.show_error_popup("Input Error", "Please enter a valid City Name or ZIP Code.")
            return
        self.start_async_fetch(query=query)

    def handle_auto_location(self) -> None:
        """Trigger search using auto-location."""
        self.start_async_fetch(auto_detect=True)

    def start_async_fetch(self, query: Optional[str] = None, auto_detect: bool = False) -> None:
        """Instantiate and run worker thread for non-blocking UI network operations."""
        self.toggle_ui_controls(enabled=False)

        self.worker = WeatherWorker(self.api_client, query=query, auto_detect=auto_detect)
        self.worker.data_fetched.connect(self.on_data_loaded)
        self.worker.error_occurred.connect(self.on_data_error)
        self.worker.finished.connect(lambda: self.toggle_ui_controls(enabled=True))
        self.worker.start()

    def toggle_ui_controls(self, enabled: bool) -> None:
        """Enable or disable search controls during processing."""
        self.btn_search.setEnabled(enabled)
        self.btn_auto_loc.setEnabled(enabled)
        self.search_input.setEnabled(enabled)

    # -------------------------------------------------------------------
    # Rendering & Data Handlers
    # -------------------------------------------------------------------
    def on_data_loaded(self, current_data: dict, forecast_data: dict, icons: list) -> None:
        """Cache data and trigger rendering."""
        self.cached_current_data = current_data
        self.cached_forecast_data = forecast_data
        self.cached_icons = icons
        self.render_weather(current_data, forecast_data, icons)

    def on_data_error(self, message: str) -> None:
        """Handle errors returned from worker thread."""
        self.show_error_popup("Weather Data Error", message)

    def show_error_popup(self, title: str, message: str) -> None:
        """Modal Dialog error display inside the GUI."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStyleSheet("QLabel{ color: #CDD6F4; } QPushButton{ background-color: #89B4FA; color: #11111B; }")
        msg.exec_()

    def render_weather(self, current: dict, forecast: dict, icons: list) -> None:
        """Update GUI widgets with calculated values and image pixmaps."""
        unit_suffix = f"°{self.current_unit}"

        # 1. Current Weather Render
        city_name = current.get("name", "Unknown")
        country = current.get("sys", {}).get("country", "")
        temp_c = current["main"]["temp"]
        humidity = current["main"]["humidity"]
        wind = current["wind"]["speed"]
        desc = current["weather"][0]["description"].title()

        display_temp = self._convert_temp(temp_c)
        self.lbl_city.setText(f"{city_name}, {country}")
        self.lbl_temp.setText(f"{display_temp:.1f} {unit_suffix}")
        self.lbl_details.setText(f"{desc} | Humidity: {humidity}% | Wind: {wind} m/s")

        if icons and len(icons[0]) > 0:
            pixmap = QPixmap()
            pixmap.loadFromData(icons[0])
            self.lbl_icon.setPixmap(pixmap)

        # 2. Hourly Forecast Render (6 steps)
        forecast_items = forecast.get("list", [])
        for idx, widget_group in enumerate(self.hourly_widgets):
            if idx < len(forecast_items):
                item = forecast_items[idx]
                dt = datetime.fromtimestamp(item["dt"])
                h_temp = self._convert_temp(item["main"]["temp"])

                widget_group["time"].setText(dt.strftime("%I %p"))
                widget_group["temp"].setText(f"{h_temp:.0f}{unit_suffix}")

                icon_idx = idx + 1
                if icon_idx < len(icons) and len(icons[icon_idx]) > 0:
                    pixmap = QPixmap()
                    pixmap.loadFromData(icons[icon_idx])
                    widget_group["icon"].setPixmap(pixmap)

        # 3. Daily Forecast Render (Group 3-hour forecasts by day)
        daily_groups: Dict[str, List[float]] = {}
        daily_descriptions: Dict[str, str] = {}

        for item in forecast_items:
            day_str = datetime.fromtimestamp(item["dt"]).strftime("%A")
            daily_groups.setdefault(day_str, []).append(item["main"]["temp"])
            if day_str not in daily_descriptions:
                daily_descriptions[day_str] = item["weather"][0]["description"].title()

        for idx, (day, temps) in enumerate(daily_groups.items()):
            if idx >= 5:
                break
            min_temp = self._convert_temp(min(temps))
            max_temp = self._convert_temp(max(temps))

            self.daily_widgets[idx]["day"].setText(day)
            self.daily_widgets[idx]["desc"].setText(daily_descriptions[day])
            self.daily_widgets[idx]["temp"].setText(f"{min_temp:.0f}° / {max_temp:.0f}{unit_suffix}")


# -------------------------------------------------------------------
# Application Entry Point
# -------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = WeatherAppUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()