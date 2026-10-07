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


async function refreshStatus() {
    try {
        const response = await fetch(
            "/api/status?t=" + Date.now(),
            {
                method: "GET",
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache"
                }
            }
        );

        if (!response.ok) {
            throw new Error(
                "Status request failed: HTTP " + response.status
            );
        }

        const data = await response.json();

        console.log("Fresh status received:", data);

        if (data.devices) {
            state.devices = {
                ...state.devices,
                ...data.devices
            };
        }

        if (data.sensors) {
            state.sensors = {
                ...state.sensors,
                ...data.sensors
            };
        }

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

        state.mqtt.connected = false;
        updateMQTTStatus();
    }
}


function updateDashboard() {

    updateMQTTStatus();


    const temperatureElement =
        document.getElementById("temperature");

    if (temperatureElement) {
        const temperature =
            Number(state.sensors.temperature);

        if (Number.isFinite(temperature)) {
            temperatureElement.textContent =
                temperature.toFixed(1) + " °C";
        }
    }


    const humidityElement =
        document.getElementById("humidity");

    if (humidityElement) {
        const humidity =
            Number(state.sensors.humidity);

        if (Number.isFinite(humidity)) {
            humidityElement.textContent =
                humidity.toFixed(1) + " %";
        }
    }


    const gasElement =
        document.getElementById("gas");

    if (gasElement) {
        gasElement.textContent =
            state.sensors.gas || "NORMAL";
    }


    const gasRawElement =
        document.getElementById("gas-raw");

    if (gasRawElement) {
        gasRawElement.textContent =
            state.sensors.gas_raw ?? 0;
    }


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


function updateMQTTStatus() {

    const connected =
        state.mqtt.connected === true;


    /*
     * Try several possible IDs so the existing
     * dashboard HTML does not need to be changed.
     */

    const possibleElements = [
        document.getElementById("mqtt-status"),
        document.getElementById("mqtt-badge"),
        document.getElementById("mqtt-indicator"),
        document.getElementById("mqtt-connection")
    ];


    possibleElements.forEach(element => {

        if (!element) {
            return;
        }

        element.textContent =
            connected
                ? "MQTT Connected"
                : "MQTT Offline";

        element.classList.toggle(
            "online",
            connected
        );

        element.classList.toggle(
            "offline",
            !connected
        );

        element.classList.toggle(
            "connected",
            connected
        );

        element.classList.toggle(
            "disconnected",
            !connected
        );
    });


    console.log(
        "MQTT dashboard status:",
        connected
            ? "CONNECTED"
            : "OFFLINE"
    );
}


function updateDevice(device, status) {

    const value =
        String(status || "OFF").toUpperCase();


    const statusElement =
        document.getElementById(
            device + "-status"
        );

    if (statusElement) {
        statusElement.textContent =
            value;
    }


    const card =
        document.getElementById(
            device + "-card"
        );

    if (card) {
        card.classList.toggle(
            "device-on",
            value === "ON"
        );
    }


    const indicator =
        document.getElementById(
            device + "-indicator"
        );

    if (indicator) {
        indicator.textContent =
            value === "ON"
                ? "ON"
                : "OFF";
    }
}


async function controlDevice(device, action) {

    try {

        console.log(
            "Sending command:",
            device,
            action
        );


        const response = await fetch(
            "/api/device/" +
            encodeURIComponent(device) +
            "/" +
            encodeURIComponent(action),
            {
                method: "POST",
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache"
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


        state.devices[device] =
            action.toUpperCase();


        updateDashboard();


        setTimeout(
            refreshStatus,
            1000
        );


    } catch (error) {

        console.error(
            "Control error:",
            error
        );
    }
}


/* Initial status */
refreshStatus();


/* Refresh every 5 seconds */
setInterval(
    refreshStatus,
    5000
);
