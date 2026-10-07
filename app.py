import os
import json
import uuid
import time
import threading

from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt


app = Flask(__name__)


# ============================================================
# MQTT CONFIGURATION
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


# ============================================================
# TOPICS
# ============================================================

LIGHT_TOPIC = "home/light"
FAN_TOPIC = "home/fan"
GEYSER_TOPIC = "home/geyser"
STATUS_TOPIC = "home/status"


# ============================================================
# DEVICE STATE
# ============================================================

device_states = {
    "light": "OFF",
    "fan": "OFF",
    "geyser": "OFF"
}


sensor_data = {
    "temperature": None,
    "humidity": None,
    "gas": "NORMAL",
    "gas_raw": None
}


mqtt_connected = False

last_error = None

last_status_time = None


state_lock = threading.Lock()


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(message, flush=True)


# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    global mqtt_connected
    global last_error

    log("")
    log("========================================")
    log("MQTT CONNECT CALLBACK")
    log(f"Reason code: {reason_code}")
    log("========================================")

    if reason_code == 0:

        mqtt_connected = True
        last_error = None

        log("MQTT CONNECTED SUCCESSFULLY")
        log(f"Broker: {MQTT_BROKER}")
        log(f"Port: {MQTT_PORT}")

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=0
        )

        log(
            f"STATUS SUBSCRIBE: "
            f"rc={result}, mid={mid}"
        )

    else:

        mqtt_connected = False

        last_error = (
            f"MQTT connection failed: "
            f"{reason_code}"
        )

        log("MQTT CONNECTION FAILED")


def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    global mqtt_connected

    mqtt_connected = False

    log("")
    log("========================================")
    log("MQTT DISCONNECTED")
    log(f"Reason code: {reason_code}")
    log("========================================")


def on_message(
    client,
    userdata,
    message
):

    global last_status_time

    if message.topic != STATUS_TOPIC:
        return

    try:

        payload = message.payload.decode(
            "utf-8"
        )

        data = json.loads(payload)

        log("")
        log("========================================")
        log("MQTT STATUS RECEIVED")
        log(f"Topic: {message.topic}")
        log(f"Payload: {payload}")
        log("========================================")

        with state_lock:

            # ------------------------------------------------
            # DEVICE STATES
            # ------------------------------------------------

            devices = data.get(
                "devices",
                {}
            )

            if "light" in devices:

                device_states["light"] = str(
                    devices["light"]
                ).upper()

            if "fan" in devices:

                device_states["fan"] = str(
                    devices["fan"]
                ).upper()

            if "geyser" in devices:

                device_states["geyser"] = str(
                    devices["geyser"]
                ).upper()

            # ------------------------------------------------
            # SENSOR DATA
            # ------------------------------------------------

            sensors = data.get(
                "sensors",
                {}
            )

            sensor_data["temperature"] = (
                sensors.get("temperature")
            )

            sensor_data["humidity"] = (
                sensors.get("humidity")
            )

            sensor_data["gas"] = sensors.get(
                "gas",
                "NORMAL"
            )

            sensor_data["gas_raw"] = (
                sensors.get("gas_raw")
            )

            last_status_time = time.time()

    except Exception as error:

        log("")
        log("MQTT STATUS PARSE ERROR")
        log(str(error))


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

CLIENT_ID = (
    "flask-dashboard-" +
    uuid.uuid4().hex[:12]
)


log("")
log("========================================")
log("STARTING HOME IOT FLASK APPLICATION")
log(f"Client ID: {CLIENT_ID}")
log(f"Broker: {MQTT_BROKER}")
log(f"Port: {MQTT_PORT}")
log(
    f"Username configured: "
    f"{bool(MQTT_USERNAME)}"
)
log(
    f"Password configured: "
    f"{bool(MQTT_PASSWORD)}"
)
log("========================================")


mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT_ID
)


mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


mqtt_client.tls_set()


mqtt_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)


mqtt_client.on_connect = on_connect

mqtt_client.on_disconnect = on_disconnect

mqtt_client.on_message = on_message


# ============================================================
# MQTT CONNECTION
# ============================================================

try:

    log("CONNECTING TO HIVEMQ...")

    mqtt_client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        keepalive=60
    )

    mqtt_client.loop_start()

    log("MQTT NETWORK LOOP STARTED")

