import os
import json
import threading
import uuid
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template
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

DEVICE_TOPICS = {
    "light": "home/light",
    "fan": "home/fan",
    "geyser": "home/geyser"
}


# ============================================================
# SHARED STATE
# ============================================================

state_lock = threading.Lock()
publish_lock = threading.Lock()

# Set when MQTT successfully connects.
mqtt_connected_event = threading.Event()


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
# MQTT CALLBACK: CONNECT
# ============================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    log("================================================")
    log(
        "MQTT CONNECTED CALLBACK: "
        f"reason_code={reason_code}"
    )

    if reason_code == 0:

        with state_lock:
            mqtt_state["connected"] = True
            mqtt_state["last_error"] = None

        mqtt_connected_event.set()

        log("MQTT CONNECTION SUCCESSFUL")

        # Subscribe to ESP32 status messages.
        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=1
        )

        log(
            "MQTT SUBSCRIBE: "
            f"topic={STATUS_TOPIC}, "
            f"result={result}, "
            f"mid={mid}"
        )

        if result == mqtt.MQTT_ERR_SUCCESS:
            log("MQTT STATUS SUBSCRIPTION ACCEPTED")
        else:
            log("MQTT STATUS SUBSCRIPTION FAILED")

    else:

        mqtt_connected_event.clear()

        with state_lock:
            mqtt_state["connected"] = False
            mqtt_state["last_error"] = str(
                reason_code
            )

        log(
            "MQTT CONNECTION FAILED: "
            f"{reason_code}"
        )


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

    mqtt_connected_event.clear()

    with state_lock:
        mqtt_state["connected"] = False
        mqtt_state["last_error"] = str(
            reason_code
        )

    log(
        "MQTT DISCONNECTED: "
        f"reason_code={reason_code}"
    )

    log(
        "MQTT BACKGROUND LOOP WILL HANDLE RECONNECT"
    )


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

    topic = message.topic

    try:

        payload = message.payload.decode(
            "utf-8"
        )

    except Exception as error:

        log(
            "MQTT PAYLOAD DECODE ERROR: "
            f"{error}"
        )

        return


    log(
        "MQTT MESSAGE RECEIVED: "
        f"topic={topic}"
    )

    log(
        f"MQTT PAYLOAD: {payload}"
    )


    # A message proves that the MQTT connection
    # is alive.

    with state_lock:

        mqtt_state["connected"] = True

        mqtt_state["last_message"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        mqtt_state["last_topic"] = topic

        mqtt_state["last_payload"] = payload


    # Only process home/status.
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


        with state_lock:

            # ------------------------------------------------
            # DEVICE STATES
            # ------------------------------------------------

            for device in (
                "light",
                "fan",
                "geyser"
            ):

                if device in devices:

                    value = str(
                        devices[device]
                    ).upper()

                    if value in (
                        "ON",
                        "OFF"
                    ):

                        device_state[
                            device
                        ] = value


            # ------------------------------------------------
            # SENSOR VALUES
            # ------------------------------------------------

            if "temperature" in sensors:

                sensor_state[
                    "temperature"
                ] = sensors["temperature"]


            if "humidity" in sensors:

                sensor_state[
                    "humidity"
                ] = sensors["humidity"]


            if "gas" in sensors:

                sensor_state[
                    "gas"
                ] = sensors["gas"]


            if "gas_raw" in sensors:

                sensor_state[
                    "gas_raw"
                ] = sensors["gas_raw"]


        log(
            "MQTT STATUS UPDATED SUCCESSFULLY"
        )

        log(
            "TEMPERATURE: "
            f"{sensor_state['temperature']}"
        )

        log(
            "HUMIDITY: "
            f"{sensor_state['humidity']}"
        )

        log(
            "GAS: "
            f"{sensor_state['gas']}"
        )


    except Exception as error:

        log(
            "MQTT STATUS UPDATE ERROR: "
            f"{error}"
        )


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

CLIENT_ID = (
    "flask-home-remote-"
    + uuid.uuid4().hex[:12]
)


log(
    f"MQTT CLIENT ID: {CLIENT_ID}"
)


mqtt_client = mqtt.Client(
    callback_api_version=
        mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT_ID
)


# MQTT username/password
mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# HiveMQ Cloud TLS
mqtt_client.tls_set()


# Automatic reconnect delay
mqtt_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30
)


# Register callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_subscribe = on_subscribe
mqtt_client.on_publish = on_publish
mqtt_client.on_message = on_message


# ============================================================
# START MQTT
# ============================================================

