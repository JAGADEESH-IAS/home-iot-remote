import os
import uuid
from flask import Flask, jsonify
import paho.mqtt.client as mqtt

app = Flask(__name__)

# ============================================================
# MQTT CONFIG
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

LIGHT_TOPIC = "home/light"

mqtt_connected = False
last_error = None
last_publish = None


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
        print("========================================", flush=True)

    else:

        mqtt_connected = False

        print(
            f"MQTT CONNECTION FAILED: {reason_code}",
            flush=True
        )


def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    global mqtt_connected

    mqtt_connected = False

    print("MQTT DISCONNECTED", flush=True)
    print(
        f"Disconnect reason: {reason_code}",
        flush=True
    )


def on_publish(
    client,
    userdata,
    mid,
    reason_code=None,
    properties=None
):

    print(
        f"MQTT PUBLISH CALLBACK: mid={mid}",
        flush=True
    )


def on_message(client, userdata, message):

    try:
        payload = message.payload.decode("utf-8")
    except Exception:
        payload = str(message.payload)

    print("========================================", flush=True)
    print("MQTT MESSAGE RECEIVED", flush=True)
    print(f"Topic: {message.topic}", flush=True)
    print(f"Payload: {payload}", flush=True)
    print("========================================", flush=True)


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

CLIENT_ID = (
    "flask-command-test-"
    + uuid.uuid4().hex[:10]
)

print("========================================", flush=True)
print("STARTING FLASK MQTT COMMAND TEST", flush=True)
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

client.tls_set()

client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
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
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "application": "HomeIoT MQTT Command Test",
        "mqtt_connected": mqtt_connected,
        "broker": MQTT_BROKER,
        "port": MQTT_PORT,
        "last_error": last_error,
        "last_publish": last_publish
    })


# ============================================================
# TEST LIGHT ON
# ============================================================

@app.route("/test/light/on")
def test_light_on():

    global last_publish

    print("========================================", flush=True)
    print("FLASK LIGHT ON TEST", flush=True)

    if not mqtt_connected:

        print(
            "MQTT IS NOT CONNECTED",
            flush=True
        )

        return jsonify({
            "success": False,
            "error": "MQTT is not connected"
        }), 503


    try:

        result = client.publish(
            LIGHT_TOPIC,
            "ON",
            qos=1,
            retain=False
        )

        print(
            f"MQTT PUBLISH RESULT: rc={result.rc}, "
            f"mid={result.mid}",
            flush=True
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_publish = (
                f"FAILED rc={result.rc}"
            )

            return jsonify({
                "success": False,
                "error": f"Publish failed: {result.rc}"
            }), 503


        # Wait for Paho to confirm transmission.
        result.wait_for_publish(
            timeout=5
        )

        last_publish = (
            f"SUCCESS mid={result.mid}"
        )

        print(
            "FLASK → HIVEMQ PUBLISH SUCCESS",
            flush=True
        )

        print(
            "Topic: home/light",
            flush=True
        )

        print(
            "Message: ON",
            flush=True
        )

        print("========================================", flush=True)


        return jsonify({
            "success": True,
            "topic": LIGHT_TOPIC,
            "message": "ON",
            "message_id": result.mid
        })


    except Exception as error:

        last_publish = (
            f"ERROR: {error}"
        )

        print(
            f"PUBLISH ERROR: {error}",
            flush=True
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "mqtt_connected": mqtt_connected,
        "last_publish": last_publish,
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
