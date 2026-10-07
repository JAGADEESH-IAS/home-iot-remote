import os,json,threading
from datetime import datetime,timezone
from flask import Flask,jsonify,render_template
import paho.mqtt.client as mqtt

app=Flask(__name__)

MQTT_BROKER=os.getenv("MQTT_BROKER","bravetawny-af88996b.a02.usw2.aws.hivemq.cloud")
MQTT_PORT=int(os.getenv("MQTT_PORT","8883"))
MQTT_USERNAME=os.getenv("MQTT_USERNAME","")
MQTT_PASSWORD=os.getenv("MQTT_PASSWORD","")

STATUS_TOPIC="home/status"
DEVICE_TOPICS={"light":"home/light","fan":"home/fan","geyser":"home/geyser"}

lock=threading.Lock()
device_state={"light":"OFF","fan":"OFF","geyser":"OFF"}
sensor_state={"temperature":None,"humidity":None,"gas":"UNKNOWN","gas_raw":0}
mqtt_state={"connected":False,"last_error":None,"last_message":None,
            "last_topic":None,"last_payload":None,"last_command":None,
            "last_command_result":None}

def log(x): print(x,flush=True)

def on_connect(client,userdata,flags,reason_code,properties):
    log(f"MQTT CONNECT: reason_code={reason_code}")
    if reason_code==0:
        with lock:
            mqtt_state["connected"]=True
            mqtt_state["last_error"]=None
        r,mid=client.subscribe(STATUS_TOPIC,qos=0)
        log(f"MQTT SUBSCRIBE: {STATUS_TOPIC}, result={r}, mid={mid}")
    else:
        with lock:
            mqtt_state["connected"]=False
            mqtt_state["last_error"]=str(reason_code)

def on_disconnect(client,userdata,disconnect_flags,reason_code,properties):
    with lock:
        mqtt_state["connected"]=False
        mqtt_state["last_error"]=str(reason_code)
    log(f"MQTT DISCONNECTED: reason_code={reason_code}")

def on_subscribe(client,userdata,mid,reason_codes,properties=None):
    log(f"MQTT SUBSCRIBE CALLBACK: mid={mid}, reason_codes={reason_codes}")

def on_publish(client,userdata,mid,reason_code=None,properties=None):
    log(f"MQTT PUBLISH CALLBACK: mid={mid}, reason_code={reason_code}")

def on_message(client,userdata,message):
    topic=message.topic
    try: payload=message.payload.decode("utf-8")
    except Exception as e:
        log(f"MQTT PAYLOAD DECODE ERROR: {e}"); return
    log(f"MQTT MESSAGE RECEIVED: topic={topic}")
    log(f"MQTT PAYLOAD: {payload}")
    with lock:
        mqtt_state["last_message"]=datetime.now(timezone.utc).isoformat()
        mqtt_state["last_topic"]=topic
        mqtt_state["last_payload"]=payload
    if topic!=STATUS_TOPIC:return
    try:
        data=json.loads(payload)
        devices=data.get("devices",{})
        sensors=data.get("sensors",{})
        with lock:
            for d in ("light","fan","geyser"):
                if devices.get(d) is not None:
                    device_state[d]=str(devices[d]).upper()
            for k in ("temperature","humidity","gas","gas_raw"):
                if k in sensors:sensor_state[k]=sensors[k]
        log("MQTT STATUS UPDATED SUCCESSFULLY")
    except Exception as e: log(f"MQTT STATUS UPDATE ERROR: {e}")

mqtt_client=mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                        client_id="flask-home-remote-control")
mqtt_client.username_pw_set(MQTT_USERNAME,MQTT_PASSWORD)
mqtt_client.tls_set()
mqtt_client.on_connect=on_connect
mqtt_client.on_disconnect=on_disconnect
mqtt_client.on_subscribe=on_subscribe
mqtt_client.on_publish=on_publish
mqtt_client.on_message=on_message
mqtt_client.reconnect_delay_set(min_delay=2,max_delay=30)

def start_mqtt():
    log(f"STARTING MQTT: {MQTT_BROKER}:{MQTT_PORT}")
    try:
        mqtt_client.connect_async(MQTT_BROKER,MQTT_PORT,keepalive=60)
        mqtt_client.loop_start()
        log("MQTT NETWORK LOOP STARTED")
    except Exception as e:
        with lock:
            mqtt_state["connected"]=False
            mqtt_state["last_error"]=str(e)
        log(f"MQTT START ERROR: {e}")

threading.Thread(target=start_mqtt,daemon=True).start()

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/status")
def api_status():
    with lock:
        return jsonify({"devices":dict(device_state),"sensors":dict(sensor_state),
                        "mqtt":dict(mqtt_state),
                        "timestamp":datetime.now(timezone.utc).isoformat()})

@app.route("/api/mqtt")
def api_mqtt():
    with lock:
        return jsonify({"broker":MQTT_BROKER,"port":MQTT_PORT,
                        "username":MQTT_USERNAME,
                        "password_configured":bool(MQTT_PASSWORD),
                        "status_topic":STATUS_TOPIC,"device_topics":DEVICE_TOPICS,
                        **dict(mqtt_state)})

@app.route("/api/device/<device>/<action>",methods=["POST","GET"])
def control_device(device,action):
    device=device.lower().strip(); action=action.upper().strip()
    log(f"DEVICE CONTROL REQUEST: {device} -> {action}")
    if device not in DEVICE_TOPICS:
        return jsonify({"success":False,"error":"Unknown device"}),400
    if action not in ("ON","OFF"):
        return jsonify({"success":False,"error":"Action must be ON or OFF"}),400
    topic=DEVICE_TOPICS[device]
    try:
        if not mqtt_client.is_connected():
            log("CONTROL ERROR: MQTT CLIENT IS NOT CONNECTED")
            with lock:
                mqtt_state["last_command"]=f"{device}:{action}"
                mqtt_state["last_command_result"]="MQTT_NOT_CONNECTED"
            return jsonify({"success":False,"error":"MQTT client is not connected"}),503
        log(f"MQTT COMMAND PUBLISH: {topic} -> {action}")
        result=mqtt_client.publish(topic=topic,payload=action,qos=0,retain=False)
        log(f"MQTT PUBLISH RESULT: rc={result.rc}, mid={result.mid}")
        with lock:
            mqtt_state["last_command"]=f"{device}:{action}"
            mqtt_state["last_command_result"]=f"rc={result.rc},mid={result.mid}"
        if result.rc!=mqtt.MQTT_ERR_SUCCESS:
            return jsonify({"success":False,"error":f"MQTT publish failed: {result.rc}"}),500
        return jsonify({"success":True,"device":device,"action":action,
                        "topic":topic,"message_id":result.mid})
    except Exception as e:
        log(f"MQTT COMMAND ERROR: {e}")
        return jsonify({"success":False,"error":str(e)}),500

@app.route("/health")
def health():
    with lock:c=mqtt_state["connected"]
    return jsonify({"status":"ok","mqtt_connected":c})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=False)
