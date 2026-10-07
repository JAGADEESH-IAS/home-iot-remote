import os
import time
import uuid

from flask import Flask, jsonify
import paho.mqtt.client as mqtt


app = Flask(__name__)


# ============================================================
# HIVEMQ CLOUD CONFIGURATION
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
# MQTT TOPICS
# ============================================================

LIGHT_TOPIC = "home/light"
FAN_TOPIC = "home/fan"
GEYSER_TOPIC = "home/geyser"
STATUS_TOPIC = "home/status"


# ============================================================
# DEBUG INFORMATION
# ============================================================

last_error = None
last_message = None
last_publish = None


def log(message):
    print(message, flush=True)


# ============================================================
# STATUS MQTT CALLBACKS
# ============================================================

def on_status_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):
    global last_error

    log("")
    log("========================================")
    log("STATUS MQTT CONNECT CALLBACK")
    log(f"Reason code: {reason_code}")

    if reason_code == 0:

        last_error = None

        log("STATUS MQTT CONNECTED SUCCESSFULLY")
        log(f"Broker: {MQTT_BROKER}")
        log(f"Port: {MQTT_PORT}")

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=1
        )

        log(
            f"STATUS SUBSCRIBE RESULT: "
            f"rc={result}, mid={mid}"
        )

    else:

        last_error = (
            f"Status MQTT connection failed: "
            f"{reason_code}"
        )

        log("STATUS MQTT CONNECTION FAILED")

    log("========================================")


def on_status_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):
    log("")
    log("========================================")
    log("STATUS MQTT DISCONNECTED")
    log(f"Reason code: {reason_code}")
    log("========================================")


def on_status_subscribe(
    client,
    userdata,
    mid,
    reason_codes,
    properties=None
):
    log(
        f"STATUS SUBSCRIBE CALLBACK: "
        f"mid={mid}, "
        f"reason_codes={reason_codes}"
    )


def on_status_message(
    client,
    userdata,
    message
):
    global last_message

    try:
        payload = message.payload.decode("utf-8")
    except Exception:
        payload = str(message.payload)

    last_message = {
        "topic": message.topic,
        "payload": payload
    }

    log("")
    log("========================================")
    log("MQTT STATUS MESSAGE RECEIVED")
    log(f"Topic: {message.topic}")
    log(f"Payload: {payload}")
    log("========================================")


# ============================================================
# START STATUS MQTT CLIENT
# ============================================================

status_client_id = (
    "flask-status-" +
    uuid.uuid4().hex[:12]
)

log("")
log("========================================")
log("STARTING FLASK STATUS MQTT CLIENT")
log(f"Client ID: {status_client_id}")
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


status_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=status_client_id
)

status_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)

status_client.tls_set()

status_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)

status_client.on_connect = on_status_connect
status_client.on_disconnect = on_status_disconnect
status_client.on_subscribe = on_status_subscribe
status_client.on_message = on_status_message


try:

    log("CONNECTING STATUS CLIENT TO HIVEMQ...")

    status_client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        keepalive=60
    )

    log("STATUS CLIENT CONNECTION CREATED")

    status_client.loop_start()

    log("STATUS CLIENT BACKGROUND LOOP STARTED")

except Exception as error:

    last_error = str(error)

    log("STATUS CLIENT CONNECTION ERROR")
    log(str(error))


# ============================================================
# ONE-SHOT MQTT COMMAND
# ============================================================

