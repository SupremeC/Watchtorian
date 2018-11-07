#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import datetime
import logging
import re

logger = logging.getLogger(__name__)
FieldUpdates = collections.namedtuple("FieldUpdates", ["field", "old_value", "new_value"])


class SystemInfo(object):
    def __init__(self):
        self.host = Host()
        self.cpu = Cpu()
        self.fs = FsSystem()


class Host(object):
    def __init__(self, ip=None, os=None, hostname=None, mac_address=None, boot_time=None, internet=None):
        self.ip = ip
        self.os = os
        self.hostname = hostname
        self.mac_address = mac_address
        self._boot_time = boot_time
        self.internet = internet

    @property
    def boot_time(self):
        """
        Returns the boot_time as a datetime object
        :return: datetime object
        """
        if isinstance(self._boot_time, float):
            return datetime.datetime.fromtimestamp(self._boot_time)
        elif isinstance(self._boot_time, datetime.datetime):
            return self._boot_time

    @boot_time.setter
    def boot_time(self, value):
        """
        Accepts either timestamp or datetime object.
        :param value: a timestamp or datetime object representing the boot_time.
        :return:
        """
        if isinstance(value, float):
            self._boot_time = datetime.datetime.fromtimestamp(value)
        elif isinstance(value, datetime.datetime):
            self._boot_time = value

    @property
    def friendly_internet(self):
        """
        Converts the base boolean to a human friendly string. Returns either "ONLINE" or "OFFLINE"
        :return: a string. "ONLINE", "OFFLINE"
        """
        if self.internet:
            return "ONLINE"
        else:
            return "OFFLINE"

    @property
    def up_time(self):
        """
        Calculates up-time based on self.boot_time and returns it in a human friendly format
        :return: string
        """
        return self.friendly_time_delta(self.boot_time)

    @staticmethod
    def friendly_time_delta(start, end=datetime.datetime.now()):
        """
        Calculates the difference between two datetime objects and returns a text representation.
        Example: 2 years, 54 days
        Example: 12 days, 1 hour
        :param start: the smaller (earlier) date
        :param end: the larger (latest) date
        :return: text string.
        """
        up_time = end - start
        years, reminder = divmod(up_time.total_seconds(), 31556926)
        days, reminder = divmod(reminder, 86400)
        hours, reminder = divmod(reminder, 3600)
        minutes, seconds = divmod(reminder, 60)
        ret = ""
        if years > 1:
            ret = str(int(years)) + " years, "
        elif years == 1:
            ret = "1 year, "
        if days > 1:
            ret += str(int(days)) + " days, "
        elif days == 1:
            ret += "1 day, "
        if hours > 1:
            ret += str(int(hours)) + " hours"
        elif hours == 1:
            ret += str(int(hours)) + " hour"
        if ret == "" and minutes > 0:
            ret += str(int(minutes)) + " minutes"
        if ret == "" and seconds > 0:
            ret += str(int(seconds)) + " seconds"
        return ret


class Cpu(object):
    def __init__(self, load=None, temp=None):
        self.temp = temp
        self.load = load


class FsSystem(object):
    def __init__(self, _total=None, used=None, free=None, percent=None):
        self.total = _total
        self.used = used
        self.free = free
        self.percent = percent

    def friendly_fs_size(self):
        """
        takes a file size (bytes) as input and converts it to a more human friendly format.
        All values above 1024 will be escalated to the next power (K, M, G, T, P, E, Z).
        Example: 5000 => 4.88 KB
        Example: 5000000 => 4.76 MB
        :return: text string.
        """
        return self.sizeof_fmt(self.used) + " of " + self.sizeof_fmt(self.total)

    @staticmethod
    def sizeof_fmt(num, suffix='B'):
        """
        return friendly byte size string.
        Example: 1024 -> 1KiB
        :param num: the number to transform
        :param suffix: string to append to the output
        :return:
        """
        # for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)


