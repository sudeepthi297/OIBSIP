"""
Desktop BMI Calculator & Health Tracker
Built with Python 3, Tkinter (ttk), SQLite3, and Matplotlib.

Author: Senior Python Developer
Architecture: Modular (MVC-aligned design pattern)
"""

import sqlite3
import datetime
from typing import List, Tuple, Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ============================================================================
# 1. CORE LOGIC & CALCULATION SERVICE
# ============================================================================

class BMICalculator:
    """Handles BMI calculations, validations, and category evaluations."""

    @staticmethod
    def calculate_bmi(weight_kg: float, height_m: float) -> float:
        """
        Calculates Body Mass Index (BMI).
        Formula: weight (kg) / (height (m)²)
        """
        if height_m <= 0:
            raise ValueError("Height must be greater than 0.")
        return round(weight_kg / (height_m ** 2), 2)

    @staticmethod
    def get_category_and_color(bmi: float) -> Tuple[str, str]:
        """Returns the Health Category name and hex color based on BMI score."""
        if bmi < 18.5:
            return "Underweight", "#3498db"  # Blue
        elif 18.5 <= bmi <= 24.9:
            return "Normal weight", "#2ecc71"  # Green
        elif 25.0 <= bmi <= 29.9:
            return "Overweight", "#f39c12"  # Orange
        else:
            return "Obese", "#e74c3c"  # Red

    @staticmethod
    def validate_inputs(height_cm: str, weight_kg: str) -> Tuple[float, float]:
        """
        Strictly validates numerical input limits:
        - Height: 50 cm to 250 cm (converted to 0.5m - 2.5m)
        - Weight: 10 kg to 300 kg
        """
        try:
            h_val = float(height_cm)
            w_val = float(weight_kg)
        except ValueError:
            raise ValueError("Height and Weight must be valid numeric values.")

        # Height check
        if not (50.0 <= h_val <= 250.0):
            raise ValueError("Height must be between 50 cm and 250 cm (0.5m - 2.5m).")

        # Weight check
        if not (10.0 <= w_val <= 300.0):
            raise ValueError("Weight must be between 10 kg and 300 kg.")

        height_m = h_val / 100.0  # Convert cm to meters
        return height_m, w_val


# ============================================================================
# 2. DATABASE PERSISTENCE LAYER
# ============================================================================

class DatabaseManager:
    """Manages SQLite3 connections, database schema, and CRUD transactions."""

    def __init__(self, db_path: str = "bmi_tracker.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initializes database schema if tables do not exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Users Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL
                    )
                """)
                # BMI Records Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bmi_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        weight REAL NOT NULL,
                        height REAL NOT NULL,
                        bmi REAL NOT NULL,
                        category TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """)
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Database initialization failed: {e}")

    def get_or_create_user(self, name: str) -> int:
        """Fetches existing user ID or creates a new user profile."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("User name cannot be blank.")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(?)", (clean_name,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                cursor.execute("INSERT INTO users (name) VALUES (?)", (clean_name,))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to fetch/create user: {e}")

    def get_all_users(self) -> List[str]:
        """Returns a list of all registered user names."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM users ORDER BY name ASC")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to fetch user list: {e}")

    def add_record(self, user_id: int, weight: float, height: float, bmi: float, category: str) -> None:
        """Persists a new BMI tracking record."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bmi_records (user_id, weight, height, bmi, category, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, weight, height, bmi, category, timestamp))
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to save record: {e}")

    def get_user_records(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieves historical tracking records for a specific user ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT weight, height, bmi, category, timestamp 
                    FROM bmi_records 
                    WHERE user_id = ? 
                    ORDER BY timestamp ASC
                """, (user_id,))
                rows = cursor.fetchall()
                
                return [
                    {
                        "weight": r[0],
                        "height": r[1],
                        "bmi": r[2],
                        "category": r[3],
                        "timestamp": r[4]
                    }
                    for r in rows
                ]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to fetch historical data: {e}")


# ============================================================================
# 3. DATA VISUALIZATION COMPONENT
# ============================================================================

