"""
Database Management Widget for DrumTracKAI Admin
===============================================
This widget provides database management functionality for the DrumTracKAI Admin application.
"""
import csv
import logging
import os
import sqlite3
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal, Slot, QAbstractTableModel, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableView,
    QComboBox, QGroupBox, QLineEdit, QTextEdit, QFormLayout, QMessageBox,
    QSplitter, QCheckBox, QSpinBox, QHeaderView, QFileDialog, QDialogButtonBox
)

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseTableModel(QAbstractTableModel):
    """Model for displaying database tables in a QTableView"""

    def __init__(self, data=None, headers=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._headers = headers or []
        self._editable = False

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers) if self._headers else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if index.row() < len(self._data) and index.column() < len(self._headers):
                return str(self._data[index.row()][index.column()])

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section < len(self._headers):
            return self._headers[section]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and self._editable:
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        flags = super().flags(index)
        if self._editable:
            flags |= Qt.ItemIsEditable
        return flags

    def setEditable(self, editable):
        self._editable = editable

    def updateData(self, data, headers=None):
        self.beginResetModel()
        self._data = data
        if headers:
            self._headers = headers
        self.endResetModel()


class DatabaseWidget(QWidget):
    """Widget for managing database connections and performing operations"""

    initialization_complete = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing DatabaseWidget")
        self._initialization_complete = False
        self.conn = None
        self.current_table = None
        self.event_bus = None

        self._setup_ui()
        self._connect_signals()

        # Set initialization flag
        self._initialization_complete = True
        self.initialization_complete.emit()
        logger.info("DatabaseWidget initialization complete")

    def _setup_ui(self):
        """Set up the user interface"""
        logger.info("Setting up DatabaseWidget UI")

        main_layout = QVBoxLayout()

        # Database connection section
        connection_group = QGroupBox("Database Connection")
        connection_layout = QHBoxLayout()

        self.db_path_edit = QLineEdit()
        self.db_path_edit.setPlaceholderText("Database path")
        self.db_path_edit.setReadOnly(True)

        self.browse_button = QPushButton("Browse")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)

        connection_layout.addWidget(self.db_path_edit)
        connection_layout.addWidget(self.browse_button)
        connection_layout.addWidget(self.connect_button)
        connection_layout.addWidget(self.disconnect_button)
        connection_group.setLayout(connection_layout)

        # Table selection section
        tables_group = QGroupBox("Tables")
        tables_layout = QVBoxLayout()

        self.tables_combo = QComboBox()
        self.refresh_tables_button = QPushButton("Refresh Tables")

        tables_header_layout = QHBoxLayout()
        tables_header_layout.addWidget(self.tables_combo)
        tables_header_layout.addWidget(self.refresh_tables_button)

        tables_layout.addLayout(tables_header_layout)
        tables_group.setLayout(tables_layout)

        # Table view section
        view_group = QGroupBox("Data View")
        view_layout = QVBoxLayout()

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)

        view_controls_layout = QHBoxLayout()
        self.edit_mode_checkbox = QCheckBox("Edit Mode")
        self.save_changes_button = QPushButton("Save Changes")
        self.save_changes_button.setEnabled(False)
        view_controls_layout.addWidget(self.edit_mode_checkbox)
        view_controls_layout.addWidget(self.save_changes_button)
        view_controls_layout.addStretch()

        view_layout.addWidget(self.table_view)
        view_layout.addLayout(view_controls_layout)
        view_group.setLayout(view_layout)

        # SQL Query section
        query_group = QGroupBox("SQL Query")
        query_layout = QVBoxLayout()

        self.query_edit = QTextEdit()
        self.query_edit.setPlaceholderText("Enter SQL query here...")
        self.execute_button = QPushButton("Execute Query")

        query_layout.addWidget(self.query_edit)
        query_layout.addWidget(self.execute_button)
        query_group.setLayout(query_layout)

        # Database operations section
        operations_group = QGroupBox("Database Operations")
        operations_layout = QHBoxLayout()

        self.backup_button = QPushButton("Backup")
        self.restore_button = QPushButton("Restore")
        self.export_button = QPushButton("Export to CSV")
        self.import_button = QPushButton("Import from CSV")
        self.stats_button = QPushButton("Database Stats")

        operations_layout.addWidget(self.backup_button)
        operations_layout.addWidget(self.restore_button)
        operations_layout.addWidget(self.export_button)
        operations_layout.addWidget(self.import_button)
        operations_layout.addWidget(self.stats_button)
        operations_group.setLayout(operations_layout)

        # Status bar
        self.status_bar = QLabel("Ready")

        # Add all sections to main layout
        main_layout.addWidget(connection_group)
        main_layout.addWidget(tables_group)
        main_layout.addWidget(view_group, 3)  # Give more stretch to the view
        main_layout.addWidget(query_group)
        main_layout.addWidget(operations_group)
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connect UI signals to slots"""
        logger.info("Connecting DatabaseWidget signals")

        # Connection controls
        self.browse_button.clicked.connect(self._on_browse)
        self.connect_button.clicked.connect(self._on_connect)
        self.disconnect_button.clicked.connect(self._on_disconnect)

        # Table selection
        self.tables_combo.currentTextChanged.connect(self._on_table_selected)
        self.refresh_tables_button.clicked.connect(self._populate_table_combo)

        # Edit mode
        self.edit_mode_checkbox.stateChanged.connect(self._toggle_edit_mode)

        # Query execution
        self.execute_button.clicked.connect(self._execute_query)

        # Table operations
        self.save_changes_button.clicked.connect(self._on_save_changes)

        # Database operations
        self.backup_button.clicked.connect(self._on_backup)
        self.restore_button.clicked.connect(self._on_restore)
        self.export_button.clicked.connect(self._on_export)
        self.import_button.clicked.connect(self._on_import)
        self.stats_button.clicked.connect(self._update_statistics)

    def _on_browse(self):
        """Open file dialog to browse for database file"""
        db_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SQLite Database",
            os.path.join(os.getcwd(), "..", "database"),
            "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*.*)"
        )

        if db_path:
            self.db_path_edit.setText(db_path)

    def _on_connect(self):
        """Connect to the selected database"""
        db_path = self.db_path_edit.text()
        if not db_path:
            QMessageBox.warning(self, "No Database Selected", "Please select a database file first.")
            return

        try:
            # Close existing connection if any
            if self.conn:
                self.conn.close()

            # Connect to database
            self.conn = sqlite3.connect(db_path)

            # Update UI
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.status_bar.setText(f"Connected to {os.path.basename(db_path)}")

            # Populate tables
            self._populate_table_combo()

            # Enable database operations
            self.backup_button.setEnabled(True)
            self.restore_button.setEnabled(True)
            self.export_button.setEnabled(True)
            self.import_button.setEnabled(True)
            self.stats_button.setEnabled(True)
            self.execute_button.setEnabled(True)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(e)}")
            self.status_bar.setText("Connection failed")
            logger.error(f"Database connection error: {str(e)}")

    def _on_disconnect(self):
        """Disconnect from the current database"""
        if self.conn:
            self.conn.close()
            self.conn = None

            # Update UI
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.status_bar.setText("Disconnected")

            # Clear tables
            self.tables_combo.clear()

            # Clear table view
            self.table_view.setModel(None)

            # Disable database operations
            self.backup_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.import_button.setEnabled(False)
            self.stats_button.setEnabled(False)
            self.execute_button.setEnabled(False)

    def _populate_table_combo(self):
        """Populate the tables combo box with available tables"""
        self.tables_combo.clear()

        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            # Get list of tables from sqlite_master
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                self.tables_combo.addItem(table)
            self.status_bar.setText(f"Found {len(tables)} tables")

        except sqlite3.Error as e:
            self.status_bar.setText(f"Error loading tables: {str(e)}")
            logger.error(f"Error loading tables: {str(e)}")

    def _on_table_selected(self, table_name):
        """Handle table selection change"""
        if not table_name:
            return

        self.current_table = table_name
        self._load_table_data(table_name)

    def _load_table_data(self, table_name):
        """Load data for the selected table"""
        if not self.conn or not table_name:
            return

        try:
            # Get table schema
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            schema = cursor.fetchall()
            headers = [col[1] for col in schema]

            # Get data
            cursor.execute(f"SELECT * FROM {table_name}")
            data = cursor.fetchall()

            # Create and set model
            model = DatabaseTableModel(data, headers, self)
            self.table_view.setModel(model)

            # Resize columns to content
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

            # Update status
            self.status_bar.setText(f"Loaded {len(data)} rows from {table_name}")

        except sqlite3.Error as e:
            self.status_bar.setText(f"Error loading data: {str(e)}")
            logger.error(f"Error loading table data: {str(e)}")

    def _toggle_edit_mode(self, state):
        """Toggle edit mode for the table view"""
        if not self.table_view.model():
            return

        is_editable = state == Qt.Checked
        self.table_view.model().setEditable(is_editable)
        self.save_changes_button.setEnabled(is_editable)

        if is_editable:
            self.status_bar.setText("Edit mode enabled - you can now modify cells")
        else:
            self.status_bar.setText("Edit mode disabled")

    def _execute_query(self):
        """Execute the SQL query in the query edit box"""
        query = self.query_edit.toPlainText().strip()

        if not self.conn or not query:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(query)

            # If query returns data, display it
            if query.lower().startswith("select") or query.lower().startswith("pragma"):
                data = cursor.fetchall()

                # Get column names
                headers = [description[0] for description in cursor.description] if cursor.description else []

                # Create and set model
                model = DatabaseTableModel(data, headers, self)
                self.table_view.setModel(model)

                # Resize columns to content
                self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

                self.status_bar.setText(f"Query returned {len(data)} rows")
            else:
                # For non-SELECT queries, commit changes and show row count
                self.conn.commit()
                self.status_bar.setText(f"Query executed successfully. {cursor.rowcount if cursor.rowcount >= 0 else 'Unknown'} rows affected.")

                # Refresh table data if we're looking at the affected table
                if self.current_table and (self.current_table.lower() in query.lower()):
                    self._load_table_data(self.current_table)

        except sqlite3.Error as e:
            QMessageBox.warning(self, "Query Error", f"Error executing query: {str(e)}")
            self.status_bar.setText(f"Query error: {str(e)}")
            logger.error(f"Error executing query: {str(e)}")
            logger.debug(f"Failed query was: {query}")

    def _on_backup(self):
        """Handle backup button click"""
        if not self.conn:
            QMessageBox.warning(self, "No Connection", "Please connect to a database first.")
            return

        db_path = self.db_path_edit.text()
        if not db_path:
            return

        # Get backup file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_backup_name = f"{os.path.basename(db_path)}.{timestamp}.backup"
        backup_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Database Backup",
            os.path.join(os.path.dirname(db_path), default_backup_name),
            "SQLite Backup (*.backup);;All Files (*.*)"
        )

        if not backup_path:
            return

        try:
            # Disconnect to ensure all changes are written
            self._on_disconnect()

            # Copy the database file
            import shutil
            shutil.copy2(db_path, backup_path)

            # Reconnect
            self.db_path_edit.setText(db_path)
            self._on_connect()

            QMessageBox.information(self, "Backup Complete", f"Database backed up to:\n{backup_path}")
            self.status_bar.setText(f"Backup saved to: {os.path.basename(backup_path)}")

        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Failed to create backup: {str(e)}")
            self.status_bar.setText("Backup failed")
            logger.error(f"Database backup error: {str(e)}")

            # Try to reconnect
            self.db_path_edit.setText(db_path)
            self._on_connect()

    def _on_restore(self):
        """Handle restore button click"""
        # Get backup file
        backup_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            os.path.dirname(self.db_path_edit.text()) if self.db_path_edit.text() else "",
            "SQLite Backup (*.backup);;SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*.*)"
        )

        if not backup_path:
            return

        # Get destination path
        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Restore To",
            self.db_path_edit.text() if self.db_path_edit.text() else "",
            "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*.*)"
        )

        if not dest_path:
            return

        # Confirm overwrite if file exists
        if os.path.exists(dest_path):
            reply = QMessageBox.question(
                self,
                "Confirm Overwrite",
                f"The file {dest_path} already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        try:
            # Disconnect if connected
            if self.conn:
                self._on_disconnect()

            # Copy backup to destination
            import shutil
            shutil.copy2(backup_path, dest_path)

            # Connect to restored database
            self.db_path_edit.setText(dest_path)
            self._on_connect()

            QMessageBox.information(self, "Restore Complete", f"Database restored to:\n{dest_path}")
            self.status_bar.setText(f"Restored from {os.path.basename(backup_path)}")

        except Exception as e:
            QMessageBox.critical(self, "Restore Error", f"Failed to restore database: {str(e)}")
            self.status_bar.setText("Restore failed")
            logger.error(f"Database restore error: {str(e)}")

    def _on_export(self):
        """Handle export button click"""
        if not self.conn or not self.current_table:
            QMessageBox.warning(self, "No Table Selected", "Please select a table to export.")
            return

        # Get export file path
        default_export_name = f"{self.current_table}.csv"
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            default_export_name,
            "CSV Files (*.csv);;All Files (*.*)"
        )

        if not export_path:
            return

        try:
            cursor = self.conn.cursor()

            # Get table data
            cursor.execute(f"SELECT * FROM {self.current_table}")
            rows = cursor.fetchall()

            # Get column names
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = [column[1] for column in cursor.fetchall()]

            # Write to CSV
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)  # Write header
                writer.writerows(rows)  # Write data

            QMessageBox.information(self, "Export Complete", f"Table exported to:\n{export_path}")
            self.status_bar.setText(f"Exported {len(rows)} rows to {os.path.basename(export_path)}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export table: {str(e)}")
            self.status_bar.setText("Export failed")
            logger.error(f"Table export error: {str(e)}")

    def _on_import(self):
        """Handle import button click"""
        if not self.conn:
            QMessageBox.warning(self, "No Connection", "Please connect to a database first.")
            return

        # Get import file
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import from CSV",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )

        if not import_path:
            return

        # Get target table name
        default_table = os.path.splitext(os.path.basename(import_path))[0]
        table_name, ok = QInputDialog.getText(
            self,
            "Target Table",
            "Enter table name (existing table will be replaced):",
            text=default_table
        )

        if not ok or not table_name:
            return

        try:
            # Read CSV file
            with open(import_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Read header row
                data = list(reader)  # Read data rows

            cursor = self.conn.cursor()

            # Drop existing table if it exists
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Create new table with columns from CSV header
            columns = [f"\"{h}\" TEXT" for h in headers]
            create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
            cursor.execute(create_sql)

            # Insert data
            placeholders = ', '.join(['?'] * len(headers))
            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
            cursor.executemany(insert_sql, data)

            self.conn.commit()

            # Refresh tables list
            self._populate_table_combo()

            # Select the newly imported table
            index = self.tables_combo.findText(table_name)
            if index >= 0:
                self.tables_combo.setCurrentIndex(index)

            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(data)} rows into table '{table_name}'"
            )
            self.status_bar.setText(f"Imported {len(data)} rows to {table_name}")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import data: {str(e)}")
            self.status_bar.setText("Import failed")
            logger.error(f"CSV import error: {str(e)}")

    def _update_statistics(self):
        """Display database statistics"""
        if not self.conn:
            return

        stats = {}
        try:
            cursor = self.conn.cursor()

            # Get table count
            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
            stats["Tables"] = cursor.fetchone()[0]

            # Get table statistics
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"SELECT count(*) FROM {table}")
                stats[f"{table} rows"] = cursor.fetchone()[0]

            # Database file size
            db_path = self.db_path_edit.text()
            if db_path and os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} bytes"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes/1024:.2f} KB"
                else:
                    size_str = f"{size_bytes/(1024*1024):.2f} MB"
                stats["Database Size"] = size_str

            # Display statistics in a message box
            stats_text = "\n".join([f"{k}: {v}" for k, v in stats.items()])
            QMessageBox.information(self, "Database Statistics", stats_text)
            self.status_bar.setText("Statistics updated")

        except Exception as e:
            QMessageBox.warning(self, "Statistics Error", f"Error getting statistics: {str(e)}")
            self.status_bar.setText("Error getting statistics")
            logger.error(f"Error getting database statistics: {str(e)}")

    def _on_save_changes(self):
        """Save changes to the database"""
        if not self.conn or not self.current_table or not self.table_view.model():
            return

        try:
            model = self.table_view.model()
            data = model._data
            headers = model._headers

            # Create a temporary table for the new data
            temp_table = f"temp_{self.current_table}"
            cursor = self.conn.cursor()

            # Drop temp table if it exists
            cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")

            # Get original table schema
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{self.current_table}'")
            original_schema = cursor.fetchone()[0]
            temp_schema = original_schema.replace(self.current_table, temp_table, 1)

            # Create temp table with same schema
            cursor.execute(temp_schema)

            # Insert updated data
            placeholders = ', '.join(['?'] * len(headers))
            insert_sql = f"INSERT INTO {temp_table} VALUES ({placeholders})"
            cursor.executemany(insert_sql, data)

            # Begin transaction
            self.conn.execute("BEGIN TRANSACTION")

            # Replace original table with temp table
            cursor.execute(f"DROP TABLE {self.current_table}")
            cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {self.current_table}")

            # Commit transaction
            self.conn.commit()

            # Reload data to refresh view
            self._load_table_data(self.current_table)

            # Disable edit mode
            self.edit_mode_checkbox.setChecked(False)

            QMessageBox.information(self, "Save Complete", "Changes saved successfully.")
            self.status_bar.setText("Changes saved")

        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            QMessageBox.critical(self, "Save Error", f"Failed to save changes: {str(e)}")
            self.status_bar.setText("Save failed")
            logger.error(f"Error saving table changes: {str(e)}")
            
    def _update_ui_state(self, connected=False):
        """Update UI state based on connection status"""
        self.tables_combo.setEnabled(connected)
        self.query_edit.setEnabled(connected)
        self.execute_button.setEnabled(connected)
        self.edit_mode_checkbox.setEnabled(connected)
        self.backup_button.setEnabled(connected)
        self.restore_button.setEnabled(connected)
        self.export_button.setEnabled(connected)
        self.import_button.setEnabled(connected)
        self.stats_button.setEnabled(connected)

    def set_event_bus(self, event_bus):
        """Set the event bus for communication"""
        self.event_bus = event_bus
        logger.info("Event bus connected to DatabaseWidget")
        
    def _on_import(self):
        """Handle CSV import into current table"""
        if not self.conn or not self.current_table:
            QMessageBox.warning(self, "No Table Selected", "Please connect to a database and select a table first.")
            return
            
        csv_file, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File to Import", "", "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not csv_file:
            return
            
        try:
            self.status_bar.setText(f"Importing data from {os.path.basename(csv_file)}...")
            
            # Read CSV file
            with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Read headers
                data = list(reader)     # Read data
                
            # Confirm import
            reply = QMessageBox.question(
                self, 
                "Confirm Import",
                f"Import {len(data)} rows into {self.current_table}? This will replace the current view.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
                
            # Update the model with new data
            model = self.table_view.model()
            if model:
                model.beginResetModel()
                model._headers = headers
                model._data = data
                model.endResetModel()
                
                self.table_view.resizeColumnsToContents()
                self.status_bar.setText(f"Imported {len(data)} rows from {os.path.basename(csv_file)}")
                
                # Enable edit mode for the imported data
                if not self.edit_mode_checkbox.isChecked():
                    self.edit_mode_checkbox.setChecked(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV: {str(e)}")
            self.status_bar.setText("Import failed")
            logger.error(f"Error importing CSV: {str(e)}")
            return
    def _on_clean(self):
        """Handle clean button click"""
        if not self.conn:
            QMessageBox.warning(self, "No Connection", "Please connect to a database first.")
            return
            
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Database Cleanup",
            "This will optimize and vacuum the database. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Execute VACUUM to clean the database
            self.conn.execute("VACUUM")
            self.conn.execute("PRAGMA optimize")
            
            QMessageBox.information(self, "Cleanup Complete", "Database cleanup completed successfully.")
            self.status_bar.setText("Cleanup completed")
            
            # Update statistics
            self._update_statistics()
            
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Cleanup Error", f"Failed to clean database: {str(e)}")
            self.status_bar.setText("Cleanup failed")
            logger.error(f"Error cleaning database: {str(e)}")
    
    def _on_add_row(self):
        """Add a new row to the table"""
        if not self.conn or not self.current_table or not self.table_view.model():
            return
            
        try:
            model = self.table_view.model()
            data = list(model._data)
            new_row = [''] * len(model._headers)
            data.append(new_row)
            model.updateData(data)
            self.status_bar.setText("New row added - edit values and save changes when done")
            
            # Enable edit mode if not already enabled
            if not self.edit_mode_checkbox.isChecked():
                self.edit_mode_checkbox.setChecked(True)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add row: {str(e)}")
            logger.error(f"Error adding row: {str(e)}")
            
    def _on_delete_row(self):
        """Delete selected row from the table"""
        if not self.conn or not self.current_table or not self.table_view.model():
            return
            
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one row to delete.")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected)} row(s)? This cannot be undone until you save changes.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            model = self.table_view.model()
            data = list(model._data)
            
            # Get indices to delete (in descending order to avoid index shifts)
            rows_to_delete = sorted([idx.row() for idx in selected], reverse=True)
            
            # Remove rows
            for row in rows_to_delete:
                if row < len(data):
                    del data[row]
                    
            model.updateData(data)
            self.status_bar.setText(f"Deleted {len(rows_to_delete)} row(s) - remember to save changes")
            
            # Enable edit mode if not already enabled
            if not self.edit_mode_checkbox.isChecked():
                self.edit_mode_checkbox.setChecked(True)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete row(s): {str(e)}")
            logger.error(f"Error deleting row(s): {str(e)}")
    
    def _update_statistics(self):
        """Update database statistics"""
        try:
            # Placeholder - would get actual statistics from database
            stats = {
                "Total Tables": 4,
                "Drummers": 24,
                "DrumBeats": 150,
                "Audio Samples": 342,
                "Database Size": "1.2 GB",
                "Last Backup": "Never",
            }
            
            # Format and display stats
            stats_text = "Database Statistics:\n\n"
            for key, value in stats.items():
                stats_text += f"{key}: {value}\n"
                
            self.stats_text.setText(stats_text)
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def _on_add_row(self):
        """Add a new row to the table"""
        current_row_count = self.data_table.rowCount()
        self.data_table.insertRow(current_row_count)
        
        # Add empty cells
        for col in range(self.data_table.columnCount()):
            self.data_table.setItem(current_row_count, col, QTableWidgetItem(""))
    
    def _on_delete_row(self):
        """Delete selected row from the table"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
            
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a row to delete")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_rows)} row(s)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Delete rows in reverse order to avoid index shifting
        for row in sorted(selected_rows, reverse=True):
            self.data_table.removeRow(row)
            
        self.status_label.setText(f"Deleted {len(selected_rows)} row(s)")
    
    def _on_save_changes(self):
        """Save changes to the database"""
        self.status_label.setText("Save not implemented")
        QMessageBox.information(self, "Not Implemented", "Save functionality is not yet implemented")