def start_mqtt():

    log("================================================")
    log("STARTING MQTT CLIENT")

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

    log("================================================")


    try:

        # Start Paho's background MQTT network loop.
        mqtt_client.loop_start()

        log(
            "MQTT BACKGROUND NETWORK LOOP STARTED"
        )


        # Start asynchronous connection.
        mqtt_client.connect_async(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        log(
            "MQTT ASYNC CONNECTION STARTED"
        )


    except Exception as error:

        with state_lock:

            mqtt_state[
                "connected"
            ] = False

            mqtt_state[
                "last_error"
            ] = str(error)


        log(
            "MQTT START ERROR: "
            f"{error}"
        )


# Start MQTT when Flask starts.
start_mqtt()


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

    with state_lock:

        response = {

            "devices":
                dict(device_state),

            "sensors":
                dict(sensor_state),

            "mqtt":
                dict(mqtt_state),

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

    with state_lock:

        response = {

            "broker":
                MQTT_BROKER,

            "port":
                MQTT_PORT,

            "username":
                MQTT_USERNAME,

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


    log("================================================")

    log(
        "DEVICE CONTROL REQUEST: "
        f"{device} -> {action}"
    )


    # --------------------------------------------------------
    # Validate device
    # --------------------------------------------------------

    if device not in DEVICE_TOPICS:

        return jsonify({

            "success": False,

            "error":
                "Unknown device"

        }), 400


    # --------------------------------------------------------
    # Validate action
    # --------------------------------------------------------

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


    try:

        # ====================================================
        # IMPORTANT:
        #
        # DO NOT use mqtt_client.is_connected() as a reason
        # to reject the command.
        #
        # The MQTT network loop may already be handling the
        # connection even if that property is temporarily false.
        #
        # We simply attempt the publish.
        # ====================================================

        log(
            "MQTT COMMAND PUBLISH: "
            f"{topic} -> {action}"
        )


        with publish_lock:

            result = mqtt_client.publish(

                topic=topic,

                payload=action,

                qos=1,

                retain=False
            )


            log(
                "MQTT PUBLISH RESULT: "
                f"rc={result.rc}, "
                f"mid={result.mid}"
            )


            # =================================================
            # If Paho explicitly reports NO_CONN:
            #
            # ask Paho to reconnect and retry once.
            # =================================================

            if result.rc == mqtt.MQTT_ERR_NO_CONN:

                log(
                    "MQTT PUBLISH REPORTS NO CONNECTION"
                )

                log(
                    "REQUESTING MQTT RECONNECT..."
                )


                mqtt_connected_event.clear()


                try:

                    # Use connect_async so the MQTT network
                    # loop remains in control.

                    mqtt_client.connect_async(
                        MQTT_BROKER,
                        MQTT_PORT,
                        keepalive=60
                    )

                    log(
                        "MQTT ASYNC RECONNECT REQUESTED"
                    )

                except Exception as reconnect_error:

                    log(
                        "MQTT RECONNECT REQUEST ERROR: "
                        f"{reconnect_error}"
                    )


                # Give the background loop time to connect.

                connected = (
                    mqtt_connected_event.wait(
                        timeout=5
                    )
                )


                if connected:

                    log(
                        "MQTT RECONNECTED - "
                        "RETRYING COMMAND"
                    )

                    result = mqtt_client.publish(

                        topic=topic,

                        payload=action,

                        qos=1,

                        retain=False
                    )


                    log(
                        "MQTT RETRY RESULT: "
                        f"rc={result.rc}, "
                        f"mid={result.mid}"
                    )

                else:

                    log(
                        "MQTT RECONNECT TIMEOUT"
                    )


            # =================================================
            # Check final publish result.
            # =================================================

            if result.rc != mqtt.MQTT_ERR_SUCCESS:

                log(
                    "MQTT COMMAND PUBLISH FAILED: "
                    f"rc={result.rc}"
                )


                with state_lock:

                    mqtt_state[
                        "last_command"
                    ] = (
                        f"{device}:{action}"
                    )

                    mqtt_state[
                        "last_command_result"
                    ] = (
                        f"FAILED rc={result.rc}"
                    )


                return jsonify({

                    "success": False,

                    "error":
                        (
                            "MQTT publish failed: "
                            f"{result.rc}"
                        ),

                    "device":
                        device,

                    "action":
                        action,

                    "topic":
                        topic

                }), 503


            # =================================================
            # Wait for Paho to confirm publication.
            # =================================================

            try:

                result.wait_for_publish(
                    timeout=5
                )

            except Exception as wait_error:

                log(
                    "MQTT WAIT FOR PUBLISH ERROR: "
                    f"{wait_error}"
                )


        # ====================================================
        # Final confirmation.
        # ====================================================

        if not result.is_published():

            log(
                "MQTT COMMAND WAS NOT CONFIRMED"
            )


            with state_lock:

                mqtt_state[
                    "last_command"
                ] = (
                    f"{device}:{action}"
                )

                mqtt_state[
                    "last_command_result"
                ] = "PUBLISH_TIMEOUT"


            return jsonify({

                "success": False,

                "error":
                    "MQTT publish timeout",

                "device":
                    device,

                "action":
                    action,

                "topic":
                    topic

            }), 503


        # ====================================================
        # SUCCESS
        # ====================================================

        log(
            "MQTT COMMAND SENT SUCCESSFULLY"
        )

        log(
            f"Topic: {topic}"
        )

        log(
            f"Message: {action}"
        )

        log(
            f"Message ID: {result.mid}"
        )


        with state_lock:

            mqtt_state[
                "last_command"
            ] = (
                f"{device}:{action}"
            )

            mqtt_state[
                "last_command_result"
            ] = (
                f"SUCCESS mid={result.mid}"
            )


        return jsonify({

            "success":
                True,

            "device":
                device,

            "action":
                action,

            "topic":
                topic,

            "message_id":
                result.mid
        })


    except Exception as error:

        log(
            "MQTT COMMAND ERROR: "
            f"{error}"
        )


        with state_lock:

            mqtt_state[
                "last_command"
            ] = (
                f"{device}:{action}"
            )

            mqtt_state[
                "last_command_result"
            ] = (
                f"ERROR: {error}"
            )


        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    with state_lock:

        connected = (
            mqtt_state["connected"]
        )


    return jsonify({

        "status":
            "ok",

        "mqtt_connected":
            connected
    })


# ============================================================
# LOCAL DEVELOPMENT
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
