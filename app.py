import os
import json
import threading
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# MQTT CONFIGURATION
# ============================================================

MQTT_BROKER = os.getenv(
    "MQTT_BROKER",
    "bravetawny-af88996b.a02.usw2.aws.hivemq.cloud"
)

MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))

MQTT_USERNAME = os.getenv(
    "MQTT_USERNAME",
    ""
)

MQTT_PASSWORD = os.getenv(
    "MQTT_PASSWORD",
    ""
)


STATUS_TOPIC = "home/status"

DEVICE_TOPICS = {
    "light": "home/light",
    "fan": "home/fan",
    "geyser": "home/geyser"
}


# ============================================================
# SHARED STATE
# ============================================================

lock = threading.Lock()

device_state = {
    "light": "OFF",
    "fan": "OFF",
    "geyser": "OFF"
}

sensor_state = {
    "temperature": None,
    "humidity": None,
    "gas": "UNKNOWN",
    "gas_raw": 0
}

mqtt_state = {
    "connected": False,
    "last_error": None,
    "last_message": None,
    "last_topic": None,
    "last_payload": None,
    "last_command": None,
    "last_command_result": None
}


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(message, flush=True)


# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, reason_code, properties):

    log(
        f"MQTT CONNECTED CALLBACK: "
        f"broker={MQTT_BROKER}:{MQTT_PORT}, "
        f"reason_code={reason_code}"
    )

    if reason_code == 0:

        with lock:
            mqtt_state["connected"] = True
            mqtt_state["last_error"] = None

        log("MQTT CONNECTION SUCCESSFUL")

        try:
            result, mid = client.subscribe(
                STATUS_TOPIC,
                qos=0
            )

            log(
                f"MQTT SUBSCRIBE: "
                f"topic={STATUS_TOPIC}, "
                f"result={result}, "
                f"mid={mid}"
            )

        except Exception as error:

            log(
                f"MQTT SUBSCRIBE ERROR: {error}"
            )

    else:

        with lock:
            mqtt_state["connected"] = False
            mqtt_state["last_error"] = (
                f"Connection refused: {reason_code}"
            )

        log(
            f"MQTT CONNECTION FAILED: "
            f"reason_code={reason_code}"
        )


def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    with lock:
        mqtt_state["connected"] = False
        mqtt_state["last_error"] = (
            f"Disconnected: {reason_code}"
        )

    log(
        f"MQTT DISCONNECTED: "
        f"reason_code={reason_code}"
    )


def on_subscribe(
    client,
    userdata,
    mid,
    reason_codes,
    properties=None
):

    log(
        f"MQTT SUBSCRIBE CALLBACK: "
        f"mid={mid}, "
        f"reason_codes={reason_codes}"
    )


def on_publish(
    client,
    userdata,
    mid,
    reason_code=None,
    properties=None
):

    log(
        f"MQTT PUBLISH CALLBACK: "
        f"mid={mid}, "
        f"reason_code={reason_code}"
    )


def on_message(
    client,
    userdata,
    message
):

    topic = message.topic

    try:
        payload = message.payload.decode("utf-8")

    except Exception as error:

        log(
            f"MQTT PAYLOAD DECODE ERROR: {error}"
        )

        return

    log(
        f"MQTT MESSAGE RECEIVED: "
        f"topic={topic}"
    )

    log(
        f"MQTT PAYLOAD: {payload}"
    )

    # Store latest MQTT message
    with lock:

        mqtt_state["last_message"] = (
            datetime.now(timezone.utc).isoformat()
        )

        mqtt_state["last_topic"] = topic

        mqtt_state["last_payload"] = payload

    # Only process home/status
    if topic != STATUS_TOPIC:
        return

    try:

        data = json.loads(payload)

        devices = data.get(
            "devices",
            {}
        )

        sensors = data.get(
            "sensors",
            {}
        )

        # -----------------------------
        # Update appliance states
        # -----------------------------

        with lock:

            for device in (
                "light",
                "fan",
                "geyser"
            ):

                if device in devices:

                    value = devices[device]

                    if value is not None:

                        device_state[device] = (
                            str(value).upper()
                        )


            # -----------------------------
            # Update sensor values
            # -----------------------------

            for sensor in (
                "temperature",
                "humidity",
                "gas",
                "gas_raw"
            ):

                if sensor in sensors:

                    sensor_state[sensor] = (
                        sensors[sensor]
                    )

        log(
            "MQTT STATUS UPDATED SUCCESSFULLY"
        )

        log(
            f"TEMPERATURE: "
            f"{sensor_state['temperature']}"
        )

        log(
            f"HUMIDITY: "
            f"{sensor_state['humidity']}"
        )

        log(
            f"GAS: "
            f"{sensor_state['gas']}"
        )

    except Exception as error:

        log(
            f"MQTT STATUS UPDATE ERROR: {error}"
        )


# ============================================================
# MQTT CLIENT
# ============================================================

# Unique client ID prevents duplicate-client conflicts
MQTT_CLIENT_ID = (
    "flask-home-remote-"
    + uuid.uuid4().hex[:12]
)