class TrendChart:
    """Manages Matplotlib canvas rendering and threshold annotations."""

    def __init__(self, parent_frame: ttk.Frame):
        self.figure, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.figure.patch.set_facecolor('#f5f6f7')
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def plot_data(self, records: List[Dict[str, Any]], username: str) -> None:
        """Re-draws line chart tracking user BMI over time with reference bands."""
        self.ax.clear()
        self.ax.set_facecolor('#ffffff')

        if not records:
            self.ax.text(0.5, 0.5, f"No historic records found for {username}", 
                         ha='center', va='center', color='#7f8c8d', fontsize=10)
            self.ax.set_axis_off()
            self.canvas.draw()
            return

        self.ax.set_axis_on()
        
        # Format timestamps for X-axis display
        dates = [r["timestamp"].split()[0] + "\n" + r["timestamp"].split()[1][:5] for r in records]
        bmis = [r["bmi"] for r in records]

        # Standard BMI Range Reference Lines & Fills
        self.ax.axhspan(0, 18.5, color='#3498db', alpha=0.10, label='Underweight (<18.5)')
        self.ax.axhspan(18.5, 24.9, color='#2ecc71', alpha=0.15, label='Normal (18.5–24.9)')
        self.ax.axhspan(25.0, 29.9, color='#f39c12', alpha=0.10, label='Overweight (25–29.9)')
        self.ax.axhspan(30.0, max(max(bmis) + 5, 40), color='#e74c3c', alpha=0.10, label='Obese (≥30)')

        # User Trend Line
        self.ax.plot(dates, bmis, marker='o', color='#2c3e50', linewidth=2, markersize=6, label='Your BMI')

        # Formatting
        self.ax.set_title(f"BMI History: {username}", fontsize=11, fontweight='bold', pad=10, color='#2c3e50')
        self.ax.set_ylabel("BMI Score", fontsize=9, color='#2c3e50')
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.tick_params(axis='x', labelsize=8, rotation=0)
        self.ax.tick_params(axis='y', labelsize=8)

        # Compact Legend
        self.ax.legend(loc='upper left', fontsize=7, framealpha=0.8)

        self.figure.tight_layout()
        self.canvas.draw()


# ============================================================================
# 4. GUI APPLICATION LAYER
# ============================================================================

