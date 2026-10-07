import os
import time
import uuid
from flask import Flask, jsonify
import paho.mqtt.client as mqtt

app = Flask(__name__)

# ============================================================
# HIVE MQ CONFIG
# ============================================================

MQTT_BROKER = os.getenv(
    "MQTT_BROKER",
    "bravetawny-af88996b.a02.usw2.aws.hivemq.cloud"
)

MQTT_PORT = int(
    os.getenv("MQTT_PORT", "8883")
)

MQTT_USERNAME = os.getenv(
    "MQTT_USERNAME",
    ""
)

MQTT_PASSWORD = os.getenv(
    "MQTT_PASSWORD",
    ""
)

STATUS_TOPIC = "home/status"


# ============================================================
# MQTT STATE
# ============================================================

mqtt_connected = False
last_message = None
last_error = None


# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, reason_code, properties):

    global mqtt_connected

    print("========================================", flush=True)
    print("MQTT CONNECT CALLBACK", flush=True)
    print(f"Reason code: {reason_code}", flush=True)

    if reason_code == 0:

        mqtt_connected = True

        print("MQTT CONNECTED SUCCESSFULLY", flush=True)
        print(f"Broker: {MQTT_BROKER}", flush=True)
        print(f"Port: {MQTT_PORT}", flush=True)

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=1
        )

        print(
            f"SUBSCRIBE RESULT: {result}, MID: {mid}",
            flush=True
        )

    else:

        mqtt_connected = False

        print(
            f"MQTT CONNECTION FAILED: {reason_code}",
            flush=True
        )

    print("========================================", flush=True)


def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    global mqtt_connected

    mqtt_connected = False

    print("========================================", flush=True)
    print("MQTT DISCONNECTED", flush=True)
    print(f"Reason code: {reason_code}", flush=True)
    print("========================================", flush=True)


def on_message(client, userdata, message):

    global last_message

    try:
        payload = message.payload.decode("utf-8")
    except Exception:
        payload = str(message.payload)

    last_message = payload

    print("========================================", flush=True)
    print("MQTT MESSAGE RECEIVED", flush=True)
    print(f"Topic: {message.topic}", flush=True)
    print(f"Payload: {payload}", flush=True)
    print("========================================", flush=True)


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

CLIENT_ID = (
    "flask-test-"
    + uuid.uuid4().hex[:10]
)

print("========================================", flush=True)
print("STARTING MQTT CONNECTION TEST", flush=True)
print(f"Client ID: {CLIENT_ID}", flush=True)
print(f"Broker: {MQTT_BROKER}", flush=True)
print(f"Port: {MQTT_PORT}", flush=True)
print(
    f"Username configured: {bool(MQTT_USERNAME)}",
    flush=True
)
print(
    f"Password configured: {bool(MQTT_PASSWORD)}",
    flush=True
)
print("========================================", flush=True)


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT_ID
)

client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)

# HiveMQ Cloud TLS
client.tls_set()

client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message


# ============================================================
# CONNECT
# ============================================================

try:

    print("CONNECTING TO HIVEMQ...", flush=True)

    client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        keepalive=60
    )

    print(
        "MQTT TCP/TLS CONNECTION CREATED",
        flush=True
    )

    client.loop_start()

    print(
        "MQTT BACKGROUND LOOP STARTED",
        flush=True
    )

except Exception as error:

    last_error = str(error)

    print(
        f"MQTT CONNECTION ERROR: {error}",
        flush=True
    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "application": "HomeIoT",
        "mqtt_connected": mqtt_connected,
        "broker": MQTT_BROKER,
        "port": MQTT_PORT,
        "last_message": last_message,
        "last_error": last_error
    })


@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "mqtt_connected": mqtt_connected,
        "last_message": last_message,
        "last_error": last_error
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        ),
        debug=False
    )
