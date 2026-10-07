import os
import time
import uuid

from flask import Flask, jsonify
import paho.mqtt.client as mqtt


app = Flask(__name__)


# ============================================================
# HIVEMQ CONFIGURATION
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
# DEBUG STATE
# ============================================================

last_error = None
last_message = None
last_publish = None


def log(message):
    print(message, flush=True)


# ============================================================
# STATUS CLIENT CALLBACKS
# ============================================================

def status_on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    global last_error

    log("")
    log("========================================")
    log("STATUS CLIENT CONNECT CALLBACK")
    log(f"Reason code: {reason_code}")
    log(f"Reason type: {type(reason_code)}")

    if reason_code == 0:

        last_error = None

        log("STATUS CLIENT CONNECTED")

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=1
        )

        log(
            f"STATUS SUBSCRIBE: "
            f"rc={result}, mid={mid}"
        )

    else:

        last_error = (
            f"Status connection failed: "
            f"{reason_code}"
        )

        log("STATUS CONNECTION FAILED")

    log("========================================")


def status_on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    log("")
    log("========================================")
    log("STATUS CLIENT DISCONNECTED")
    log(f"Reason code: {reason_code}")
    log("========================================")


def status_on_subscribe(
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


def status_on_message(
    client,
    userdata,
    message
):

    global last_message

    try:
        payload = message.payload.decode(
            "utf-8"
        )
    except Exception:
        payload = str(message.payload)

    last_message = {
        "topic": message.topic,
        "payload": payload
    }

    log("")
    log("========================================")
    log("STATUS MESSAGE RECEIVED")
    log(f"Topic: {message.topic}")
    log(f"Payload: {payload}")
    log("========================================")


# ============================================================
# STATUS MQTT CLIENT
# ============================================================

status_client_id = (
    "flask-status-" +
    uuid.uuid4().hex[:12]
)

log("")
log("========================================")
log("STARTING STATUS MQTT CLIENT")
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

status_client.on_connect = status_on_connect
status_client.on_disconnect = status_on_disconnect
status_client.on_subscribe = status_on_subscribe
status_client.on_message = status_on_message


try:

    status_client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        keepalive=60
    )

    status_client.loop_start()

    log("STATUS CLIENT STARTED")

except Exception as error:

    last_error = str(error)

    log("STATUS CLIENT ERROR")
    log(str(error))


# ============================================================
# COMMAND CLIENT CALLBACKS
# ============================================================

def command_on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    log("")
    log("----------------------------------------")
    log("COMMAND CLIENT CONNECT CALLBACK")
    log(f"Reason code: {reason_code}")
    log(f"Reason type: {type(reason_code)}")

    if reason_code == 0:
        log("COMMAND CLIENT CONNECTED TO HIVEMQ")
    else:
        log("COMMAND CLIENT CONNECTION FAILED")

    log("----------------------------------------")


def command_on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    log("")
    log("----------------------------------------")
    log("COMMAND CLIENT DISCONNECTED")
    log(f"Reason code: {reason_code}")
    log("----------------------------------------")


def command_on_publish(
    client,
    userdata,
    mid,
    reason_code=None,
    properties=None
):

    log("")
    log("----------------------------------------")
    log("COMMAND PUBLISH CALLBACK")
    log(f"Message ID: {mid}")
    log(f"Reason code: {reason_code}")
    log("----------------------------------------")


# ============================================================
# COMMAND PUBLISH TEST
# ============================================================

