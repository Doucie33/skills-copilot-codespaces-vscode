#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_now.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <ArduinoOTA.h>
#include <Wire.h>

// ====== Métadonnées demandées ======
String CODE_NAME = "ESC_LoRa";
String CODE_VERSION = "v2.0.0";
String MODULE_NAME = "ESC_LoRa_Module";
bool HAS_OLED = true;

// ====== Modes ======
enum NodeMode { MODE_MASTER = 0, MODE_SLAVE = 1, MODE_RELAY = 2 };
NodeMode currentMode = MODE_SLAVE;

// ====== Réseau ======
String wifiSSID = "";
String wifiPASS = "";
String apPass = "12345678";
String loraNetworkName = "ESC_LoRa_Mesh";
String mqttHost = "192.168.4.2";
uint16_t mqttPort = 1883;
String mqttUser = "";
String mqttPass = "";

// ====== Paramètres ======
uint32_t heartbeatPeriodMs = 30UL * 60UL * 1000UL; // 30 min
uint32_t staleDataPollMs = 10UL * 60UL * 1000UL;
uint32_t deepSleepSec = 0;
bool hidePasswordsOnWeb = true;
bool gpsEnabled = false;

// ====== Objet globaux ======
Preferences prefs;
WebServer server(80);
WiFiClient espClient;
PubSubClient mqtt(espClient);

// ====== Identité module ======
String moduleId;
String apSSID;

// ====== Structures ESPNOW ======
#define MAX_PEERS 20
struct PeerInfo {
  uint8_t mac[6];
  String id;
  bool paired;
  uint32_t lastSeen;
  uint32_t lastSensorUpdate;
  bool online;
};

PeerInfo peers[MAX_PEERS];
uint8_t peerCount = 0;

struct MeshPacket {
  char type[16];
  char sourceId[24];
  char targetId[24];
  char payload[220];
};

// ====== État capteurs (exemple extensible) ======
struct SensorState {
  float dhtTemp = NAN;
  float dhtHum = NAN;
  float pressure = NAN;
  float airQuality = NAN;
  float thermoK = NAN;
  float current = NAN;
  float batteryV = NAN;
  int rssi = 0;
};
SensorState currentSensors;
SensorState lastSentSensors;

