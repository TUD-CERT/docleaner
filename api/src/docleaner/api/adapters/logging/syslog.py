import datetime
import logging.handlers
import re
import socket
import time
from typing import Any


class SysLogHandler5424(logging.handlers.SysLogHandler):
    """Based on https://docs.python.org/3/howto/logging-cookbook.html"""

    tz_offset = re.compile(r"([+-]\d{2})(\d{2})$")
    escaped = re.compile(r'([\]"\\])')

    def __init__(self, *args: Any, **kwargs: Any):
        self.msgid = kwargs.pop("msgid", None)
        self.appname = kwargs.pop("appname", None)
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        version = 1
        asctime = datetime.datetime.fromtimestamp(record.created).isoformat()
        m = self.tz_offset.match(time.strftime("%z"))
        has_offset = False
        if m and time.timezone:
            hrs, mins = m.groups()
            if int(hrs) or int(mins):
                has_offset = True
        if not has_offset:
            asctime += "Z"
        else:
            asctime += f"{hrs}:{mins}"
        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = "-"
        appname = self.appname or "-"
        procid = record.process
        msgid = self.msgid or "-"
        msg = super().format(record)
        sdata = "-"
        return (
            f"{version} {asctime} {hostname} {appname} {procid} {msgid} {sdata} {msg}"
        )
