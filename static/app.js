let lastData=null;
function getElement(id){return document.getElementById(id);}
function showMessage(t,type=""){const e=getElement("message");if(e){e.textContent=t;e.className="message "+type;}}
function updateMQTT(data){
 const b=getElement("mqttBadge"),t=getElement("mqttText");
 if(!data.mqtt)return;
 if(data.mqtt.connected){b.textContent="● MQTT Connected";b.classList.remove("offline");b.classList.add("online");t.textContent="Connected";}
 else{b.textContent="● MQTT Offline";b.classList.remove("online");b.classList.add("offline");t.textContent="Offline";}
}
function updateDevice(d,v){
 const e=getElement(d+"State");if(!e)return;
 const s=String(v||"OFF").toUpperCase();e.textContent=s;e.classList.remove("on","off");e.classList.add(s==="ON"?"on":"off");
}
function updateSensors(data){
 if(!data.sensors)return;
 const t=getElement("temperature"),h=getElement("humidity"),g=getElement("gas");
 if(data.sensors.temperature!=null)t.textContent=Number(data.sensors.temperature).toFixed(1)+" °C";
 if(data.sensors.humidity!=null)h.textContent=Number(data.sensors.humidity).toFixed(1)+" %";
 if(data.sensors.gas!=null)g.textContent=String(data.sensors.gas).toUpperCase();
}
function updateDashboard(data){
 if(!data)return;updateMQTT(data);
 if(data.devices){updateDevice("light",data.devices.light);updateDevice("fan",data.devices.fan);updateDevice("geyser",data.devices.geyser);}
 updateSensors(data);lastData=data;
}
async function fetchStatus(){
 try{
  const r=await fetch("/api/status?t="+Date.now(),{cache:"no-store",headers:{"Cache-Control":"no-cache"}});
  if(!r.ok)return;updateDashboard(await r.json());
 }catch(e){console.error("Dashboard update error:",e);}
}
async function controlDevice(device,action){
 showMessage("Sending "+action+" command to "+device+"...","sending");
 try{
  const r=await fetch("/api/device/"+encodeURIComponent(device)+"/"+encodeURIComponent(action)+"?t="+Date.now(),
    {method:"POST",cache:"no-store",headers:{"Cache-Control":"no-cache"}});
  let d={};try{d=await r.json();}catch(e){}
  if(!r.ok||!d.success){showMessage("Error: "+(d.error||"Command failed"),"error");return;}
  showMessage(device.toUpperCase()+" → "+action+" command sent","success");
  await fetchStatus();
  setTimeout(()=>showMessage(""),2500);
 }catch(e){console.error(e);showMessage("Connection error","error");}
}
document.addEventListener("DOMContentLoaded",()=>{fetchStatus();setInterval(fetchStatus,2000);});