def publish_command(topic, payload):

    global last_error
    global last_publish

    command_client_id = (
        "flask-command-" +
        uuid.uuid4().hex[:12]
    )

    command_client = None

    log("")
    log("")
    log("########################################")
    log("STARTING ONE-SHOT MQTT COMMAND")
    log(f"Client ID: {command_client_id}")
    log(f"Broker: {MQTT_BROKER}")
    log(f"Port: {MQTT_PORT}")
    log(f"Topic: {topic}")
    log(f"Payload: {payload}")
    log("QoS: 1")
    log("########################################")

    try:

        # ----------------------------------------------------
        # CREATE NEW MQTT CLIENT
        # ----------------------------------------------------

        command_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=command_client_id
        )

        command_client.username_pw_set(
            MQTT_USERNAME,
            MQTT_PASSWORD
        )

        command_client.tls_set()

        command_client.reconnect_delay_set(
            min_delay=2,
            max_delay=10
        )

        # ----------------------------------------------------
        # CONNECT TO HIVEMQ
        # ----------------------------------------------------

        log("")
        log("CONNECTING ONE-SHOT CLIENT TO HIVEMQ...")

        connect_result = command_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        log(
            f"CONNECT() RETURNED: "
            f"{connect_result}"
        )

        # ----------------------------------------------------
        # START MQTT NETWORK LOOP
        # ----------------------------------------------------

        command_client.loop_start()

        log(
            "ONE-SHOT MQTT LOOP STARTED"
        )

        # ----------------------------------------------------
        # WAIT FOR CONNECTION
        # ----------------------------------------------------

        connected = False

        for attempt in range(20):

            time.sleep(0.25)

            try:
                if command_client.is_connected():

                    connected = True

                    log(
                        "MQTT CONNECTION CONFIRMED"
                    )

                    log(
                        f"Connection confirmation "
                        f"time: "
                        f"{(attempt + 1) * 0.25:.2f} seconds"
                    )

                    break

            except Exception as check_error:

                log(
                    f"Connection check error: "
                    f"{check_error}"
                )

        # ----------------------------------------------------
        # CONNECTION FAILED
        # ----------------------------------------------------

        if not connected:

            last_error = (
                "One-shot MQTT client did not "
                "connect to HiveMQ."
            )

            log("")
            log("########################################")
            log("MQTT CONNECTION FAILED")
            log(
                "command_client.is_connected() = FALSE"
            )
            log("########################################")

            return {
                "success": False,
                "stage": "mqtt_connect",
                "error": last_error
            }

        # ----------------------------------------------------
        # CONNECTION SUCCESS
        # ----------------------------------------------------

        log("")
        log("MQTT CONNECTION IS ACTIVE")
        log("Preparing MQTT publish...")

        # ----------------------------------------------------
        # PUBLISH
        # ----------------------------------------------------

        publish_result = command_client.publish(
            topic=topic,
            payload=payload,
            qos=1,
            retain=False
        )

        log("")
        log("MQTT PUBLISH RETURNED")
        log(
            f"Return code: "
            f"{publish_result.rc}"
        )
        log(
            f"Message ID: "
            f"{publish_result.mid}"
        )

        # ----------------------------------------------------
        # CHECK PUBLISH RETURN CODE
        # ----------------------------------------------------

        if publish_result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_error = (
                f"MQTT publish failed. "
                f"rc={publish_result.rc}"
            )

            log("")
            log("########################################")
            log("MQTT PUBLISH FAILED")
            log(f"Error: {last_error}")
            log("########################################")

            return {
                "success": False,
                "stage": "publish",
                "error": last_error,
                "publish_rc": publish_result.rc,
                "message_id": publish_result.mid
            }

        # ----------------------------------------------------
        # WAIT FOR PUBLISH COMPLETION
        # ----------------------------------------------------

        log("")
        log(
            "WAITING FOR MQTT PUBLISH COMPLETION..."
        )

        published = publish_result.wait_for_publish(
            timeout=10
        )

        log(
            f"WAIT_FOR_PUBLISH RESULT: "
            f"{published}"
        )

        # ----------------------------------------------------
        # PUBLISH TIMEOUT
        # ----------------------------------------------------

        if not published:

            last_error = (
                "MQTT publish was accepted by "
                "Paho but was not completed "
                "within 10 seconds."
            )

            log("")
            log("########################################")
            log("PUBLISH COMPLETION TIMEOUT")
            log(
                "The MQTT broker did not confirm "
                "the QoS 1 publication."
            )
            log("########################################")

            return {
                "success": False,
                "stage": "publish_wait",
                "error": last_error,
                "message_id": publish_result.mid
            }

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        last_error = None

        last_publish = {
            "topic": topic,
            "payload": payload,
            "qos": 1,
            "message_id": publish_result.mid,
            "success": True
        }

        log("")
        log("########################################")
        log("MQTT COMMAND PUBLISHED SUCCESSFULLY")
        log(f"Topic: {topic}")
        log(f"Payload: {payload}")
        log(
            f"Message ID: "
            f"{publish_result.mid}"
        )
        log("########################################")

        return {
            "success": True,
            "topic": topic,
            "message": payload,
            "qos": 1,
            "message_id": publish_result.mid,
            "note": (
                "HiveMQ acknowledged the "
                "QoS 1 publish."
            )
        }

    except Exception as error:

        last_error = str(error)

        log("")
        log("########################################")
        log("MQTT COMMAND EXCEPTION")
        log(str(error))
        log("########################################")

        return {
            "success": False,
            "stage": "exception",
            "error": str(error)
        }

    finally:

        # ----------------------------------------------------
        # STOP NETWORK LOOP
        # ----------------------------------------------------

        if command_client is not None:

            try:
                command_client.loop_stop()
            except Exception:
                pass

            try:
                command_client.disconnect()
            except Exception:
                pass

            log(
                "ONE-SHOT MQTT CLIENT CLOSED"
            )


