from pathlib import Path
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QProgressBar, 
    QTextEdit, QMessageBox, QFrame, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon, QFont, QPalette, QColor

from imggen_app.config.settings import Settings, load_settings
from imggen_app.infrastructure.spreadsheet.excel_openpyxl import ExcelHandler
from imggen_app.presentation.qt.worker import ImageWorker
from imggen_app.domain.models import SessionSummary

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Main GUI Window for the application.
    Constructs the single-screen interface using PySide6 widgets.
    Coordinates user input and background worker lifecycle.
    """
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.setup_ui()
        
        # State tracking for user-selected paths
        self.spreadsheet_path: Path | None = None
        self.destination_dir: Path | None = None
        # Reference to the active background thread
        self.worker: ImageWorker | None = None

    def setup_ui(self):
        self.setWindowTitle("Auto Product Image Downloader")
        self.setMinimumSize(800, 600)
        
        # Central Widget and Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Title Section
        title_label = QLabel("Product Image Importer")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 1. Template Section
        template_group = QFrame()
        template_group.setFrameShape(QFrame.StyledPanel)
        template_layout = QHBoxLayout(template_group)
        
        self.btn_download_template = QPushButton("Download Template (.xlsx)")
        self.btn_download_template.clicked.connect(self.on_download_template)
        template_layout.addWidget(QLabel("Step 1: Get the spreadsheet structure:"))
        template_layout.addStretch()
        template_layout.addWidget(self.btn_download_template)
        main_layout.addWidget(template_group)

        # 2. Upload Section
        upload_group = QFrame()
        upload_group.setFrameShape(QFrame.StyledPanel)
        upload_layout = QHBoxLayout(upload_group)
        
        self.btn_upload = QPushButton("Upload Filled Spreadsheet")
        self.btn_upload.clicked.connect(self.on_upload_spreadsheet)
        self.label_upload_status = QLabel("No file selected")
        self.label_upload_status.setStyleSheet("color: gray;")
        
        upload_layout.addWidget(QLabel("Step 2: Select your filled file:"))
        upload_layout.addStretch()
        upload_layout.addWidget(self.label_upload_status)
        upload_layout.addWidget(self.btn_upload)
        main_layout.addWidget(upload_group)

        # 3. Destination Section
        dest_group = QFrame()
        dest_group.setFrameShape(QFrame.StyledPanel)
        dest_layout = QHBoxLayout(dest_group)
        
        self.btn_select_dest = QPushButton("Select Destination Folder")
        self.btn_select_dest.clicked.connect(self.on_select_destination)
        self.label_dest_status = QLabel("No folder selected")
        self.label_dest_status.setStyleSheet("color: gray;")
        
        dest_layout.addWidget(QLabel("Step 3: Choose save location:"))
        dest_layout.addStretch()
        dest_layout.addWidget(self.label_dest_status)
        dest_layout.addWidget(self.btn_select_dest)
        main_layout.addWidget(dest_group)

        # 4. Search Engine Section
        engine_group = QFrame()
        engine_group.setFrameShape(QFrame.StyledPanel)
        engine_layout = QHBoxLayout(engine_group)
        
        self.combo_engine = QComboBox()
        self.combo_engine.addItems(["Yahoo", "Google", "eBay"])
        
        engine_layout.addWidget(QLabel("Step 4: Select Search Engine:"))
        engine_layout.addStretch()
        engine_layout.addWidget(self.combo_engine)
        main_layout.addWidget(engine_group)

        # 5. Generate Section
        gen_layout = QHBoxLayout()
        self.btn_generate = QPushButton("GENERATE IMAGES")
        self.btn_generate.setFixedHeight(50)
        self.btn_generate.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.btn_generate.setStyleSheet("background-color: #0078d4; color: white;")
        self.btn_generate.clicked.connect(self.on_generate)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.on_cancel)
        
        gen_layout.addWidget(self.btn_generate)
        gen_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(gen_layout)

        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        # Log Section
        main_layout.addWidget(QLabel("Activity Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        main_layout.addWidget(self.log_area)

    @Slot()
    def on_download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", "product_image_template.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            try:
                ExcelHandler.create_template(Path(path))
                QMessageBox.information(self, "Success", f"Template saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create template: {e}")

    @Slot()
    def on_upload_spreadsheet(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Spreadsheet", "", "Excel Files (*.xlsx)"
        )
        if path:
            self.spreadsheet_path = Path(path)
            self.label_upload_status.setText(self.spreadsheet_path.name)
            self.label_upload_status.setStyleSheet("color: black; font-weight: bold;")

    @Slot()
    def on_select_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.destination_dir = Path(folder)
            self.label_dest_status.setText(str(self.destination_dir))
            self.label_dest_status.setStyleSheet("color: black; font-weight: bold;")

    @Slot()
    def on_generate(self):
        if not self.spreadsheet_path or not self.destination_dir:
            QMessageBox.warning(self, "Input Required", "Please select both a spreadsheet and a destination folder.")
            return

        try:
            # Load rows to ensure spreadsheet is valid
            rows = list(ExcelHandler.read_rows(self.spreadsheet_path))
            if not rows:
                QMessageBox.warning(self, "Empty Spreadsheet", "No valid product rows found in the spreadsheet.")
                return
            
            # Reset UI
            self.log_area.clear()
            self.progress_bar.setValue(0)
            self.set_ui_enabled(False)
            
            # Start Worker
            self.worker = ImageWorker(self.settings, rows, self.destination_dir, self.combo_engine.currentText())
            self.worker.progress.connect(self.progress_bar.setValue)
            self.worker.log_msg.connect(self.append_log)
            self.worker.finished.connect(self.on_finished)
            self.worker.error.connect(self.on_worker_error)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start processing: {e}")

    @Slot()
    def on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.append_log("[User] Cancellation requested...")
            self.btn_cancel.setEnabled(False)

    def on_finished(self, summary: SessionSummary):
        self.set_ui_enabled(True)
        msg = (
            f"Processing Complete!\n\n"
            f"Total products: {summary.total_rows}\n"
            f"Successful: {summary.successful_rows}\n"
            f"Failed: {summary.failed_rows}\n"
            f"Total images saved: {summary.total_images_saved}"
        )
        if summary.errors:
            msg += f"\n\nFirst few errors:\n" + "\n".join(summary.errors[:5])
            
        QMessageBox.information(self, "Finished", msg)

    def on_worker_error(self, err_msg: str):
        self.set_ui_enabled(True)
        QMessageBox.critical(self, "Worker Error", f"An error occurred in the background thread:\n{err_msg}")

    def set_ui_enabled(self, enabled: bool):
        self.btn_download_template.setEnabled(enabled)
        self.btn_upload.setEnabled(enabled)
        self.btn_select_dest.setEnabled(enabled)
        self.combo_engine.setEnabled(enabled)
        self.btn_generate.setEnabled(enabled)
        self.btn_cancel.setEnabled(not enabled)

    @Slot(str)
    def append_log(self, text: str):
        self.log_area.append(text)
        # Scroll to bottom
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