log(
    f"MQTT CLIENT ID: {MQTT_CLIENT_ID}"
)


mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=MQTT_CLIENT_ID
)


# Username/password
mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# TLS for HiveMQ Cloud port 8883
mqtt_client.tls_set()


# Callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_subscribe = on_subscribe
mqtt_client.on_publish = on_publish
mqtt_client.on_message = on_message


# Automatic reconnect delay
mqtt_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)


# ============================================================
# MQTT STARTUP
# ============================================================

def start_mqtt():

    log(
        "================================================"
    )

    log(
        "STARTING MQTT CONNECTION"
    )

    log(
        f"Broker: {MQTT_BROKER}"
    )

    log(
        f"Port: {MQTT_PORT}"
    )

    log(
        f"Username configured: "
        f"{bool(MQTT_USERNAME)}"
    )

    log(
        f"Password configured: "
        f"{bool(MQTT_PASSWORD)}"
    )

    log(
        "================================================"
    )

    try:

        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        log(
            "MQTT TCP/TLS CONNECTION CREATED"
        )

        mqtt_client.loop_forever()

    except Exception as error:

        with lock:

            mqtt_state["connected"] = False

            mqtt_state["last_error"] = str(error)

        log(
            f"MQTT CONNECTION ERROR: {error}"
        )


mqtt_thread = threading.Thread(
    target=start_mqtt,
    daemon=True
)

mqtt_thread.start()


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# STATUS API
# ============================================================

@app.route("/api/status")
def api_status():

    with lock:

        response = {
            "devices": dict(device_state),

            "sensors": dict(sensor_state),

            "mqtt": dict(mqtt_state),

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }

    return jsonify(response)


# ============================================================
# MQTT DEBUG API
# ============================================================

@app.route("/api/mqtt")
def api_mqtt():

    with lock:

        response = {
            "broker": MQTT_BROKER,

            "port": MQTT_PORT,

            "username": MQTT_USERNAME,

            "password_configured":
                bool(MQTT_PASSWORD),

            "status_topic":
                STATUS_TOPIC,

            "device_topics":
                DEVICE_TOPICS,

            **dict(mqtt_state)
        }

    return jsonify(response)


# ============================================================
# DEVICE CONTROL
# ============================================================

@app.route(
    "/api/device/<device>/<action>",
    methods=["POST", "GET"]
)
def control_device(
    device,
    action
):

    device = device.lower().strip()

    action = action.upper().strip()

    log(
        "================================================"
    )

    log(
        f"DEVICE CONTROL REQUEST: "
        f"{device} -> {action}"
    )

    # Validate device
    if device not in DEVICE_TOPICS:

        return jsonify({
            "success": False,
            "error": "Unknown device"
        }), 400


    # Validate action
    if action not in (
        "ON",
        "OFF"
    ):

        return jsonify({
            "success": False,
            "error":
                "Action must be ON or OFF"
        }), 400


    topic = DEVICE_TOPICS[device]


    # Check MQTT connection
    if not mqtt_client.is_connected():

        log(
            "CONTROL ERROR: "
            "MQTT CLIENT IS NOT CONNECTED"
        )

        with lock:

            mqtt_state["last_command"] = (
                f"{device}:{action}"
            )

            mqtt_state["last_command_result"] = (
                "MQTT_NOT_CONNECTED"
            )

        return jsonify({
            "success": False,
            "error":
                "MQTT client is not connected"
        }), 503


    try:

        log(
            f"MQTT COMMAND PUBLISH: "
            f"topic={topic}, "
            f"payload={action}"
        )


        result = mqtt_client.publish(
            topic=topic,
            payload=action,
            qos=0,
            retain=False
        )


        log(
            f"MQTT PUBLISH RESULT: "
            f"rc={result.rc}, "
            f"mid={result.mid}"
        )


        with lock:

            mqtt_state["last_command"] = (
                f"{device}:{action}"
            )

            mqtt_state["last_command_result"] = (
                f"rc={result.rc},mid={result.mid}"
            )


        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            log(
                f"MQTT PUBLISH FAILED: "
                f"rc={result.rc}"
            )

            return jsonify({
                "success": False,
                "error":
                    f"MQTT publish failed: "
                    f"{result.rc}"
            }), 500


        log(
            "MQTT COMMAND ACCEPTED"
        )


        return jsonify({

            "success": True,

            "device": device,

            "action": action,

            "topic": topic,

            "message_id": result.mid
        })


    except Exception as error:

        log(
            f"MQTT COMMAND ERROR: {error}"
        )

        with lock:

            mqtt_state["last_command"] = (
                f"{device}:{action}"
            )

            mqtt_state["last_command_result"] = (
                f"ERROR: {error}"
            )


        return jsonify({

            "success": False,

            "error": str(error)

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    with lock:

        connected = (
            mqtt_state["connected"]
        )

        last_error = (
            mqtt_state["last_error"]
        )


    return jsonify({

        "status": "ok",

        "mqtt_connected":
            connected,

        "mqtt_error":
            last_error
    })


# ============================================================
# RUN LOCAL
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
