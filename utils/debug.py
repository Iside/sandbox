# -*- coding: utf-8 -*-

import colorama
import logging
import os
import sys

SUCCESS = logging.CRITICAL + 1 # You always want to display success

class Formatter(logging.Formatter):

    def __init__(self, fmt=None, datefmt=None, arrow_style="==>"):
        logging.Formatter.__init__(self)
        self._enable_colors = os.isatty(sys.stderr.fileno())
        self._arrow_style = arrow_style
        self._color_table = {
            "DEBUG": colorama.Fore.WHITE + colorama.Style.DIM,
            "INFO": colorama.Fore.BLUE + colorama.Style.BRIGHT,
            "WARNING": colorama.Fore.YELLOW + colorama.Style.BRIGHT,
            "ERROR": colorama.Fore.RED + colorama.Style.BRIGHT,
            "CRITICAL": colorama.Fore.RED + colorama.Style.BRIGHT,
            "SUCCESS": colorama.Fore.GREEN + colorama.Style.BRIGHT
        }

    def format(self, record):
        if self._enable_colors:
            s = "{0}{1}{2} ".format(
                self._color_table.get(record.levelname),
                self._arrow_style,
                colorama.Style.RESET_ALL
            )
        else:
            s = "{0} ".format(self._arrow_style)
        return s + logging.Formatter.format(self, record)


def log_success(msg, *args, **kwargs):
    logging.log(SUCCESS, msg, *args, **kwargs)

def configure_logging(arrow_style, level="DEBUG"):
    logging.addLevelName(SUCCESS, "SUCCESS")
    stderr_format = Formatter(arrow_style=arrow_style)
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(stderr_format)
    root_logger = logging.getLogger()
    root_logger.addHandler(stderr_handler)
    root_logger.setLevel(level)