def publish_command(
    topic,
    payload,
    qos
):

    global last_error
    global last_publish

    client_id = (
        "flask-command-" +
        uuid.uuid4().hex[:12]
    )

    client = None

    log("")
    log("")
    log("########################################")
    log("STARTING COMMAND TEST")
    log(f"Client ID: {client_id}")
    log(f"Broker: {MQTT_BROKER}")
    log(f"Port: {MQTT_PORT}")
    log(f"Topic: {topic}")
    log(f"Payload: {payload}")
    log(f"QoS: {qos}")
    log("########################################")

    try:

        # ----------------------------------------------------
        # CREATE CLIENT
        # ----------------------------------------------------

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id
        )

        client.username_pw_set(
            MQTT_USERNAME,
            MQTT_PASSWORD
        )

        client.tls_set()

        client.on_connect = command_on_connect
        client.on_disconnect = command_on_disconnect
        client.on_publish = command_on_publish

        # ----------------------------------------------------
        # CONNECT
        # ----------------------------------------------------

        log("")
        log("CONNECTING TO HIVEMQ...")

        connect_result = client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        log(
            f"CONNECT RETURNED: "
            f"{connect_result}"
        )

        # ----------------------------------------------------
        # START NETWORK LOOP
        # ----------------------------------------------------

        client.loop_start()

        log("NETWORK LOOP STARTED")

        # ----------------------------------------------------
        # WAIT FOR CONNACK
        # ----------------------------------------------------

        connected = False

        for i in range(40):

            time.sleep(0.25)

            if client.is_connected():

                connected = True

                log(
                    "########################################"
                )

                log(
                    "MQTT CONNECTION CONFIRMED"
                )

                log(
                    f"After {(i + 1) * 0.25:.2f} seconds"
                )

                log(
                    "########################################"
                )

                break

        if not connected:

            last_error = (
                "MQTT client never became connected."
            )

            log("")
            log("MQTT CONNECTION FAILED")

            return {
                "success": False,
                "stage": "connect",
                "error": last_error
            }

        # ----------------------------------------------------
        # PUBLISH
        # ----------------------------------------------------

        log("")
        log("PUBLISHING NOW...")

        info = client.publish(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=False
        )

        log(
            f"PUBLISH RETURN CODE: "
            f"{info.rc}"
        )

        log(
            f"PUBLISH MESSAGE ID: "
            f"{info.mid}"
        )

        # ----------------------------------------------------
        # CHECK IMMEDIATE ERROR
        # ----------------------------------------------------

        if info.rc != mqtt.MQTT_ERR_SUCCESS:

            last_error = (
                f"Publish returned error "
                f"code {info.rc}"
            )

            log("PUBLISH FAILED IMMEDIATELY")

            return {
                "success": False,
                "stage": "publish",
                "error": last_error,
                "rc": info.rc,
                "message_id": info.mid
            }

        # ----------------------------------------------------
        # QOS 0
        # ----------------------------------------------------

        if qos == 0:

            log("")
            log(
                "QoS 0 selected."
            )

            log(
                "Waiting 3 seconds for "
                "network loop to transmit..."
            )

            time.sleep(3)

            log(
                "QoS 0 transmission window complete."
            )

            last_publish = {
                "topic": topic,
                "payload": payload,
                "qos": 0,
                "message_id": info.mid
            }

            return {
                "success": True,
                "stage": "qos0_publish",
                "topic": topic,
                "message": payload,
                "qos": 0,
                "message_id": info.mid,
                "note": (
                    "Paho accepted the QoS 0 "
                    "publication."
                )
            }

        # ----------------------------------------------------
        # QOS 1
        # ----------------------------------------------------

        log("")
        log(
            "QoS 1 selected."
        )

        log(
            "Waiting up to 10 seconds..."
        )

        try:

            info.wait_for_publish(
                timeout=10
            )

        except Exception as wait_error:

            log(
                f"wait_for_publish exception: "
                f"{wait_error}"
            )

        # ----------------------------------------------------
        # IMPORTANT:
        # CHECK is_published()
        # ----------------------------------------------------

        published = info.is_published()

        log("")
        log(
            f"is_published(): "
            f"{published}"
        )

        if published:

            log("")
            log(
                "########################################"
            )

            log(
                "QOS 1 PUBLISH COMPLETED"
            )

            log(
                "########################################"
            )

            last_error = None

            last_publish = {
                "topic": topic,
                "payload": payload,
                "qos": 1,
                "message_id": info.mid,
                "published": True
            }

            return {
                "success": True,
                "stage": "qos1_publish",
                "topic": topic,
                "message": payload,
                "qos": 1,
                "message_id": info.mid,
                "published": True
            }

        # ----------------------------------------------------
        # QOS 1 FAILED
        # ----------------------------------------------------

        last_error = (
            "Paho did not mark the QoS 1 "
            "message as published."
        )

        log("")
        log(
            "########################################"
        )
        log(
            "QOS 1 PUBLISH NOT COMPLETED"
        )
        log(
            "########################################"
        )

        return {
            "success": False,
            "stage": "qos1_publish",
            "error": last_error,
            "message_id": info.mid,
            "published": False
        }

    except Exception as error:

        last_error = str(error)

        log("")
        log("########################################")
        log("COMMAND EXCEPTION")
        log(str(error))
        log("########################################")

        return {
            "success": False,
            "stage": "exception",
            "error": str(error)
        }

    finally:

        if client is not None:

            try:
                client.loop_stop()
            except Exception:
                pass

            try:
                client.disconnect()
            except Exception:
                pass

            log(
                "COMMAND CLIENT CLOSED"
            )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    try:
        connected = status_client.is_connected()
    except Exception:
        connected = False

    return jsonify({
        "application": "HomeIoT MQTT Diagnostic",
        "broker": MQTT_BROKER,
        "port": MQTT_PORT,
        "status_mqtt_connected": connected,
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
        connected = status_client.is_connected()
    except Exception:
        connected = False

    return jsonify({
        "status": "ok",
        "status_mqtt_connected": connected,
        "last_error": last_error,
        "last_message": last_message,
        "last_publish": last_publish
    })


# ============================================================
# LIGHT ON - QOS 0
# ============================================================

@app.route("/test/light/on", methods=["GET"])
def light_on():

    result = publish_command(
        LIGHT_TOPIC,
        "ON",
        0
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# LIGHT OFF - QOS 0
# ============================================================

@app.route("/test/light/off", methods=["GET"])
def light_off():

    result = publish_command(
        LIGHT_TOPIC,
        "OFF",
        0
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# LIGHT ON - QOS 1
# ============================================================

@app.route("/test/light/on-qos1", methods=["GET"])
def light_on_qos1():

    result = publish_command(
        LIGHT_TOPIC,
        "ON",
        1
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# LIGHT OFF - QOS 1
# ============================================================

@app.route("/test/light/off-qos1", methods=["GET"])
def light_off_qos1():

    result = publish_command(
        LIGHT_TOPIC,
        "OFF",
        1
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# FAN ON
# ============================================================

@app.route("/test/fan/on", methods=["GET"])
def fan_on():

    result = publish_command(
        FAN_TOPIC,
        "ON",
        0
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# FAN OFF
# ============================================================

@app.route("/test/fan/off", methods=["GET"])
def fan_off():

    result = publish_command(
        FAN_TOPIC,
        "OFF",
        0
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# GEYSER ON
# ============================================================

@app.route("/test/geyser/on", methods=["GET"])
def geyser_on():

    result = publish_command(
        GEYSER_TOPIC,
        "ON",
        0
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# GEYSER OFF
# ============================================================

@app.route("/test/geyser/off", methods=["GET"])
def geyser_off():

    result = publish_command(
        GEYSER_TOPIC,
        "OFF",
        0
    )

    if result.get("success"):
        return jsonify(result), 200

    return jsonify(result), 503


# ============================================================
# START FLASK
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        ),
        debug=False
    )
