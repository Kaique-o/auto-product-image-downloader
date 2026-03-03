import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from imggen_app.config.settings import load_settings, Settings
from imggen_app.config.logging_config import configure_logging
from imggen_app.presentation.qt.main_window import MainWindow
from imggen_app.presentation.qt.qt_logging import QtSignalingHandler
from imggen_app.domain.exceptions import ConfigError

def main():
    """
    Main entry point for the Auto Product Image Downloader application.
    Initializes the Qt application, logging, and the main window.
    """
    # 1. Initialize the Qt Application instance
    app = QApplication(sys.argv)
    app.setApplicationName("Auto Product Image Downloader")
    
    # 2. Setup Logging and Configuration
    # We use a signaling handler to pipe logs into the GUI text area safely
    ui_log_handler = QtSignalingHandler()
    try:
        # Load settings from .env file and environment variables
        settings = load_settings()
        # Configure file, console, and UI logging handlers
        configure_logging(log_level=settings.log_level, ui_handler=ui_log_handler)
    except ConfigError as e:
        # Show a critical error if configuration is missing (e.g. API Key)
        QMessageBox.critical(None, "Configuration Error", str(e))
        sys.exit(1)
    except Exception as e:
        # Fallback for unexpected startup errors
        print(f"Failed to start: {e}")
        sys.exit(1)

    # 3. Create and Show the Main Window
    # The window needs the settings to coordinate the business logic
    window = MainWindow(settings)
    
    # Connect the UI log handler's signal to the window's text area slot
    ui_log_handler.log_signal.connect(window.append_log)
    
    window.show()
    
    # 4. Start the Application Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
