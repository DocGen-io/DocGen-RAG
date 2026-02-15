import logging
import sys

class DocGenLogger:
    def __init__(self, name: str = "DocGen", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Critical: Prevent duplicate logs if the logger is initialized twice
        if not self.logger.handlers:
            self._setup_handler()

    def _setup_handler(self):
        # StreamHandler for console output
        handler = logging.StreamHandler(sys.stdout)
        
        # Custom Formatter: We keep the basic info here, 
        # and handle the "Big Box" styling in our methods
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s : %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _format_box(self, label: str, location: str, msg: str) -> str:
        """Internal helper to create your visual separators."""
        loc_str = f" at {location}" if location else ""
        border = "ـ" * 60
        return f"\n{label.upper()}{loc_str} \t {msg}\n"

    def error(self, msg: str, location: str = ""):
        self.logger.error(self._format_box("Error", location, msg))

    def info(self, msg: str, location: str = ""):
        self.logger.info(self._format_box("Info", location, msg))

    def warning(self, msg: str, location: str = ""):
        self.logger.warning(self._format_box("Warning", location, msg))

    def debug(self, msg: str, location: str = ""):
        self.logger.debug(self._format_box("Debug", location, msg))