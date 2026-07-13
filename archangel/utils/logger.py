"""Logger initialisation and configuration."""

import logging
import sys
from pathlib import Path


def init_logger(debug: bool = False, log_dir: str | Path = "logs") -> None:
    """Configure the root logger for The Archangel.

    Parameters
    ----------
    debug : bool
        If True, set log level to DEBUG; otherwise INFO.
    log_dir : str or Path
        Directory where log files will be written.
    """
    level = logging.DEBUG if debug else logging.INFO

    # Ensure the log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any pre-existing handlers
    root.handlers.clear()

    # --- Console handler (stderr) ---
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        "%(levelname)-8s %(name)s | %(message)s",
    ))
    root.addHandler(console)

    # --- File handler ---
    log_file = log_path / "archangel.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  |  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(file_handler)