class BMIApp(tk.Tk):
    """Main Application Interface (Tkinter UI Frame)."""

    def __init__(self):
        super().__init__()
        
        self.title("Production-Grade BMI Health Tracker")
        self.geometry("950x620")
        self.minsize(850, 550)

        # Core Services
        self.db = DatabaseManager()
        
        # Style Configuration
        self._setup_styles()
        
        # Build UI Components
        self._build_layout()
        
        # Initial Population
        self.refresh_user_dropdown()

    def _setup_styles(self) -> None:
        """Applies modern clean styling configuration using ttk."""
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Global Colors
        self.configure(bg="#f5f6f7")
        self.style.configure(".", background="#f5f6f7", font=("Segoe UI", 10))
        
        # Label Frames
        self.style.configure("TLabelframe", background="#ffffff", relief="flat")
        self.style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background="#ffffff", foreground="#2c3e50")

        # Custom Button
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#2980b9", foreground="#ffffff")
        self.style.map("Primary.TButton", background=[("active", "#3498db")])

    def _build_layout(self) -> None:
        """Constructs two-pane responsive application interface layout."""
        # Top Header Banner
        header = tk.Frame(self, bg="#2c3e50", height=50)
        header.pack(fill=tk.X, side=tk.TOP)
        header_label = tk.Label(header, text="BMI Health Analytics Suite", bg="#2c3e50", fg="#ffffff", font=("Segoe UI", 14, "bold"))
        header_label.pack(side=tk.LEFT, padx=20, pady=10)

        # Central Split Container
        main_container = ttk.Frame(self, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left Column: Input Forms & Display (Fixed Width Frame)
        left_frame = ttk.LabelFrame(main_container, text=" User Input & Results ", padding=15)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # --- Form Controls ---
        ttk.Label(left_frame, text="User Name / ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.user_combo = ttk.Combobox(left_frame, width=22)
        self.user_combo.grid(row=0, column=1, sticky="w", pady=5)
        self.user_combo.bind("<<ComboboxSelected>>", self._on_user_selected)

        ttk.Label(left_frame, text="Height (cm):").grid(row=1, column=0, sticky="w", pady=5)
        self.height_entry = ttk.Entry(left_frame, width=24)
        self.height_entry.grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(left_frame, text="Weight (kg):").grid(row=2, column=0, sticky="w", pady=5)
        self.weight_entry = ttk.Entry(left_frame, width=24)
        self.weight_entry.grid(row=2, column=1, sticky="w", pady=5)

        # Process Action Button
        calc_btn = ttk.Button(left_frame, text="Calculate & Save", style="Primary.TButton", command=self.on_calculate)
        calc_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(15, 15))
        # --- Dynamic Results Banner ---
        ttk.Separator(left_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)

        self.results_frame = tk.Frame(left_frame, bg="#ecf0f1", bd=1, relief="solid", padx=10,pady=10)
        self.results_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)

        self.bmi_value_label = tk.Label(self.results_frame, text="BMI: --", font=("Segoe UI", 18, "bold"), bg="#ecf0f1", fg="#7f8c8d")
        self.bmi_value_label.pack(pady=(5, 2))

        self.category_badge = tk.Label(self.results_frame, text="Awaiting Input", font=("Segoe UI", 11, "bold"), 
                                       bg="#7f8c8d", fg="#ffffff", padx=12, pady=4)
        self.category_badge.pack(pady=(2, 5))

        # Right Column: Visual Matplotlib Chart
        right_frame = ttk.LabelFrame(main_container, text=" Historical BMI Trend Analysis ", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.chart = TrendChart(right_frame)

    def refresh_user_dropdown(self) -> None:
        """Loads known active user profiles into the dropdown selector."""
        try:
            users = self.db.get_all_users()
            self.user_combo['values'] = users
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_user_selected(self, event: Optional[tk.Event] = None) -> None:
        """Event handler when selecting a user from dropdown menu."""
        user_name = self.user_combo.get().strip()
        if user_name:
            self.load_user_chart(user_name)

    def load_user_chart(self, username: str) -> None:
        """Fetches and displays historical tracking records on the Matplotlib canvas."""
        try:
            user_id = self.db.get_or_create_user(username)
            records = self.db.get_user_records(user_id)
            self.chart.plot_data(records, username)
        except Exception as e:
            messagebox.showerror("Error Loading Data", str(e))

    def on_calculate(self) -> None:
        """Calculates BMI score, validates fields, persists data, and updates UI."""
        username = self.user_combo.get().strip()
        height_str = self.height_entry.get().strip()
        weight_str = self.weight_entry.get().strip()

        # Step 1: Input Validation
        if not username:
            messagebox.showwarning("Validation Error", "Please specify a User Name.")
            return

        try:
            height_m, weight_kg = BMICalculator.validate_inputs(height_str, weight_str)
        except ValueError as err:
            messagebox.showwarning("Validation Error", str(err))
            return

        # Step 2: Compute Results
        try:
            bmi = BMICalculator.calculate_bmi(weight_kg, height_m)
            category, color_hex = BMICalculator.get_category_and_color(bmi)

            # Step 3: Persist to DB
            user_id = self.db.get_or_create_user(username)
            self.db.add_record(user_id, weight_kg, height_m, bmi, category)

            # Step 4: Refresh UI Elements
            self.bmi_value_label.config(text=f"BMI: {bmi:.2f}", fg="#2c3e50")
            self.category_badge.config(text=category.upper(), bg=color_hex, fg="#ffffff")

            # Update Dropdown & Redraw Chart
            self.refresh_user_dropdown()
            self.user_combo.set(username)
            self.load_user_chart(username)

            # Clear Numerical Entry Fields
            self.height_entry.delete(0, tk.END)
            self.weight_entry.delete(0, tk.END)

        except Exception as err:
            messagebox.showerror("Execution Error", f"An unexpected error occurred: {err}")


# ============================================================================
# 5. ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = BMIApp()
    app.mainloop()