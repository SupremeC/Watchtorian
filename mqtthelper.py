import logging
import socket

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


def mqtt_publish(topic_data: dict, broker_address: str, port=1883, user=None, pwd=None, client_id: str = None):
    """

    :param topic_data: List of topics and values to publish
    :param broker_address: IP or address to MQTT broker
    :param port: Port of MQTT broker. Default = 1883
    :param user:
    :param pwd:
    :param client_id:
    :return:
    """
    try:
        if client_id is None:
            client = mqtt.Client(clean_session=True)
        else:
            client = mqtt.Client(client_id=client_id, clean_session=True)

        if user is not None and pwd is not None:
            client.username_pw_set(user, pwd)

        client.connect(broker_address, port)
        for topic, msg in topic_data.items():
            client.publish(topic, msg, retain=True)
        client.disconnect()
        logger.info("Published to MQTT")
    except socket.timeout:
        logger.error("Failed to publish to MQTT", exc_info=True)
