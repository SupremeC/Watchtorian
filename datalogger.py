#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import datetime
import logging
import os.path

from customtypes import PollData

logger = logging.getLogger(__name__)


class DataLogger(object):
    NEWLINE = "\n"

    @staticmethod
    def writeline_to_data_log(filename, data):
        """ Appends data to the end of the data file"""
        with codecs.open(filename, "a", "utf-8") as file:
            # with open(filename, "a") as file:
            file.write(str(data) + DataLogger.NEWLINE)

    @staticmethod
    def create_data_log(filename,
                        overwrite: bool = False,
                        email_date: datetime = None,
                        mqtt_date: datetime = None,
                        data: list = None,
                        aggregate_data: list = None):
        """
        Creates a new data file.

        :param filename: path and filename to data log
        :param overwrite: [Bool]. If file already exists, should it be overwritten?
        :param email_date: date when last email was sent
        :param mqtt_date: date when last mqtt message was published
        :param data: a list
        :param aggregate_data: a list
        :return: None
        """
        if os.path.isfile(filename) and overwrite:
            logger.warning("data file already exists. It will be overwritten.")
            os.remove(filename)
        if os.path.isfile(filename) and not overwrite:
            return
        # with open(filename, "w+") as f:
        with codecs.open(filename, "w+", "utf-8") as file:
            if email_date is None:
                email_date = datetime.datetime.min
            if mqtt_date is None:
                mqtt_date = datetime.datetime.min
            file.write("# format {report_history:last_email_date;last_mqtt_pub_date}" + DataLogger.NEWLINE)
            file.write("report_history:{0};{1}{2}".format(email_date.strftime(PollData.DATETIME_FORMAT),
                                                          mqtt_date.strftime(PollData.DATETIME_FORMAT),
                                                          DataLogger.NEWLINE))
            file.write("#" + DataLogger.NEWLINE)
            file.write("#" + DataLogger.NEWLINE)
            file.write("#" + DataLogger.NEWLINE)

            file.write("# data aggregate format {aggregate:datetime;cpu_load%;cpu_temp;disk%;internet%;notUsed" +
                       DataLogger.NEWLINE)

            # if isinstance(x,(list,)):
            if aggregate_data is not None and isinstance(aggregate_data, (list,)):
                for a in aggregate_data:
                    file.write("aggregate:" + str(a) + DataLogger.NEWLINE)

            file.write("#" + DataLogger.NEWLINE)
            file.write("#" + DataLogger.NEWLINE)
            file.write("#" + DataLogger.NEWLINE)

            file.write("# data format {datetime;cpuload;cputemp;disk;internet;[{machines}]}" + DataLogger.NEWLINE)
            if data is not None and isinstance(data, (list,)):
                for d in data:
                    file.write(str(d) + DataLogger.NEWLINE)

    @staticmethod
    def clear_data_log(filename):
        """ Erase all the stored data."""
        open(filename, 'w').close()

    @staticmethod
    def read_data_log(filename, skip_data):
        """
        Reads the data log.
        Will throw ValueError() exception if data is corrupted or missing.

        :param skip_data: Only read the headers. Will not read and parse the data.
        :param filename: path and filename to data log
        :return: an object of undecided format TODO
        """
        email_sent = None
        mqtt = None
        data = []
        aggregate_data = []
        # with open(filename, "r") as file:
        with codecs.open(filename, "r", "utf-8") as file:
            data_list = [line.rstrip() for line in file]
            for line in data_list:
                if not line.strip():
                    continue  # skip the empty line
                if line.startswith("#"):
                    continue  # skip comment lines
                if line.startswith("report_history:"):
                    email_sent, mqtt = DataLogger._parse_history_line(line)
                    # return early if [skip_data] == TRUE
                    if skip_data:
                        return email_sent, mqtt, None
                if not skip_data and line.startswith("aggregate"):
                    l = line.strip().replace("aggregate:", "")
                    aggregate_data.append(PollData.from_text(l))
                if not skip_data and line[0].isdigit():
                    data.append(PollData.from_text(line.strip()))
        if email_sent is None:
            raise ValueError("Email last sent date was not found in file " + filename)
        if mqtt is None:
            raise ValueError("mqtt last sent date was not found in file " + filename)
        return email_sent, mqtt, data, aggregate_data

    @staticmethod
    def _parse_history_line(line: str):
        email_sent = None
        mqtt = None
        try:
            p = line.strip().replace("report_history:", "").split(";")
            email_sent = DataLogger.str_to_datetime(p[0])
            mqtt = DataLogger.str_to_datetime(p[1])
        except ValueError:
            logger.error("Failed to parse history line", exc_info=True)
        return email_sent, mqtt

    @staticmethod
    def str_to_datetime(s):
        """
        Parses a string and converts it to DateTime
        :param s: the string to parse
        :return: a datetime
        """
        return datetime.datetime.strptime(s, PollData.DATETIME_FORMAT)
