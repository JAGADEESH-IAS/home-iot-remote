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

        result, mid = client.subscribe(
            STATUS_TOPIC,
            qos=0
        )

        log(
            "MQTT SUBSCRIBE: "
            f"topic={STATUS_TOPIC}, "
            f"result={result}, "
            f"mid={mid}"
        )

    else:

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
        "MQTT network loop will attempt "
        "automatic reconnection."
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


    # If a message arrives, MQTT is clearly alive.
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

            # -------------------------------
            # DEVICE STATES
            # -------------------------------

            for device in (
                "light",
                "fan",
                "geyser"
            ):

                if device in devices:

                    value = str(
                        devices[device]
                    ).upper()

                    if value in ("ON", "OFF"):

                        device_state[device] = value


            # -------------------------------
            # SENSOR VALUES
            # -------------------------------

            if "temperature" in sensors:

                sensor_state["temperature"] = (
                    sensors["temperature"]
                )


            if "humidity" in sensors:

                sensor_state["humidity"] = (
                    sensors["humidity"]
                )


            if "gas" in sensors:

                sensor_state["gas"] = (
                    sensors["gas"]
                )


            if "gas_raw" in sensors:

                sensor_state["gas_raw"] = (
                    sensors["gas_raw"]
                )


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

mqtt_client.on_subscribe = on_subscribe

mqtt_client.on_publish = on_publish

mqtt_client.on_message = on_message


# ============================================================
# MQTT CONNECTION THREAD
# ============================================================

def mqtt_worker():

    log("================================================")
    log("STARTING MQTT CONNECTION")
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


    while True:

        try:

            if not mqtt_client.is_connected():

                log(
                    "MQTT CONNECT ATTEMPT"
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

                except Exception as error:

                    with state_lock:

                        mqtt_state["connected"] = False

                        mqtt_state["last_error"] = str(
                            error
                        )

                    log(
                        "MQTT CONNECT ERROR: "
                        f"{error}"
                    )

                    time.sleep(5)

                    continue


            # Run the MQTT network loop.
            mqtt_client.loop(
                timeout=1.0
            )


        except Exception as error:

            with state_lock:

                mqtt_state["connected"] = False

                mqtt_state["last_error"] = str(
                    error
                )

            log(
                "MQTT NETWORK ERROR: "
                f"{error}"
            )

            time.sleep(3)


mqtt_thread = threading.Thread(
    target=mqtt_worker,
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

    with state_lock:

        response = {
            "devices": dict(
                device_state
            ),

            "sensors": dict(
                sensor_state
            ),

            "mqtt": dict(
                mqtt_state
            ),

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
            "error": "Unknown device"
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

        # ----------------------------------------------------
        # Make sure MQTT is connected.
        # ----------------------------------------------------

        if not mqtt_client.is_connected():

            log(
                "MQTT IS NOT CONNECTED."
            )

            log(
                "ATTEMPTING IMMEDIATE RECONNECT..."
            )

            try:

                mqtt_client.reconnect()

                log(
                    "MQTT RECONNECT SUCCESSFUL"
                )

            except Exception as error:

                log(
                    "MQTT RECONNECT FAILED: "
                    f"{error}"
                )

                with state_lock:

                    mqtt_state[
                        "last_command"
                    ] = f"{device}:{action}"

                    mqtt_state[
                        "last_command_result"
                    ] = (
                        "RECONNECT_FAILED: "
                        f"{error}"
                    )

                return jsonify({

                    "success": False,

                    "error":
                        "MQTT connection unavailable"
                }), 503


        # ----------------------------------------------------
        # Publish command
        # ----------------------------------------------------

        log(
            "MQTT COMMAND PUBLISH: "
            f"{topic} -> {action}"
        )


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


        with state_lock:

            mqtt_state[
                "last_command"
            ] = f"{device}:{action}"

            mqtt_state[
                "last_command_result"
            ] = (
                f"rc={result.rc}, "
                f"mid={result.mid}"
            )


        # ----------------------------------------------------
        # Check publish result
        # ----------------------------------------------------

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            log(
                "MQTT COMMAND PUBLISH FAILED"
            )


            return jsonify({

                "success": False,

                "error":
                    f"MQTT publish failed: "
                    f"{result.rc}",

                "device":
                    device,

                "action":
                    action,

                "topic":
                    topic
            }), 503


        log(
            "MQTT COMMAND ACCEPTED"
        )


        return jsonify({

            "success": True,

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


        return jsonify({

            "success": False,

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

        "status": "ok",

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
