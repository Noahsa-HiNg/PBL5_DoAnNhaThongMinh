
import paho.mqtt.client as mqtt

class MQTTService:
    def __init__(self, broker="broker.emqx.io", port=1883):
        self.client = mqtt.Client()
        self.broker = broker
        self.port = port
        self.on_message_received = None

    def connect(self):
        self.client.on_message = self._internal_on_message
        self.client.connect(self.broker, self.port)
        self.client.subscribe("pbl5/sensor/#")
        self.client.loop_start()

    def _internal_on_message(self, client, userdata, msg):
        if self.on_message_received:
            self.on_message_received(msg.topic, msg.payload.decode())

    def publish(self, topic, payload):
        self.client.publish(topic, payload)