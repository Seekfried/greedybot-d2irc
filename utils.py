import logging
import os
import sys
from ipaddress import ip_address, IPv4Address, IPv6Address

class _ColourFormatter(logging.Formatter):

    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output

def is_docker() -> bool:
    path = '/proc/self/cgroup'
    return os.path.exists('/.dockerenv') or (os.path.isfile(path) and any('docker' in line for line in open(path)))


def stream_supports_colour(stream: any) -> bool:
    is_a_tty = hasattr(stream, 'isatty') and stream.isatty()

    # Pycharm and Vscode support colour in their inbuilt editors
    if 'PYCHARM_HOSTED' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode':
        return is_a_tty

    if sys.platform != 'win32':
        # Docker does not consistently have a tty attached to it
        return is_a_tty or is_docker()

    # ANSICON checks for things like ConEmu
    # WT_SESSION checks if this is Windows Terminal
    return is_a_tty and ('ANSICON' in os.environ or 'WT_SESSION' in os.environ)


def create_logger(logger_name: str, level: int = logging.INFO) -> logging.Logger:
    handler = logging.StreamHandler()
    formatter = None
    if stream_supports_colour(handler.stream):
        formatter = _ColourFormatter()
    else:
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    logger = logging.getLogger(logger_name)
    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

def sanitize_ip_and_port(ip_and_port: str) -> str:
    sanitized_ip_and_port: str = ip_and_port.replace('[','').replace(']','')
    ip = ":".join(sanitized_ip_and_port.split(":")[:-1])
    port = sanitized_ip_and_port.split(":")[-1]
    if not port.isdigit() and not (1024 <= int(port) <= 65535):
        raise ValueError("Not a valid port! Ports must be integers between 1024 and 65535")
    if not isinstance(ip_address(ip), (IPv4Address, IPv6Address)):
        raise ValueError("Not a valid IP address!")
    return sanitized_ip_and_port

def is_ipv4_address(ip_and_port: str) -> bool:
    ip = ":".join(ip_and_port.split(":")[:-1])
    try:
        return isinstance(ip_address(ip), IPv4Address)
    except ValueError:
        return False

def is_ipv6_address(ip_and_port: str) -> bool:
    ip = ":".join(ip_and_port.split(":")[:-1])
    try:
        return isinstance(ip_address(ip), IPv6Address)
    except ValueError:
        return False