// ====== Utilitaires ======
String macToString(const uint8_t *mac) {
  char buf[18];
  snprintf(buf, sizeof(buf), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(buf);
}

String getModeLabel() {
  if (currentMode == MODE_MASTER) return "master";
  if (currentMode == MODE_RELAY) return "relay";
  return "slave";
}

String buildStateTopic() {
  return "esc_lora/" + moduleId + "/state";
}

String buildCmdTopic() {
  return "esc_lora/" + moduleId + "/cmd";
}

String buildAttributesTopic() {
  return "esc_lora/" + moduleId + "/attributes";
}

bool sensorChanged(float a, float b, float eps = 0.05f) {
  if (isnan(a) && isnan(b)) return false;
  if (isnan(a) != isnan(b)) return true;
  return fabs(a - b) > eps;
}

bool shouldSendSensorUpdate() {
  return sensorChanged(currentSensors.dhtTemp, lastSentSensors.dhtTemp)
      || sensorChanged(currentSensors.dhtHum, lastSentSensors.dhtHum)
      || sensorChanged(currentSensors.pressure, lastSentSensors.pressure)
      || sensorChanged(currentSensors.airQuality, lastSentSensors.airQuality)
      || sensorChanged(currentSensors.thermoK, lastSentSensors.thermoK)
      || sensorChanged(currentSensors.current, lastSentSensors.current)
      || sensorChanged(currentSensors.batteryV, lastSentSensors.batteryV)
      || currentSensors.rssi != lastSentSensors.rssi;
}

// ====== Persistance ======
void loadConfig() {
  prefs.begin("esc_lora", true);
  CODE_NAME = prefs.getString("code_name", CODE_NAME);
  CODE_VERSION = prefs.getString("version", CODE_VERSION);
  MODULE_NAME = prefs.getString("mod_name", MODULE_NAME);
  wifiSSID = prefs.getString("wifi_ssid", wifiSSID);
  wifiPASS = prefs.getString("wifi_pass", wifiPASS);
  apPass = prefs.getString("ap_pass", apPass);
  mqttHost = prefs.getString("mqtt_host", mqttHost);
  mqttPort = prefs.getUInt("mqtt_port", mqttPort);
  mqttUser = prefs.getString("mqtt_user", mqttUser);
  mqttPass = prefs.getString("mqtt_pass", mqttPass);
  loraNetworkName = prefs.getString("lora_name", loraNetworkName);
  hidePasswordsOnWeb = prefs.getBool("hide_pwd", hidePasswordsOnWeb);
  heartbeatPeriodMs = prefs.getULong("hb_ms", heartbeatPeriodMs);
  staleDataPollMs = prefs.getULong("stale_ms", staleDataPollMs);
  deepSleepSec = prefs.getUInt("sleep_sec", deepSleepSec);
  gpsEnabled = prefs.getBool("gps_en", gpsEnabled);
  currentMode = (NodeMode)prefs.getUChar("mode", MODE_SLAVE);
  HAS_OLED = prefs.getBool("oled", HAS_OLED);
  prefs.end();
}

void saveConfig() {
  prefs.begin("esc_lora", false);
  prefs.putString("code_name", CODE_NAME);
  prefs.putString("version", CODE_VERSION);
  prefs.putString("mod_name", MODULE_NAME);
  prefs.putString("wifi_ssid", wifiSSID);
  prefs.putString("wifi_pass", wifiPASS);
  prefs.putString("ap_pass", apPass);
  prefs.putString("mqtt_host", mqttHost);
  prefs.putUInt("mqtt_port", mqttPort);
  prefs.putString("mqtt_user", mqttUser);
  prefs.putString("mqtt_pass", mqttPass);
  prefs.putString("lora_name", loraNetworkName);
  prefs.putBool("hide_pwd", hidePasswordsOnWeb);
  prefs.putULong("hb_ms", heartbeatPeriodMs);
  prefs.putULong("stale_ms", staleDataPollMs);
  prefs.putUInt("sleep_sec", deepSleepSec);
  prefs.putBool("gps_en", gpsEnabled);
  prefs.putUChar("mode", (uint8_t)currentMode);
  prefs.putBool("oled", HAS_OLED);
  prefs.end();
}

// ====== MQTT ======
void publishDiscovery(const String& key, const String& name, const String& deviceClass = "", const String& unit = "") {
  if (!mqtt.connected()) return;
  String topic = "homeassistant/sensor/" + moduleId + "/" + key + "/config";
  DynamicJsonDocument doc(512);
  doc["name"] = name;
  doc["uniq_id"] = moduleId + "_" + key;
  doc["stat_t"] = buildStateTopic();
  doc["json_attr_t"] = buildAttributesTopic();
  doc["val_tpl"] = "{{ value_json." + key + " }}";
  if (deviceClass.length()) doc["dev_cla"] = deviceClass;
  if (unit.length()) doc["unit_of_meas"] = unit;
  JsonObject dev = doc.createNestedObject("dev");
  dev["ids"][0] = moduleId;
  dev["name"] = MODULE_NAME;
  dev["mf"] = "LilyGO";
  dev["mdl"] = "T3 S3 LR1121 / T-Beam SX1276";
  dev["sw"] = CODE_VERSION;

  String payload;
  serializeJson(doc, payload);
  mqtt.publish(topic.c_str(), payload.c_str(), true);
}

void publishDynamicSensorDiscovery(const JsonArray& sensors) {
  for (JsonVariant s : sensors) {
    String key = s["key"] | "sensor";
    String name = s["name"] | key;
    String devCl = s["device_class"] | "";
    String unit = s["unit"] | "";
    publishDiscovery(key, name, devCl, unit);
  }
}

void publishState() {
  if (!mqtt.connected()) return;

  DynamicJsonDocument doc(768);
  doc["id"] = moduleId;
  doc["name"] = MODULE_NAME;
  doc["version"] = CODE_VERSION;
  doc["mode"] = getModeLabel();
  doc["online"] = true;
  doc["rssi"] = currentSensors.rssi;
  doc["battery_v"] = currentSensors.batteryV;
  doc["dht_temp"] = currentSensors.dhtTemp;
  doc["dht_hum"] = currentSensors.dhtHum;
  doc["pressure"] = currentSensors.pressure;
  doc["air_quality"] = currentSensors.airQuality;
  doc["max6675_k"] = currentSensors.thermoK;
  doc["ly254_current"] = currentSensors.current;
  doc["lora_network"] = loraNetworkName;

  String payload;
  serializeJson(doc, payload);
  mqtt.publish(buildStateTopic().c_str(), payload.c_str(), true);

  DynamicJsonDocument attr(512);
  attr["module"] = MODULE_NAME;
  attr["code_name"] = CODE_NAME;
  attr["version"] = CODE_VERSION;
  attr["mode"] = getModeLabel();
  attr["oled"] = HAS_OLED;
  attr["gps_enabled"] = gpsEnabled;
  attr["mesh_peer_count"] = peerCount;

  String attrPayload;
  serializeJson(attr, attrPayload);
  mqtt.publish(buildAttributesTopic().c_str(), attrPayload.c_str(), true);
}

void mqttCallback(char* topic, byte* payload, unsigned int len) {
  String t(topic);
  String msg;
  for (unsigned int i = 0; i < len; i++) msg += (char)payload[i];

  if (t == buildCmdTopic()) {
    if (msg == "ping") {
      publishState();
    } else if (msg == "reboot") {
      ESP.restart();
    } else if (msg == "pair_clear" && currentMode == MODE_MASTER) {
      peerCount = 0;
    }
  }
}

void ensureMqtt() {
  if (mqtt.connected()) return;
  mqtt.setServer(mqttHost.c_str(), mqttPort);
  mqtt.setCallback(mqttCallback);

  String clientId = "esc_lora_" + moduleId;
  bool ok = mqttUser.length()
    ? mqtt.connect(clientId.c_str(), mqttUser.c_str(), mqttPass.c_str())
    : mqtt.connect(clientId.c_str());

  if (ok) {
    mqtt.subscribe(buildCmdTopic().c_str());
    publishDiscovery("battery_v", MODULE_NAME + " Batterie", "voltage", "V");
    publishDiscovery("rssi", MODULE_NAME + " RSSI", "signal_strength", "dBm");
    publishDiscovery("dht_temp", MODULE_NAME + " Température", "temperature", "°C");
    publishDiscovery("dht_hum", MODULE_NAME + " Humidité", "humidity", "%");
  }
}

// ====== ESPNOW ======
void ensurePeer(const uint8_t* mac, const String& id) {
  for (uint8_t i = 0; i < peerCount; i++) {
    if (memcmp(peers[i].mac, mac, 6) == 0) {
      peers[i].lastSeen = millis();
      peers[i].online = true;
      return;
    }
  }

  if (peerCount >= MAX_PEERS) return;
  memcpy(peers[peerCount].mac, mac, 6);
  peers[peerCount].id = id;
  peers[peerCount].paired = true;
  peers[peerCount].lastSeen = millis();
  peers[peerCount].lastSensorUpdate = millis();
  peers[peerCount].online = true;

  esp_now_peer_info_t p = {};
  memcpy(p.peer_addr, mac, 6);
  p.channel = 0;
  p.encrypt = false;
  if (!esp_now_is_peer_exist(mac)) {
    esp_now_add_peer(&p);
  }
  peerCount++;
}

void sendPacketTo(const uint8_t* mac, const char* type, const String& target, const String& payload) {
  MeshPacket pkt = {};
  strlcpy(pkt.type, type, sizeof(pkt.type));
  strlcpy(pkt.sourceId, moduleId.c_str(), sizeof(pkt.sourceId));
  strlcpy(pkt.targetId, target.c_str(), sizeof(pkt.targetId));
  strlcpy(pkt.payload, payload.c_str(), sizeof(pkt.payload));
  esp_now_send(mac, (uint8_t*)&pkt, sizeof(pkt));
}

void broadcastPacket(const char* type, const String& payload) {
  for (uint8_t i = 0; i < peerCount; i++) {
    sendPacketTo(peers[i].mac, type, peers[i].id, payload);
  }
}

void onEspNowRecv(const esp_now_recv_info_t *ri, const uint8_t *incomingData, int len) {
  if (len != sizeof(MeshPacket)) return;
  MeshPacket pkt;
  memcpy(&pkt, incomingData, sizeof(pkt));

  String type = pkt.type;
  String src = pkt.sourceId;
  String pay = pkt.payload;

  ensurePeer(ri->src_addr, src);

  if (type == "pair_req" && currentMode == MODE_MASTER) {
    sendPacketTo(ri->src_addr, "pair_ack", src, "ok");
  } else if (type == "pair_del" && currentMode == MODE_MASTER) {
    for (int i = peerCount - 1; i >= 0; i--) {
      if (peers[i].id == pay) {
        for (uint8_t j = i; j < peerCount - 1; j++) peers[j] = peers[j + 1];
        peerCount--;
      }
    }
  } else if (type == "sensor") {
    for (uint8_t i = 0; i < peerCount; i++) {
      if (peers[i].id == src) peers[i].lastSensorUpdate = millis();
    }
    if (currentMode == MODE_MASTER) {
      mqtt.publish(("esc_lora/" + src + "/state").c_str(), pay.c_str(), true);
    }
  } else if (type == "ping") {
    sendPacketTo(ri->src_addr, "pong", src, "alive");
  } else if (type == "pull_data") {
    DynamicJsonDocument doc(256);
    doc["id"] = moduleId;
    doc["battery_v"] = currentSensors.batteryV;
    doc["rssi"] = currentSensors.rssi;
    String out;
    serializeJson(doc, out);
    sendPacketTo(ri->src_addr, "sensor", src, out);
  }

  if (currentMode == MODE_RELAY) {
    broadcastPacket(pkt.type, pay);
  }
}

// ====== Web ======
String htmlHeader(const String& title) {
  return "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<title>" + title + "</title><style>body{font-family:sans-serif;max-width:920px;margin:20px auto;padding:0 12px}"
         "input,select,button,textarea{width:100%;padding:10px;margin:6px 0}fieldset{margin:10px 0}"
         ".row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.ok{color:green}.warn{color:#b45309}</style></head><body>"
         "<h1>🛰️ " + CODE_NAME + " - " + CODE_VERSION + "</h1>";
}

void handleRoot() {
  String s = htmlHeader("ESC_LoRa");
  s += "<p class='ok'>ID: <b>" + moduleId + "</b> | Mode: <b>" + getModeLabel() + "</b></p>";
  s += "<p>AP: <b>" + apSSID + "</b> | IP: <b>" + WiFi.localIP().toString() + "</b></p>";
  s += "<ul>"
       "<li><a href='/wifi'>⚙️ WiFi/MQTT/Mode</a></li>"
       "<li><a href='/gps'>📍 GPS</a></li>"
       "<li><a href='/sensors'>📈 Capteurs</a></li>"
       "<li><a href='/peers'>🔗 Appairage Mesh</a></li>"
       "</ul></body></html>";
  server.send(200, "text/html", s);
}

void handleWifi() {
  if (server.method() == HTTP_POST) {
    wifiSSID = server.arg("wifiSSID");
    wifiPASS = server.arg("wifiPASS");
    mqttHost = server.arg("mqttHost");
    mqttPort = server.arg("mqttPort").toInt();
    loraNetworkName = server.arg("loraName");
    MODULE_NAME = server.arg("moduleName");
    CODE_VERSION = server.arg("version");
    heartbeatPeriodMs = server.arg("heartbeatMin").toInt() * 60UL * 1000UL;
    currentMode = (NodeMode)server.arg("mode").toInt();
    HAS_OLED = server.hasArg("oled");
    hidePasswordsOnWeb = server.hasArg("hidepwd");
    saveConfig();
  }

  String type = hidePasswordsOnWeb ? "password" : "text";
  String s = htmlHeader("Paramètres");
  s += "<form method='post'><div class='row'>";
  s += "<div><label>SSID</label><input name='wifiSSID' value='" + wifiSSID + "'></div>";
  s += "<div><label>Mot de passe</label><input type='" + type + "' name='wifiPASS' value='" + wifiPASS + "'></div>";
  s += "<div><label>MQTT Host</label><input name='mqttHost' value='" + mqttHost + "'></div>";
  s += "<div><label>MQTT Port</label><input name='mqttPort' value='" + String(mqttPort) + "'></div>";
  s += "<div><label>Nom LoRa</label><input name='loraName' value='" + loraNetworkName + "'></div>";
  s += "<div><label>Nom module</label><input name='moduleName' value='" + MODULE_NAME + "'></div>";
  s += "<div><label>Version</label><input name='version' value='" + CODE_VERSION + "'></div>";
  s += "<div><label>Heartbeat (min)</label><input name='heartbeatMin' value='" + String(heartbeatPeriodMs / 60000UL) + "'></div>";
  s += "<div><label>Mode</label><select name='mode'>"
       "<option value='0'" + String(currentMode == MODE_MASTER ? " selected" : "") + ">Master</option>"
       "<option value='1'" + String(currentMode == MODE_SLAVE ? " selected" : "") + ">Slave</option>"
       "<option value='2'" + String(currentMode == MODE_RELAY ? " selected" : "") + ">Relay</option>"
       "</select></div></div>";
  s += "<label><input type='checkbox' name='oled'" + String(HAS_OLED ? " checked" : "") + "> OLED actif</label>";
  s += "<label><input type='checkbox' name='hidepwd'" + String(hidePasswordsOnWeb ? " checked" : "") + "> Masquer mots de passe</label>";
  s += "<button>💾 Sauvegarder</button></form><a href='/'>⬅️ Retour</a></body></html>";
  server.send(200, "text/html", s);
}

void handleGPS() {
  if (server.method() == HTTP_POST) {
    gpsEnabled = server.hasArg("gps");
    saveConfig();
  }
  String s = htmlHeader("GPS");
  s += "<form method='post'><label><input type='checkbox' name='gps'" + String(gpsEnabled ? " checked" : "") + "> GPS activé</label><button>💾 Enregistrer</button></form>";
  s += "<a href='/'>⬅️ Retour</a></body></html>";
  server.send(200, "text/html", s);
}

void handleSensors() {
  DynamicJsonDocument doc(512);
  doc["module"] = MODULE_NAME;
  doc["id"] = moduleId;
  doc["mode"] = getModeLabel();
  doc["battery_v"] = currentSensors.batteryV;
  doc["rssi"] = currentSensors.rssi;
  doc["dht_temp"] = currentSensors.dhtTemp;
  doc["dht_hum"] = currentSensors.dhtHum;
  doc["pressure"] = currentSensors.pressure;
  doc["air_quality"] = currentSensors.airQuality;
  doc["max6675_k"] = currentSensors.thermoK;
  doc["ly254_current"] = currentSensors.current;

  String out;
  serializeJsonPretty(doc, out);
  server.send(200, "application/json", out);
}

void handlePeers() {
  if (server.hasArg("delete") && currentMode == MODE_MASTER) {
    String id = server.arg("delete");
    for (int i = peerCount - 1; i >= 0; i--) {
      if (peers[i].id == id) {
        for (uint8_t j = i; j < peerCount - 1; j++) peers[j] = peers[j + 1];
        peerCount--;
      }
    }
  }

  String s = htmlHeader("Peers");
  s += "<h2>Appairage Mesh</h2><ul>";
  for (uint8_t i = 0; i < peerCount; i++) {
    s += "<li><b>" + peers[i].id + "</b> (" + macToString(peers[i].mac) + ") - " + (peers[i].online ? "🟢" : "🔴");
    if (currentMode == MODE_MASTER) s += " <a href='/peers?delete=" + peers[i].id + "'>❌ supprimer</a>";
    s += "</li>";
  }
  s += "</ul><a href='/'>⬅️ Retour</a></body></html>";
  server.send(200, "text/html", s);
}

void setupWeb() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/wifi", HTTP_GET, handleWifi);
  server.on("/wifi", HTTP_POST, handleWifi);
  server.on("/gps", HTTP_GET, handleGPS);
  server.on("/gps", HTTP_POST, handleGPS);
  server.on("/sensors", HTTP_GET, handleSensors);
  server.on("/peers", HTTP_GET, handlePeers);
  server.begin();
}

