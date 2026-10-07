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
# TOPICS
# ============================================================

STATUS_TOPIC = "home/status"

LIGHT_TOPIC = "home/light"


# ============================================================
# STATE
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
# MQTT CONNECT
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
    log(f"Reason code: {reason_code}")

    if reason_code == 0:

        mqtt_connected = True
        last_error = None

        log("MQTT CONNECTED SUCCESSFULLY")
        log(f"Broker: {MQTT_BROKER}")
        log(f"Port: {MQTT_PORT}")

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=1
        )

        log(
            "STATUS SUBSCRIBE RESULT: "
            f"rc={result}, mid={mid}"
        )

    else:

        mqtt_connected = False

        last_error = (
            f"MQTT connection failed: "
            f"{reason_code}"
        )

        log(
            "MQTT CONNECTION FAILED"
        )

    log("========================================")


# ============================================================
# MQTT DISCONNECT
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
        f"MQTT disconnected: "
        f"{reason_code}"
    )

    log("========================================")
    log("MQTT DISCONNECTED")
    log(f"Reason code: {reason_code}")
    log("========================================")


# ============================================================
# MQTT SUBSCRIBE
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
# MQTT PUBLISH CALLBACK
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
# MQTT MESSAGE
# ============================================================

def on_message(
    client,
    userdata,
    message
):

    global mqtt_connected
    global last_message

    mqtt_connected = True

    try:

        payload = message.payload.decode(
            "utf-8"
        )

    except Exception:

        payload = str(
            message.payload
        )


    last_message = {
        "topic": message.topic,
        "payload": payload
    }


    log("========================================")
    log("MQTT MESSAGE RECEIVED")
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
log("STARTING FLASK MQTT COMMAND TEST")
log(f"Client ID: {CLIENT_ID}")
log(f"Broker: {MQTT_BROKER}")
log(f"Port: {MQTT_PORT}")

log(
    "Username configured: "
    f"{bool(MQTT_USERNAME)}"
)

log(
    "Password configured: "
    f"{bool(MQTT_PASSWORD)}"
)

log("========================================")


mqtt_client = mqtt.Client(
    callback_api_version=
        mqtt.CallbackAPIVersion.VERSION2,

    client_id=CLIENT_ID
)


# ============================================================
# AUTHENTICATION
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
# RECONNECT SETTINGS
# ============================================================

mqtt_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)


# ============================================================
# CALLBACKS
# ============================================================

mqtt_client.on_connect = on_connect

mqtt_client.on_disconnect = on_disconnect

mqtt_client.on_subscribe = on_subscribe

mqtt_client.on_publish = on_publish

mqtt_client.on_message = on_message


# ============================================================
# CONNECT
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
        "MQTT CONNECTION CREATED"
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
# HOME
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
# LIGHT ON TEST
#
# IMPORTANT:
# QoS 0 for this diagnostic test.
#
# We deliberately do NOT call wait_for_publish().
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

        log(
            "ATTEMPTING MQTT PUBLISH"
        )

        log(
            "Topic: home/light"
        )

        log(
            "Message: ON"
        )

        log(
            "QoS: 0"
        )


        # ----------------------------------------------------
        # DIRECT PUBLISH
        # ----------------------------------------------------

        result = mqtt_client.publish(

            topic=LIGHT_TOPIC,

            payload="ON",

            qos=0,

            retain=False
        )


        log(
            "MQTT PUBLISH RETURNED: "
            f"rc={result.rc}, "
            f"mid={result.mid}"
        )


        # ----------------------------------------------------
        # Check Paho return code
        # ----------------------------------------------------

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_publish = (
                f"FAILED rc={result.rc}"
            )

            last_error = (
                f"Publish failed: "
                f"{result.rc}"
            )


            log(
                "PUBLISH FAILED"
            )

            log("========================================")


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


        # ----------------------------------------------------
        # QoS 0 does not wait for PUBACK.
        #
        # Give the background MQTT loop a short moment
        # to transmit the packet.
        # ----------------------------------------------------

        time.sleep(1)


        last_publish = (
            f"SUCCESS rc={result.rc}, "
            f"mid={result.mid}"
        )

        last_error = None


        log(
            "FLASK -> HIVEMQ COMMAND "
            "QUEUED SUCCESSFULLY"
        )

        log(
            "Topic: home/light"
        )

        log(
            "Message: ON"
        )

        log(
            "QoS: 0"
        )

        log("========================================")


        return jsonify({

            "success":
                True,

            "topic":
                LIGHT_TOPIC,

            "message":
                "ON",

            "qos":
                0,

            "message_id":
                result.mid,

            "note":
                (
                    "QoS 0 publish accepted by "
                    "the MQTT client"
                )
        })


    except Exception as error:

        last_publish = (
            f"ERROR: {error}"
        )

        last_error = str(
            error
        )


        log(
            "PUBLISH EXCEPTION: "
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
# LIGHT OFF TEST
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
            "ATTEMPTING MQTT PUBLISH"
        )

        log(
            "Topic: home/light"
        )

        log(
            "Message: OFF"
        )

        log(
            "QoS: 0"
        )


        result = mqtt_client.publish(

            topic=LIGHT_TOPIC,

            payload="OFF",

            qos=0,

            retain=False
        )


        log(
            "MQTT PUBLISH RETURNED: "
            f"rc={result.rc}, "
            f"mid={result.mid}"
        )


        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            last_publish = (
                f"FAILED rc={result.rc}"
            )

            last_error = (
                f"Publish failed: "
                f"{result.rc}"
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


        time.sleep(1)


        last_publish = (
            f"SUCCESS rc={result.rc}, "
            f"mid={result.mid}"
        )

        last_error = None


        log(
            "FLASK -> HIVEMQ COMMAND "
            "QUEUED SUCCESSFULLY"
        )

        log(
            "Topic: home/light"
        )

        log(
            "Message: OFF"
        )

        log(
            "QoS: 0"
        )

        log("========================================")


        return jsonify({

            "success":
                True,

            "topic":
                LIGHT_TOPIC,

            "message":
                "OFF",

            "qos":
                0,

            "message_id":
                result.mid,

            "note":
                (
                    "QoS 0 publish accepted by "
                    "the MQTT client"
                )
        })


    except Exception as error:

        last_publish = (
            f"ERROR: {error}"
        )

        last_error = str(
            error
        )


        log(
            "PUBLISH EXCEPTION: "
            f"{error}"
        )


        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# RUN
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
