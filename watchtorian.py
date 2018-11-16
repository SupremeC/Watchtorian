#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import logging.config
import os
from datetime import datetime as dt

import httplib2
from apiclient import discovery

import confighelper as ch
import gmail
import systemwatcher as sw
from customtypes import PollData
from datalogger import DataLogger
from mqtthelper import mqtt_publish


def script_home_path():
    return os.path.dirname(os.path.realpath(__file__))


def path_join(filename, basedir=script_home_path()):
    return os.path.join(basedir, filename)


# FIXED CONSTANTS
LOGGING_CONFIG_FILE = path_join("logging_config.ini")
APP_CONFIG_FILE = "config.ini"
DATA_LOG_FILE = "poll_data/polldata.dat"

# Logging setup, so that we can have unified logging throughout the app
logging.config.fileConfig(fname=LOGGING_CONFIG_FILE, disable_existing_loggers=False)
logger = logging.getLogger(__name__)

try:
    def main():
        config = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        config.read(APP_CONFIG_FILE)

        # fetch interesting system data that we will use for statistics
        swo = sw.SystemWatcher()
        swo._update_host_fs()
        swo._update_cpu_internet_uptime()
        data = PollData.from_system_info(swo.system_info)
        logger.info("fetched system data")

        # TODO - Poll machines
        # m = Machine("RPI-A", "192.168.1.170", 443, "TCP/ping", True)
        # data.machines.append(m)

        # Write system data to permanent storage
        DataLogger.writeline_to_data_log(DATA_LOG_FILE, data)
        logger.info("wrote data to file ./" + DATA_LOG_FILE)

        # Does any value exceed a threshold?
        # In that case we need to send a report immediately
        send_warning = False
        if data.cpu_load >= config.getint("warning_thresholds", "cpu_utilization_percent"):
            send_warning = True
            logger.info("CPU load threshold exceeded!")
        if data.cpu_temp >= config.getint("warning_thresholds", "cpu_temp"):
            send_warning = True
            logger.info("CPU temp threshold exceeded!")
        if data.disk_usage_percent >= config.getint("warning_thresholds", "disk_used_percent"):
            send_warning = True
            logger.info("Disk usage threshold exceeded!")

        # Get the last time we created a report
        dl = DataLogger.read_data_log(DATA_LOG_FILE, True)

        # Is it time to publish to MQTT broker?
        mqtt_enabled, mqtt_interval = ch.get_report(config, "publish_to_mqtt")
        if mqtt_enabled and (dt.now() - dl[1]).total_seconds() > mqtt_interval:
            to_pub = dict()
            to_pub[config.get("MQTT", "topic_alive")] = "on"
            to_pub[config.get("MQTT", "topic_cpu_temp")] = data.cpu_temp
            to_pub[config.get("MQTT", "topic_cpu_load")] = data.cpu_load
            to_pub[config.get("MQTT", "topic_cpu_internet")] = data.internet
            to_pub[config.get("MQTT", "topic_diskusagepercent")] = data.disk_usage_percent
            mqtt_publish(
                to_pub,
                config.get("MQTT", "broker_ip"),
                int(config.get("MQTT", "broker_port")),
                config.get("MQTT", "broker_user"),
                config.get("MQTT", "broker_pwd")
            )

        # Is it time to send an email report?
        email_enabled, email_interval = ch.get_report(config, "send_emails")
        if send_warning or email_enabled and (dt.now() - dl[0]).total_seconds() > email_interval:
            # Save report date because it will be overwritten when doing Aggregate
            last_report = dl[0]

            # aggregate data (an unfortunate side-affect is that the last report date will be set to Now()
            aggregate_data()

            # Load data
            dl = DataLogger.read_data_log(DATA_LOG_FILE, False)

            # get email credentials
            email_config = ch.config_section_map(config, "email")
            credentials = gmail.get_email_credentials()
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('gmail', 'v1', http=http, cache_discovery=False)

            # build html email from a template
            html_email = gmail.apply_email_template(
                last_report, config.get("app", "name"), data, dl, path_join("email_templates/default.html"))

            gmail.send_email_message(service, email_config["user"],
                                     gmail.create_email_message(email_config["from_address"],
                                                                email_config["to_address"],
                                                                email_config["subject"], html_email))
            logger.info("Sent email report to " + email_config["to_address"])


    def aggregate_data():
        """
         Compute data aggregate for whole period (since last email report)
         and save it to file (bad idea! it shouldn't)
        :return: None
        """
        # Load the entire data file
        df = DataLogger.read_data_log(DATA_LOG_FILE, False)

        # compute the average for all existing data
        df[3].append(PollData.aggregate(df[2]))

        # save a new file with ONLY the aggregate data
        now = dt.now()
        DataLogger.create_data_log(DATA_LOG_FILE, True, now, now, None, df[3])
        logger.info("Aggregate data complete. New data file created.")


    if __name__ == "__main__":
        main()

except KeyboardInterrupt:
    logger.info("Keyboard Interrupt. exiting program")
except:
    logger.error('Exception occurred', exc_info=True)
finally:
    logger.info("Cleaning up complete. Exiting program now")
