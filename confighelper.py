#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser


def config_section_map(config: configparser.ConfigParser, section: str) -> dict:
    """

    :rtype: dict
    """
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
                pass
        except KeyError:
            dict1[option] = None
    return dict1


def get_report(config: configparser.ConfigParser, name: str):
    val = config.get("reports", name).split(",")
    return val[0] in ["True", "true", "1", "yes", "y"], int(val[1])


def get_email_conf(config: configparser.ConfigParser) -> dict:
    """

    :rtype: dict
    :param config:
    :return: a Dict with all email settings from config file
    """
    host = config.get("email", "mail_host")
    port = config.get("email", "mail_port")
    user = config.get("email", "from_address")
    from_address = config.get("email", "from_address")
    pwd = config.get("email", "pwd")
    to = config.get("email", "to_address")
    subject = config.get("email", "subject")
    return {"host": host, "port": port,
            "user": user, "pwd": pwd,
            "from_address": from_address,
            "to": to, "subject": subject}
