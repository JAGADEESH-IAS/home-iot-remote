const state = {
    devices: {
        light: "OFF",
        fan: "OFF",
        geyser: "OFF"
    },

    sensors: {
        temperature: 0,
        humidity: 0,
        gas: "NORMAL",
        gas_raw: 0
    },

    mqtt: {
        connected: false
    }
};


/* =========================================================
   REFRESH STATUS FROM FLASK
   ========================================================= */

async function refreshStatus() {

    try {

        const response = await fetch(
            "/api/status?t=" + Date.now(),
            {
                method: "GET",
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
            }
        );


        if (!response.ok) {
            throw new Error(
                "Status request failed: HTTP " +
                response.status
            );
        }


        const data = await response.json();


        console.log(
            "Fresh status received:",
            data
        );


        /* DEVICE STATUS */

        if (data.devices) {

            state.devices = {
                ...state.devices,
                ...data.devices
            };
        }


        /* SENSOR STATUS */

        if (data.sensors) {

            state.sensors = {
                ...state.sensors,
                ...data.sensors
            };
        }


        /* MQTT STATUS */

        if (data.mqtt) {

            state.mqtt = {
                ...state.mqtt,
                ...data.mqtt
            };
        }


        updateDashboard();


    } catch (error) {

        console.error(
            "Status refresh error:",
            error
        );


        /*
         * If Flask cannot be reached,
         * show MQTT as offline.
         */

        state.mqtt.connected = false;

        updateMQTTStatus();
    }
}


/* =========================================================
   UPDATE DASHBOARD
   ========================================================= */

function updateDashboard() {

    updateMQTTStatus();

    updateTemperature();

    updateHumidity();

    updateGas();

    updateDevice(
        "light",
        state.devices.light
    );

    updateDevice(
        "fan",
        state.devices.fan
    );

    updateDevice(
        "geyser",
        state.devices.geyser
    );
}


/* =========================================================
   MQTT STATUS
   ========================================================= */

function updateMQTTStatus() {

    const connected =
        state.mqtt.connected === true;


    console.log(
        "MQTT status:",
        connected
            ? "CONNECTED"
            : "OFFLINE"
    );


    /* -------------------------
       Top MQTT badge
       ------------------------- */

    const mqttBadge =
        document.getElementById(
            "mqttBadge"
        );


    if (mqttBadge) {

        mqttBadge.textContent =
            connected
                ? "● MQTT Connected"
                : "● MQTT Offline";


        mqttBadge.classList.remove(
            "offline"
        );


        mqttBadge.classList.remove(
            "online"
        );


        mqttBadge.classList.add(
            connected
                ? "online"
                : "offline"
        );
    }


    /* -------------------------
       Monitoring MQTT card
       ------------------------- */

    const mqttText =
        document.getElementById(
            "mqttText"
        );


    if (mqttText) {

        mqttText.textContent =
            connected
                ? "Connected"
                : "Offline";
    }
}


/* =========================================================
   TEMPERATURE
   ========================================================= */

function updateTemperature() {

    const element =
        document.getElementById(
            "temperature"
        );


    if (!element) {
        return;
    }


    const temperature =
        Number(
            state.sensors.temperature
        );


    if (Number.isFinite(temperature)) {

        element.textContent =
            temperature.toFixed(1) +
            " °C";
    }
}


/* =========================================================
   HUMIDITY
   ========================================================= */

function updateHumidity() {

    const element =
        document.getElementById(
            "humidity"
        );


    if (!element) {
        return;
    }


    const humidity =
        Number(
            state.sensors.humidity
        );


    if (Number.isFinite(humidity)) {

        element.textContent =
            humidity.toFixed(1) +
            " %";
    }
}


/* =========================================================
   GAS
   ========================================================= */

function updateGas() {

    const gasElement =
        document.getElementById(
            "gas"
        );


    if (gasElement) {

        gasElement.textContent =
            state.sensors.gas ||
            "NORMAL";
    }
}


/* =========================================================
   DEVICE STATUS
   ========================================================= */

function updateDevice(
    device,
    status
) {

    const value =
        String(
            status || "OFF"
        ).toUpperCase();


    /*
     * Your HTML uses:
     *
     * lightState
     * fanState
     * geyserState
     */

    const stateElement =
        document.getElementById(
            device + "State"
        );


    if (stateElement) {

        stateElement.textContent =
            value;


        stateElement.classList.remove(
            "on"
        );


        stateElement.classList.remove(
            "off"
        );


        stateElement.classList.add(
            value === "ON"
                ? "on"
                : "off"
        );
    }
}


/* =========================================================
   CONTROL DEVICE
   ========================================================= */

async function controlDevice(
    device,
    action
) {

    try {

        console.log(
            "Sending command:",
            device,
            action
        );


        /*
         * Send command to Flask.
         */

        const response =
            await fetch(
                "/api/device/" +
                encodeURIComponent(device) +
                "/" +
                encodeURIComponent(action),
                {
                    method: "POST",
                    cache: "no-store",
                    headers: {
                        "Cache-Control":
                            "no-cache",
                        "Pragma":
                            "no-cache"
                    }
                }
            );


        const result =
            await response.json();


        console.log(
            "Command response:",
            result
        );


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Command failed"
            );
        }


        /*
         * Command accepted by Flask.
         * Update dashboard immediately.
         */

        state.devices[device] =
            action.toUpperCase();


        updateDevice(
            device,
            state.devices[device]
        );


        console.log(
            "Command successfully sent:",
            device,
            action
        );


        /*
         * Get the actual ESP32 state
         * one second later.
         */

        setTimeout(
            refreshStatus,
            1000
        );


    } catch (error) {

        console.error(
            "Control error:",
            error
        );


        /*
         * Restore actual state from ESP32.
         */

        refreshStatus();
    }
}


/* =========================================================
   INITIAL LOAD
   ========================================================= */

refreshStatus();


/* =========================================================
   REFRESH EVERY 5 SECONDS
   ========================================================= */

setInterval(
    refreshStatus,
    5000
);
