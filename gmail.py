#!/usr/bin/env python
# -*- coding: utf-8 -*-
# import httplib2
import base64
import codecs
import datetime as dt
import logging
import os
from email.mime.text import MIMEText

import oauth2client
# from apiclient import discovery
from apiclient import errors
from oauth2client import client
from oauth2client import tools

SCOPES = 'https://www.googleapis.com/auth/gmail.compose'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Watchtorian'

logger = logging.getLogger(__name__)

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None


def send_email_message(service, user_id, message):
    """Send an email message.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    message: Message to be sent.

  Returns:
    Sent Message.
  """
    try:
        message = (service.users().messages().send(userId=user_id, body=message)
                   .execute())
        logger.info('Email Message Id: %s' % message['id'])
        return message
    except errors.HttpError as err:
        print('An error occurred: %s' % err)


def create_email_message(sender, to, subject, message_text):
    """Create a message for an email.

  Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.

  Returns:
    An object containing a base64url encoded email object.
  """
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    # return {'raw': base64.urlsafe_b64encode(message.as_string())}
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


def get_email_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sendEmail.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def apply_email_template(last_email, host: str, data, datalog, filename: str):
    """

    :param last_email: date of last email
    :param host: name of the host this script in running on
    :param data: latest system info
    :param datalog: Aggregated history data
    :param filename: Path (absolute or relative) and filename to the email template
    :rtype: str
    :return: email body html code
    """
    datetime_format = "%Y%m%d %H:%M"
    src = get_email_template(filename)
    cl = get_n_last_value("cpu_load", datalog[3])
    clc = get_n_last_value("cpu_load", datalog[3], 1)
    ct = get_n_last_value("cpu_temp", datalog[3])
    ctc = get_n_last_value("cpu_temp", datalog[3], 1)
    dl = get_n_last_value("disk_usage_percent", datalog[3])
    dlc = get_n_last_value("disk_usage_percent", datalog[3], 1)
    il = get_n_last_value("internet", datalog[3])
    ilc = get_n_last_value("internet", datalog[3], 1)

    src = src.replace("{host}", host)
    src = src.replace("{report_date}", dt.datetime.now().strftime(datetime_format))
    src = src.replace("{last_report_date}", last_email.strftime(datetime_format))
    src = src.replace("{cpu_load}", "{0:.2f}".format(cl))
    src = src.replace("{cpu_load_change}", delta_rep(cl, clc, False))
    src = src.replace("{cpu_temp}", "{0:.2f}".format(ct))
    src = src.replace("{cpu_temp_change}", delta_rep(ct, ctc, False))
    src = src.replace("{disk}", "{0:.2f}".format(dl))
    src = src.replace("{disk_change}", delta_rep(dl, dlc, False))
    src = src.replace("{internet}", "{0:.2f}".format(il))
    src = src.replace("{internet_change}", delta_rep(il, ilc, True))

    rows = ""
    rows += "<tr><td>Snapshot right now</td>"
    rows += "<td>" + "{0:.2f}".format(data.cpu_load) + "</td>"
    rows += "<td>" + "{0:.2f}".format(data.cpu_temp) + "</td>"
    rows += "<td>" + "{0:.2f}".format(data.disk_usage_percent) + "</td>"
    rows += "<td>" + "Online" if data.internet else "Offline" + "</td></tr>"
    for x in datalog[3]:
        rows += "<tr>"
        rows += "<td>" + x.when.strftime(datetime_format) + "</td>"
        rows += "<td>" + "{0:.2f}".format(x.cpu_load) + "</td>"
        rows += "<td>" + "{0:.2f}".format(x.cpu_temp) + "</td>"
        rows += "<td>" + "{0:.2f}".format(x.disk_usage_percent) + "</td>"
        rows += "<td>" + "{0:.2f}".format(x.internet) + "</td>"
        rows += "</tr>"
    return src.replace("{hist_table_rows}", rows)


def get_email_template(filename: str, encoding: str = "utf-8") -> str:
    """
    Returns the entire content of the file.
    :param filename: path (absolute or relative) and filename to the email template
    :param encoding: encoding of file to read. default = utf-8.
    :rtype: str
    :return: email template (entire content of file)
    """
    filename = path_join(filename)

    with codecs.open(filename, "r", encoding) as file:
        return file.read()
    pass


def delta_rep(new: float, old: float, positive_is_good: bool = True) -> str:
    if old is None:
        old = 0
    if positive_is_good and new >= old:
        r = "<span style='color:green'>"
    elif not positive_is_good and new <= old:
        r = "<span style='color:green'>"
    else:
        r = "<span style='color:red'>"

    if new < old:
        r += "▼" + str(int(abs(new - old))) + "</span>"
    elif new == old:
        r += "±" + str(int(abs(new - old))) + "</span>"
    else:
        r += "▲" + str(int(abs(new - old))) + "</span>"
    return r


def get_n_last_value(what: str, arr: list, index: int = 0):
    if not arr:
        raise ValueError
    if len(arr) <= index:
        return None

    # sort based on date
    arr.sort(key=lambda x: x.when, reverse=True)
    return getattr(arr[index], what)


def script_home_path():
    return os.path.dirname(os.path.realpath(__file__))


def path_join(filename, basedir=script_home_path()):
    return os.path.join(basedir, filename)

'''
import smtplib
import logging

logger = logging.getLogger(__name__)


def send_email(**kwargs):
    """
    Expects the following mandatory named arguments:
     - mail_host: str
     - mail_port: int
     - user: str
     - pwd: str
     - from_address: str
     - to_address: str
     - subject: str
     - body: str
    """
    email_text = """\  
    From: %s  
    To: %s  
    Subject: %s
    
    %s
    """ % (kwargs.get("from_address"), kwargs.get("to"), kwargs.get("subject"), kwargs.get("body"))

    try:
        server = smtplib.SMTP_SSL(kwargs.get("host"), kwargs.get("port"))
        server.ehlo()
        server.login(kwargs.get("user")), kwargs.get("pwd")
        server.sendmail(kwargs.get("from"), kwargs.get("to"), email_text)
        server.close()

        logger.debug("Email sent!")
        return True
    except Exception as e:
        logger.error("Error when sending email: ", exc_info=True)
        return False, e
'''