// ====== Capteurs (placeholder intégration matérielle) ======
void readSensors() {
  currentSensors.rssi = WiFi.RSSI();
  currentSensors.batteryV = 3.80f;
  currentSensors.dhtTemp = 22.5f;
  currentSensors.dhtHum = 52.0f;
  currentSensors.pressure = 1013.2f;
  currentSensors.airQuality = 87.0f;
  currentSensors.thermoK = 120.5f;
  currentSensors.current = 1.25f;
}

void sendPairRequestIfSlave() {
  if (currentMode != MODE_SLAVE) return;
  uint8_t bcast[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
  sendPacketTo(bcast, "pair_req", "master", "pair_me");
}

void checkMasterTasks() {
  if (currentMode != MODE_MASTER) return;

  static uint32_t lastHb = 0;
  static uint32_t lastPull = 0;
  uint32_t now = millis();

  if (now - lastHb > heartbeatPeriodMs) {
    broadcastPacket("ping", "proof_of_life");
    lastHb = now;
  }

  if (now - lastPull > staleDataPollMs) {
    for (uint8_t i = 0; i < peerCount; i++) {
      if (now - peers[i].lastSensorUpdate > staleDataPollMs) {
        sendPacketTo(peers[i].mac, "pull_data", peers[i].id, "stale_request");
      }
    }
    lastPull = now;
  }
}

void setupEspNow() {
  WiFi.mode(WIFI_AP_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("Erreur ESP-NOW init");
    return;
  }
  esp_now_register_recv_cb(onEspNowRecv);

  esp_now_peer_info_t bcast = {};
  memset(bcast.peer_addr, 0xFF, 6);
  bcast.channel = 0;
  bcast.encrypt = false;
  if (!esp_now_is_peer_exist(bcast.peer_addr)) {
    esp_now_add_peer(&bcast);
  }
}

void setupWiFiAndAP() {
  moduleId = String((uint32_t)(ESP.getEfuseMac() >> 24), HEX);
  moduleId.toUpperCase();
  apSSID = "ESC_LoRa" + moduleId;

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSSID.c_str(), apPass.c_str());

  if (wifiSSID.length()) {
    WiFi.begin(wifiSSID.c_str(), wifiPASS.c_str());
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) {
      delay(250);
      Serial.print('.');
    }
  }

  Serial.println();
  Serial.println("=== ESC_LoRa boot ===");
  Serial.println("ID module: " + moduleId);
  Serial.println("AP SSID: " + apSSID);
  Serial.println("IP STA: " + WiFi.localIP().toString());
  Serial.println("IP AP: " + WiFi.softAPIP().toString());
}