except Exception as error:

    mqtt_connected = False

    last_error = str(error)

    log("MQTT STARTUP ERROR")
    log(str(error))


# ============================================================
# PUBLISH COMMAND
# ============================================================

def publish_command(
    topic,
    payload
):

    global last_error

    log("")
    log("========================================")
    log("DEVICE COMMAND")
    log(f"Topic: {topic}")
    log(f"Payload: {payload}")
    log("QoS: 0")
    log("========================================")

    try:

        # ----------------------------------------------------
        # IMPORTANT:
        # QoS 0 is the method we just proved works.
        # ----------------------------------------------------

        result = mqtt_client.publish(
            topic=topic,
            payload=payload,
            qos=0,
            retain=False
        )

        log(
            f"MQTT PUBLISH RESULT: "
            f"rc={result.rc}, "
            f"mid={result.mid}"
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_error = (
                f"MQTT publish failed: "
                f"rc={result.rc}"
            )

            log(
                f"MQTT PUBLISH FAILED: "
                f"{last_error}"
            )

            return False

        # ----------------------------------------------------
        # Give the MQTT network loop a short time to transmit.
        # ----------------------------------------------------

        time.sleep(0.5)

        log("MQTT COMMAND QUEUED FOR TRANSMISSION")

        last_error = None

        return True

    except Exception as error:

        last_error = str(error)

        log("MQTT COMMAND EXCEPTION")
        log(str(error))

        return False


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    return render_template(
        "index.html"
    )


# ============================================================
# API STATUS
# ============================================================

@app.route("/api/status")
def api_status():

    with state_lock:

        status = {
            "mqtt": {
                "connected": mqtt_connected
            },

            "devices": {
                "light": device_states["light"],
                "fan": device_states["fan"],
                "geyser": device_states["geyser"]
            },

            "sensors": {
                "temperature": sensor_data["temperature"],
                "humidity": sensor_data["humidity"],
                "gas": sensor_data["gas"],
                "gas_raw": sensor_data["gas_raw"]
            },

            "last_status_received": (
                last_status_time
            ),

            "last_error": last_error
        }

    return jsonify(status)


# ============================================================
# DEVICE CONTROL
# ============================================================

@app.route(
    "/api/device/<device>/<action>",
    methods=["POST"]
)
def control_device(
    device,
    action
):

    device = device.lower()
    action = action.upper()

    log("")
    log("========================================")
    log("DEVICE CONTROL REQUEST")
    log(f"Device: {device}")
    log(f"Action: {action}")
    log("========================================")

    # --------------------------------------------------------
    # Validate device
    # --------------------------------------------------------

    topics = {
        "light": LIGHT_TOPIC,
        "fan": FAN_TOPIC,
        "geyser": GEYSER_TOPIC
    }

    if device not in topics:

        return jsonify({
            "success": False,
            "error": "Unknown device"
        }), 400

    # --------------------------------------------------------
    # Validate action
    # --------------------------------------------------------

    if action not in ["ON", "OFF"]:

        return jsonify({
            "success": False,
            "error": "Invalid action"
        }), 400

    # --------------------------------------------------------
    # Check MQTT connection
    # --------------------------------------------------------

    try:

        connected_now = (
            mqtt_client.is_connected()
        )

    except Exception:

        connected_now = False

    if not connected_now:

        log(
            "MQTT CLIENT IS NOT CONNECTED"
        )

        return jsonify({
            "success": False,
            "error": "MQTT is not connected"
        }), 503

    # --------------------------------------------------------
    # Publish
    # --------------------------------------------------------

    success = publish_command(
        topics[device],
        action
    )

    if not success:

        return jsonify({
            "success": False,
            "error": last_error or "MQTT publish failed"
        }), 503

    # --------------------------------------------------------
    # Do not pretend the physical device changed yet.
    #
    # ESP32 will report the real state through
    # home/status.
    # --------------------------------------------------------

    log(
        "COMMAND SENT TO MQTT"
    )

    return jsonify({
        "success": True,
        "device": device,
        "action": action,
        "topic": topics[device],
        "qos": 0,
        "message": "Command published successfully"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    try:

        connected = (
            mqtt_client.is_connected()
        )

    except Exception:

        connected = False

    return jsonify({
        "status": "ok",
        "mqtt_connected": connected,
        "last_error": last_error
    })


# ============================================================
# START LOCAL SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        ),
        debug=False
    )
