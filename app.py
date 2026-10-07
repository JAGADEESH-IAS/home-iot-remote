import os
import uuid
import time

from flask import Flask, jsonify
import paho.mqtt.client as mqtt


# ============================================================
# FLASK APP
# ============================================================

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
# MQTT TOPICS
# ============================================================

STATUS_TOPIC = "home/status"
LIGHT_TOPIC = "home/light"


# ============================================================
# MQTT STATE
# ============================================================

mqtt_connected = False

last_error = None

last_message = None

last_publish = None


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(message, flush=True)


# ============================================================
# MQTT CALLBACK: CONNECT
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

    log("========================================")
    log("MQTT CONNECT CALLBACK")

    log(
        f"Reason code: {reason_code}"
    )


    if reason_code == 0:

        mqtt_connected = True

        last_error = None

        log(
            "MQTT CONNECTED SUCCESSFULLY"
        )

        log(
            f"Broker: {MQTT_BROKER}"
        )

        log(
            f"Port: {MQTT_PORT}"
        )


        # ----------------------------------------------------
        # Subscribe to ESP32 status
        # ----------------------------------------------------

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=1
        )

        log(
            "MQTT STATUS SUBSCRIBE: "
            f"result={result}, "
            f"mid={mid}"
        )

    else:

        mqtt_connected = False

        last_error = (
            f"Connection failed: {reason_code}"
        )

        log(
            "MQTT CONNECTION FAILED"
        )

        log(
            f"Reason: {reason_code}"
        )


    log("========================================")


# ============================================================
# MQTT CALLBACK: DISCONNECT
# ============================================================

def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    global mqtt_connected
    global last_error

    mqtt_connected = False

    last_error = (
        f"Disconnected: {reason_code}"
    )

    log("========================================")

    log(
        "MQTT DISCONNECTED"
    )

    log(
        f"Reason code: {reason_code}"
    )

    log("========================================")


# ============================================================
# MQTT CALLBACK: SUBSCRIBE
# ============================================================

def on_subscribe(
    client,
    userdata,
    mid,
    reason_codes,
    properties=None
):

    log(
        "MQTT SUBSCRIBE CALLBACK: "
        f"mid={mid}, "
        f"reason_codes={reason_codes}"
    )


# ============================================================
# MQTT CALLBACK: PUBLISH
# ============================================================

def on_publish(
    client,
    userdata,
    mid,
    reason_code=None,
    properties=None
):

    log(
        "MQTT PUBLISH CALLBACK: "
        f"mid={mid}, "
        f"reason_code={reason_code}"
    )


# ============================================================
# MQTT CALLBACK: MESSAGE
# ============================================================

def on_message(
    client,
    userdata,
    message
):

    global mqtt_connected
    global last_message

    try:

        payload = message.payload.decode(
            "utf-8"
        )

    except Exception:

        payload = str(
            message.payload
        )


    # --------------------------------------------------------
    # IMPORTANT:
    # Receiving a message proves that MQTT is connected.
    # --------------------------------------------------------

    mqtt_connected = True

    last_message = {
        "topic": message.topic,
        "payload": payload
    }


    log("========================================")

    log(
        "MQTT MESSAGE RECEIVED"
    )

    log(
        f"Topic: {message.topic}"
    )

    log(
        f"Payload: {payload}"
    )

    log("========================================")


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

CLIENT_ID = (
    "flask-command-test-"
    + uuid.uuid4().hex[:10]
)


log("========================================")

log(
    "STARTING FLASK MQTT COMMAND TEST"
)

log(
    f"Client ID: {CLIENT_ID}"
)

log(
    f"Broker: {MQTT_BROKER}"
)

log(
    f"Port: {MQTT_PORT}"
)

log(
    "Username configured: "
    f"{bool(MQTT_USERNAME)}"
)

log(
    "Password configured: "
    f"{bool(MQTT_PASSWORD)}"
)

log("========================================")


# ============================================================
# CREATE CLIENT
# ============================================================

mqtt_client = mqtt.Client(
    callback_api_version=
        mqtt.CallbackAPIVersion.VERSION2,

    client_id=CLIENT_ID
)


# ============================================================
# MQTT AUTHENTICATION
# ============================================================

mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# ============================================================
# TLS
# ============================================================

mqtt_client.tls_set()


# ============================================================
# AUTOMATIC RECONNECT
# ============================================================

mqtt_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)


# ============================================================
# CALLBACK REGISTRATION
# ============================================================

mqtt_client.on_connect = on_connect

mqtt_client.on_disconnect = on_disconnect

mqtt_client.on_subscribe = on_subscribe

mqtt_client.on_publish = on_publish

mqtt_client.on_message = on_message


# ============================================================
# CONNECT TO HIVEMQ
# ============================================================

try:

    log(
        "CONNECTING TO HIVEMQ..."
    )


    mqtt_client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        keepalive=60
    )


    log(
        "MQTT TCP/TLS CONNECTION CREATED"
    )


    mqtt_client.loop_start()


    log(
        "MQTT BACKGROUND LOOP STARTED"
    )


except Exception as error:

    mqtt_connected = False

    last_error = str(
        error
    )

    log(
        "MQTT CONNECTION ERROR: "
        f"{error}"
    )


# ============================================================
# HOME / STATUS
# ============================================================