void setupOTA() {
  ArduinoOTA.setHostname(("ESC_LoRa-" + moduleId).c_str());
  ArduinoOTA.begin();
}

void maybeDeepSleep() {
  if (deepSleepSec == 0) return;
  esp_sleep_enable_timer_wakeup((uint64_t)deepSleepSec * 1000000ULL);
  esp_deep_sleep_start();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  loadConfig();
  setupWiFiAndAP();
  setupEspNow();
  setupWeb();
  setupOTA();
  mqtt.setBufferSize(1024);

  sendPairRequestIfSlave();
}

void loop() {
  server.handleClient();
  ArduinoOTA.handle();
  ensureMqtt();
  mqtt.loop();

  static uint32_t lastRead = 0;
  if (millis() - lastRead > 5000) {
    readSensors();

    if (shouldSendSensorUpdate()) {
      DynamicJsonDocument doc(512);
      doc["id"] = moduleId;
      doc["name"] = MODULE_NAME;
      doc["version"] = CODE_VERSION;
      doc["mode"] = getModeLabel();
      doc["battery_v"] = currentSensors.batteryV;
      doc["rssi"] = currentSensors.rssi;
      doc["dht_temp"] = currentSensors.dhtTemp;
      doc["dht_hum"] = currentSensors.dhtHum;
      doc["pressure"] = currentSensors.pressure;
      doc["air_quality"] = currentSensors.airQuality;
      doc["max6675_k"] = currentSensors.thermoK;
      doc["ly254_current"] = currentSensors.current;

      JsonArray dyn = doc.createNestedArray("dynamic_sensors");
      JsonObject s1 = dyn.createNestedObject();
      s1["key"] = "ens160_tvoc";
      s1["name"] = "TVOC";
      s1["unit"] = "ppb";
      JsonObject s2 = dyn.createNestedObject();
      s2["key"] = "ads1115_ch0";
      s2["name"] = "ADS1115 CH0";
      s2["unit"] = "V";

      String payload;
      serializeJson(doc, payload);

      if (currentMode == MODE_SLAVE || currentMode == MODE_RELAY) {
        broadcastPacket("sensor", payload);
      }

      publishState();
      publishDynamicSensorDiscovery(dyn);
      lastSentSensors = currentSensors;
    }

    checkMasterTasks();
    lastRead = millis();
  }

  static uint32_t bootT0 = millis();
  if (deepSleepSec > 0 && millis() - bootT0 > 45000) {
    maybeDeepSleep();
  }
}