# ============================================================
# HOME / DEBUG INFORMATION
# ============================================================

@app.route("/")
def home():

    try:
        status_connected = (
            status_client.is_connected()
        )
    except Exception:
        status_connected = False

    return jsonify({
        "application": "HomeIoT MQTT Command Test",
        "broker": MQTT_BROKER,
        "port": MQTT_PORT,
        "status_mqtt_connected": status_connected,
        "last_error": last_error,
        "last_message": last_message,
        "last_publish": last_publish
    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    try:
        status_connected = (
            status_client.is_connected()
        )
    except Exception:
        status_connected = False

    return jsonify({
        "status": "ok",
        "status_mqtt_connected": status_connected,
        "last_error": last_error,
        "last_message": last_message,
        "last_publish": last_publish
    })


# ============================================================
# LIGHT ON
# ============================================================

@app.route("/test/light/on", methods=["GET"])
def test_light_on():

    log("")
    log("========================================")
    log("FLASK LIGHT ON REQUEST")
    log("========================================")

    result = publish_command(
        LIGHT_TOPIC,
        "ON"
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# LIGHT OFF
# ============================================================

@app.route("/test/light/off", methods=["GET"])
def test_light_off():

    log("")
    log("========================================")
    log("FLASK LIGHT OFF REQUEST")
    log("========================================")

    result = publish_command(
        LIGHT_TOPIC,
        "OFF"
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# FAN ON
# ============================================================

@app.route("/test/fan/on", methods=["GET"])
def test_fan_on():

    log("")
    log("========================================")
    log("FLASK FAN ON REQUEST")
    log("========================================")

    result = publish_command(
        FAN_TOPIC,
        "ON"
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# FAN OFF
# ============================================================

@app.route("/test/fan/off", methods=["GET"])
def test_fan_off():

    log("")
    log("========================================")
    log("FLASK FAN OFF REQUEST")
    log("========================================")

    result = publish_command(
        FAN_TOPIC,
        "OFF"
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# GEYSER ON
# ============================================================

@app.route("/test/geyser/on", methods=["GET"])
def test_geyser_on():

    log("")
    log("========================================")
    log("FLASK GEYSER ON REQUEST")
    log("========================================")

    result = publish_command(
        GEYSER_TOPIC,
        "ON"
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# GEYSER OFF
# ============================================================

@app.route("/test/geyser/off", methods=["GET"])
def test_geyser_off():

    log("")
    log("========================================")
    log("FLASK GEYSER OFF REQUEST")
    log("========================================")

    result = publish_command(
        GEYSER_TOPIC,
        "OFF"
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        ),
        debug=False
    )
