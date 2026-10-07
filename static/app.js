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
    }
};


// ===============================
// GET LATEST STATUS FROM FLASK
// ===============================
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

        // Update device states
        if (data.devices) {
            state.devices = {
                ...state.devices,
                ...data.devices
            };
        }

        // Update sensor values
        if (data.sensors) {
            state.sensors = {
                ...state.sensors,
                ...data.sensors
            };
        }

        updateDashboard();

    } catch (error) {
        console.error("Status refresh error:", error);
    }
}


// ===============================
// UPDATE DASHBOARD
// ===============================
function updateDashboard() {

    // -------------------------------
    // TEMPERATURE
    // -------------------------------
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


    // -------------------------------
    // HUMIDITY
    // -------------------------------
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


    // -------------------------------
    // GAS
    // -------------------------------
    const gasElement =
        document.getElementById("gas");

    if (gasElement) {
        gasElement.textContent =
            state.sensors.gas || "NORMAL";
    }


    // -------------------------------
    // GAS RAW VALUE
    // -------------------------------
    const gasRawElement =
        document.getElementById("gas-raw");

    if (gasRawElement) {
        gasRawElement.textContent =
            state.sensors.gas_raw ?? 0;
    }


    // -------------------------------
    // DEVICE STATES
    // -------------------------------
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


// ===============================
// UPDATE DEVICE DISPLAY
// ===============================
function updateDevice(device, status) {

    const value =
        String(status || "OFF").toUpperCase();


    // Device status text
    const statusElement =
        document.getElementById(
            device + "-status"
        );

    if (statusElement) {
        statusElement.textContent = value;
    }


    // Device card
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


    // Optional ON/OFF indicators
    const indicator =
        document.getElementById(
            device + "-indicator"
        );

    if (indicator) {
        indicator.textContent =
            value === "ON" ? "ON" : "OFF";
    }
}


// ===============================
// CONTROL LIGHT / FAN / GEYSER
// ===============================
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


        // Show requested state immediately
        state.devices[device] =
            action.toUpperCase();

        updateDashboard();


        // Ask Flask for actual ESP32 status
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


// ===============================
// INITIAL LOAD
// ===============================
refreshStatus();


// ===============================
// REFRESH EVERY 5 SECONDS
// ===============================
setInterval(
    refreshStatus,
    5000
);