class PollData(object):
    DATETIME_FORMAT = "%Y%m%dT%H%M"
    FIELD_PART = ","
    PERCENT_PATTERN = re.compile("^\d{1,3}\.\d{1,2}$")

    def __init__(self, when: datetime = None, load: float = None, temp: float = None,
                 disk: float = None, internet: bool = None, machines=None):
        self.when = when
        self.cpu_load = load
        self.cpu_temp = temp
        self.disk_usage_percent = disk
        self.internet = internet
        self.machines = machines

    @classmethod
    def from_system_info(cls, o: SystemInfo):
        c = cls()
        c.internet = o.host.internet
        c.cpu_temp = o.cpu.temp
        c.cpu_load = o.cpu.load
        c.when = datetime.datetime.now()
        c.disk_usage_percent = o.fs.percent
        c.machines = []
        return c

    @classmethod
    def from_text(cls, text: str):
        """
        Parses a string and converts the text to a PollData object
         Expects this input format: {datetime;cpuload;cputemp;disk;internet;[{machines,}]}
         Example: 20181010T1644;4.3;44.8;5.2;1;RPI-A¤192.168.1.170¤443¤TCP/ping¤True
        :param text:
        :return: a [PollData] object
        """
        try:
            lst = text.split(";")
            if len(lst) != 6:
                raise IndexError("Input was not in expected format. Expected 6 values. Got " + str(len(lst)))
            c = cls(
                PollData.string_to_date(lst[0]),
                float(lst[1]),
                float(lst[2]),
                float(lst[3]),
                float(lst[4]) if PollData.PERCENT_PATTERN.match(lst[4]) else
                lst[4] in ["1", "True", "true", "y", "yes", "yup"],
                None)
            if len(lst[5]) > 0:
                tmp = lst[5].split(PollData.FIELD_PART)
                c.machines = []
                for m in tmp:
                    c.machines.append(Machine.from_text(m))
                c.machines = filter(None, c.machines)
            return c
        except ValueError as e:
            print("fuck!")
            logger.error("failed to convert: " + str(e))
            return None

    @classmethod
    def aggregate(cls, data: list):
        """
        Aggregates the following data and stores the average value
         - CPU load
         - CPU temp
         - Disk usage (in percent)
         - Internet (on/off -> percent)
        :param data: a list of [PollData] objects
        :return: a [PollData] object
        """
        c = cls()
        c.when = datetime.datetime.now()
        c.cpu_load = sum(log_row.cpu_load for log_row in data) / float(len(data))
        c.cpu_temp = sum(log_row.cpu_temp for log_row in data) / float(len(data))
        c.disk_usage_percent = sum(log_row.disk_usage_percent for log_row in data) / float(len(data))
        c.internet = sum(float(log_row.internet) for log_row in data) / float(len(data)) * 100
        return c

    def __str__(self):
        """
        Converts [self] to a text representation.
        To do the reverse, see class method PollData.from_text(...)
        :return: text string
        """
        if self.machines is None or self.machines is not list:
            machines = ""
        else:
            machines = PollData.FIELD_PART.join(map(str, self.machines))

        if type(self.internet) == float:
            internet = "{0:.2f}".format(self.internet) if self.internet is not None else 0
        else:
            internet = self.internet

        return "{};{};{};{};{};{}".format(
            PollData.date_formatter(self.when),
            "{0:.2f}".format(self.cpu_load) if self.cpu_load is not None else 0,
            "{0:.2f}".format(self.cpu_temp) if self.cpu_temp is not None else 0,
            "{0:.2f}".format(self.disk_usage_percent) if self.disk_usage_percent is not None else 0,
            str(internet) if self.internet is not None else 0,
            machines
        )

    @staticmethod
    def date_formatter(d: datetime.datetime):
        return d.strftime(PollData.DATETIME_FORMAT)

    @staticmethod
    def string_to_date(s: str):
        """
        Parses a string and converts it to DateTime
        :param s: the string to parse
        :return: a datetime
        """
        return datetime.datetime.strptime(s, PollData.DATETIME_FORMAT)


class Machine(object):
    SEP = "¤"

    def __init__(self, name, ip, port: int = None, method: str = None, result: bool = False):
        self.name = name
        self.ip = ip
        self.port = port
        self.poll_method = method
        self.result = result

    def __str__(self):
        return "{0}{5}{1}{5}{2}{5}{3}{5}{4}".format(
            self.name,
            self.ip,
            self.port,
            self.poll_method,
            self.result,
            Machine.SEP)

    @classmethod
    def from_text(cls, text: str):
        try:
            lst = text.split(Machine.SEP)
            return cls(lst[0], lst[1], int(lst[2]), lst[3], lst[4] in ["1", "True", "true", "yes", "y"])
        except (ValueError, IndexError):
            logger.error("Failed to convert text string to [machine] object", exc_info=True)
            return None