@app.route("/")
def home():

    return jsonify({

        "application":
            "HomeIoT MQTT Command Test",

        "broker":
            MQTT_BROKER,

        "port":
            MQTT_PORT,

        "mqtt_connected":
            mqtt_connected,

        "last_error":
            last_error,

        "last_message":
            last_message,

        "last_publish":
            last_publish
    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "ok",

        "mqtt_connected":
            mqtt_connected,

        "last_error":
            last_error,

        "last_message":
            last_message,

        "last_publish":
            last_publish
    })


# ============================================================
# TEST: LIGHT ON
# ============================================================

@app.route(
    "/test/light/on",
    methods=["GET"]
)
def test_light_on():

    global last_publish
    global last_error


    log("========================================")

    log(
        "FLASK LIGHT ON TEST"
    )


    try:

        # ----------------------------------------------------
        # DO NOT block based on mqtt_connected.
        #
        # We know MQTT can receive messages, so directly
        # attempt the publish.
        # ----------------------------------------------------

        log(
            "ATTEMPTING MQTT PUBLISH..."
        )


        result = mqtt_client.publish(

            topic=LIGHT_TOPIC,

            payload="ON",

            qos=1,

            retain=False
        )


        log(
            "MQTT PUBLISH RESULT: "
            f"rc={result.rc}, "
            f"mid={result.mid}"
        )


        # ----------------------------------------------------
        # Check Paho return code.
        # ----------------------------------------------------

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_publish = (
                f"FAILED rc={result.rc}"
            )

            last_error = (
                f"Publish failed: {result.rc}"
            )


            log(
                "FLASK -> HIVEMQ PUBLISH FAILED"
            )


            return jsonify({

                "success":
                    False,

                "error":
                    (
                        "MQTT publish failed"
                    ),

                "publish_rc":
                    result.rc,

                "message_id":
                    result.mid

            }), 503


        # ----------------------------------------------------
        # Wait for Paho to confirm publication.
        # ----------------------------------------------------

        try:

            result.wait_for_publish(
                timeout=5
            )

        except Exception as wait_error:

            log(
                "WAIT FOR PUBLISH ERROR: "
                f"{wait_error}"
            )


        # ----------------------------------------------------
        # Check final publication state.
        # ----------------------------------------------------

        if not result.is_published():

            last_publish = (
                "PUBLISH_TIMEOUT"
            )

            last_error = (
                "MQTT publish timeout"
            )


            log(
                "FLASK -> HIVEMQ PUBLISH TIMEOUT"
            )


            return jsonify({

                "success":
                    False,

                "error":
                    "MQTT publish timeout",

                "message_id":
                    result.mid

            }), 503


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        last_publish = (
            f"SUCCESS mid={result.mid}"
        )

        last_error = None


        log(
            "FLASK -> HIVEMQ PUBLISH SUCCESS"
        )

        log(
            "Topic: home/light"
        )

        log(
            "Message: ON"
        )

        log(
            f"Message ID: {result.mid}"
        )

        log("========================================")


        return jsonify({

            "success":
                True,

            "topic":
                LIGHT_TOPIC,

            "message":
                "ON",

            "message_id":
                result.mid

        })


    except Exception as error:

        last_publish = (
            f"ERROR: {error}"
        )

        last_error = str(
            error
        )


        log(
            "FLASK -> HIVEMQ PUBLISH ERROR: "
            f"{error}"
        )

        log("========================================")


        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# TEST: LIGHT OFF
# ============================================================

@app.route(
    "/test/light/off",
    methods=["GET"]
)
def test_light_off():

    global last_publish
    global last_error


    log("========================================")

    log(
        "FLASK LIGHT OFF TEST"
    )


    try:

        log(
            "ATTEMPTING MQTT PUBLISH..."
        )


        result = mqtt_client.publish(

            topic=LIGHT_TOPIC,

            payload="OFF",

            qos=1,

            retain=False
        )


        log(
            "MQTT PUBLISH RESULT: "
            f"rc={result.rc}, "
            f"mid={result.mid}"
        )


        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_publish = (
                f"FAILED rc={result.rc}"
            )

            last_error = (
                f"Publish failed: {result.rc}"
            )


            return jsonify({

                "success":
                    False,

                "error":
                    "MQTT publish failed",

                "publish_rc":
                    result.rc,

                "message_id":
                    result.mid

            }), 503


        try:

            result.wait_for_publish(
                timeout=5
            )

        except Exception as wait_error:

            log(
                "WAIT FOR PUBLISH ERROR: "
                f"{wait_error}"
            )


        if not result.is_published():

            last_publish = (
                "PUBLISH_TIMEOUT"
            )

            last_error = (
                "MQTT publish timeout"
            )


            return jsonify({

                "success":
                    False,

                "error":
                    "MQTT publish timeout",

                "message_id":
                    result.mid

            }), 503


        last_publish = (
            f"SUCCESS mid={result.mid}"
        )

        last_error = None


        log(
            "FLASK -> HIVEMQ PUBLISH SUCCESS"
        )

        log(
            "Topic: home/light"
        )

        log(
            "Message: OFF"
        )

        log(
            f"Message ID: {result.mid}"
        )

        log("========================================")


        return jsonify({

            "success":
                True,

            "topic":
                LIGHT_TOPIC,

            "message":
                "OFF",

            "message_id":
                result.mid

        })


    except Exception as error:

        last_publish = (
            f"ERROR: {error}"
        )

        last_error = str(
            error
        )


        log(
            "FLASK -> HIVEMQ PUBLISH ERROR: "
            f"{error}"
        )


        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# RUN FLASK
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        ),

        debug=False
    )
