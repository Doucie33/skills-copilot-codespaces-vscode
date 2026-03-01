#include <WiFi.h>
#include <esp_now.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>
#include <esp_wifi.h>
#include <esp_sleep.h>
#include <time.h>

#if __has_include(<ArduinoJson.h>)
#include <ArduinoJson.h>
#define HAS_ARDUINO_JSON 1
#else
#define HAS_ARDUINO_JSON 0
#endif

#if __has_include(<LoRa.h>)
#include <LoRa.h>
#define HAS_LORA 1
#else
#define HAS_LORA 0
#endif

// =======================
// ESC_LoRa - v2.0.0
// =======================
String CODE_NAME = "ESC_LoRa";
String CODE_VERSION = "v2.0.0";

String MODULE_NAME = "ESC_Module";
String LORA_NETWORK_NAME = "ESC_LoRaNet";
bool HAS_OLED = true;

// AP defaults for first connection
String apSsid = "ESC_LoRa+ID";
String apPassword = "12345678";
bool maskPasswords = true;

// WiFi client
String staSsid = "";
String staPassword = "";

// MQTT
String mqttHost = "192.168.4.2";
uint16_t mqttPort = 1883;
String mqttUser = "";
String mqttPass = "";
String mqttPrefix = "esc_lora";

// GPS settings (editable by web)
uint32_t gpsBaud = 9600;
String gpsMode = "NMEA";

// Deep sleep settings
bool deepSleepEnabled = false;
uint32_t deepSleepSeconds = 900;

// Heartbeat & ping settings
uint32_t heartbeatIntervalSec = 1800; // 30 min default
uint32_t staleRequestSec = 300;

// GPIO mapping (editable)
int dhtPin = 4;
int relayPin = 12;
int max6675SckPin = 18;
int max6675CsPin = 5;
int max6675SoPin = 19;
int batteryAdcPin = 1;

// Role selection
enum Role : uint8_t { ROLE_MASTER = 0, ROLE_SLAVE = 1, ROLE_RELAY = 2 };
Role currentRole = ROLE_SLAVE;

Preferences prefs;
WebServer server(80);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String moduleId;
String effectiveApSsid;

struct PeerInfo {
  String id;
  uint8_t mac[6];
  bool online;
  uint32_t lastSeen;
  uint32_t lastData;
};

PeerInfo peers[16];
size_t peerCount = 0;

String lastSensorPayload = "";
uint32_t lastHeartbeatMs = 0;
uint32_t lastStaleCheckMs = 0;

String roleToString(Role r) {
  switch (r) {
    case ROLE_MASTER: return "master";
    case ROLE_SLAVE: return "slave";
    case ROLE_RELAY: return "relay";
    default: return "unknown";
  }
}

Role stringToRole(const String& value) {
  if (value == "master") return ROLE_MASTER;
  if (value == "relay") return ROLE_RELAY;
  return ROLE_SLAVE;
}

String macToString(const uint8_t* mac) {
  char out[18];
  snprintf(out, sizeof(out), "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(out);
}

String escapeHtml(const String& in) {
  String s = in;
  s.replace("&", "&amp;");
  s.replace("<", "&lt;");
  s.replace(">", "&gt;");
  s.replace("\"", "&quot;");
  return s;
}

void saveSettings() {
  prefs.putString("codeName", CODE_NAME);
  prefs.putString("version", CODE_VERSION);
  prefs.putString("module", MODULE_NAME);
  prefs.putString("loraNet", LORA_NETWORK_NAME);
  prefs.putBool("hasOLED", HAS_OLED);
  prefs.putString("apSsid", apSsid);
  prefs.putString("apPass", apPassword);
  prefs.putBool("maskPwd", maskPasswords);
  prefs.putString("staSsid", staSsid);
  prefs.putString("staPass", staPassword);
  prefs.putString("mqttHost", mqttHost);
  prefs.putUShort("mqttPort", mqttPort);
  prefs.putString("mqttUser", mqttUser);
  prefs.putString("mqttPass", mqttPass);
  prefs.putString("mqttPre", mqttPrefix);
  prefs.putUInt("gpsBaud", gpsBaud);
  prefs.putString("gpsMode", gpsMode);
  prefs.putBool("sleepEn", deepSleepEnabled);
  prefs.putUInt("sleepSec", deepSleepSeconds);
  prefs.putUInt("hbSec", heartbeatIntervalSec);
  prefs.putUInt("staleSec", staleRequestSec);
  prefs.putInt("dhtPin", dhtPin);
  prefs.putInt("relayPin", relayPin);
  prefs.putInt("batPin", batteryAdcPin);
  prefs.putUInt("role", (uint32_t)currentRole);
}

void loadSettings() {
  prefs.begin("esc_lora", false);
  CODE_NAME = prefs.getString("codeName", CODE_NAME);
  CODE_VERSION = prefs.getString("version", CODE_VERSION);
  MODULE_NAME = prefs.getString("module", MODULE_NAME);
  LORA_NETWORK_NAME = prefs.getString("loraNet", LORA_NETWORK_NAME);
  HAS_OLED = prefs.getBool("hasOLED", HAS_OLED);
  apSsid = prefs.getString("apSsid", apSsid);
  apPassword = prefs.getString("apPass", apPassword);
  maskPasswords = prefs.getBool("maskPwd", maskPasswords);
  staSsid = prefs.getString("staSsid", staSsid);
  staPassword = prefs.getString("staPass", staPassword);
  mqttHost = prefs.getString("mqttHost", mqttHost);
  mqttPort = prefs.getUShort("mqttPort", mqttPort);
  mqttUser = prefs.getString("mqttUser", mqttUser);
  mqttPass = prefs.getString("mqttPass", mqttPass);
  mqttPrefix = prefs.getString("mqttPre", mqttPrefix);
  gpsBaud = prefs.getUInt("gpsBaud", gpsBaud);
  gpsMode = prefs.getString("gpsMode", gpsMode);
  deepSleepEnabled = prefs.getBool("sleepEn", deepSleepEnabled);
  deepSleepSeconds = prefs.getUInt("sleepSec", deepSleepSeconds);
  heartbeatIntervalSec = prefs.getUInt("hbSec", heartbeatIntervalSec);
  staleRequestSec = prefs.getUInt("staleSec", staleRequestSec);
  dhtPin = prefs.getInt("dhtPin", dhtPin);
  relayPin = prefs.getInt("relayPin", relayPin);
  batteryAdcPin = prefs.getInt("batPin", batteryAdcPin);
  currentRole = (Role)prefs.getUInt("role", currentRole);
}

float readBatteryVoltage() {
  int raw = analogRead(batteryAdcPin);
  float v = (raw / 4095.0f) * 3.3f * 2.0f;
  return v;
}

float readBatteryPercent() {
  float v = readBatteryVoltage();
  float pct = (v - 3.2f) / (4.2f - 3.2f) * 100.0f;
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

String buildSensorJson(bool includeMeta = true) {
#if HAS_ARDUINO_JSON
  StaticJsonDocument<768> doc;
  if (includeMeta) {
    doc["id"] = moduleId;
    doc["name"] = MODULE_NAME;
    doc["version"] = CODE_VERSION;
    doc["mode"] = roleToString(currentRole);
    doc["online"] = true;
  }

  JsonObject bat = doc.createNestedObject("battery");
  bat["voltage"] = readBatteryVoltage();
  bat["percent"] = readBatteryPercent();

  JsonObject sensors = doc.createNestedObject("sensors");
  sensors["rssi"] = WiFi.RSSI();
  sensors["dht22_temp"] = 23.5;
  sensors["dht22_hum"] = 54.0;
  sensors["ms4525do_pressure"] = 1012.5;
  sensors["ens160_tvoc"] = 145;
  sensors["aht21_temp"] = 23.2;
  sensors["max6675_k"] = 44.6;
  sensors["ly254_current"] = 1.20;
  sensors["ywbl_wh"] = 320.0;
  sensors["sct013_current"] = 0.85;

  String out;
  serializeJson(doc, out);
  return out;
#else
  String out = "{";
  out += "\"id\":\"" + moduleId + "\",";
  out += "\"name\":\"" + MODULE_NAME + "\",";
  out += "\"version\":\"" + CODE_VERSION + "\",";
  out += "\"mode\":\"" + roleToString(currentRole) + "\",";
  out += "\"battery\":{\"voltage\":" + String(readBatteryVoltage(), 2) + ",\"percent\":" + String(readBatteryPercent(), 1) + "},";
  out += "\"sensors\":{\"rssi\":" + String(WiFi.RSSI()) + "}";
  out += "}";
  return out;
#endif
}

void publishMqtt(const String& topic, const String& payload, bool retained = false) {
  if (!mqtt.connected()) return;
  mqtt.publish(topic.c_str(), payload.c_str(), retained);
}

void publishDynamicDiscovery(const String& jsonPayload) {
#if HAS_ARDUINO_JSON
  StaticJsonDocument<1024> doc;
  if (deserializeJson(doc, jsonPayload) != DeserializationError::Ok) return;
  JsonObject sensors = doc["sensors"];
  for (JsonPair kv : sensors) {
    String sensorName = kv.key().c_str();
    String uniq = moduleId + "_" + sensorName;
    String cfgTopic = "homeassistant/sensor/" + uniq + "/config";

    StaticJsonDocument<512> cfg;
    cfg["name"] = MODULE_NAME + " " + sensorName;
    cfg["uniq_id"] = uniq;
    cfg["stat_t"] = mqttPrefix + "/" + moduleId + "/sensors";
    cfg["val_tpl"] = "{{ value_json.sensors." + sensorName + " }}";
    cfg["avty_t"] = mqttPrefix + "/" + moduleId + "/status";
    cfg["pl_avail"] = "online";
    cfg["pl_not_avail"] = "offline";

    StaticJsonDocument<256> dev;
    dev["ids"][0] = moduleId;
    dev["name"] = MODULE_NAME;
    dev["sw"] = CODE_VERSION;
    cfg["dev"] = dev;

    String cfgPayload;
    serializeJson(cfg, cfgPayload);
    publishMqtt(cfgTopic, cfgPayload, true);
  }
#endif
}

void addOrUpdatePeer(const String& id, const uint8_t* mac) {
  for (size_t i = 0; i < peerCount; i++) {
    if (peers[i].id == id) {
      memcpy(peers[i].mac, mac, 6);
      peers[i].online = true;
      peers[i].lastSeen = millis();
      return;
    }
  }

  if (peerCount < 16) {
    peers[peerCount].id = id;
    memcpy(peers[peerCount].mac, mac, 6);
    peers[peerCount].online = true;
    peers[peerCount].lastSeen = millis();
    peers[peerCount].lastData = millis();
    peerCount++;
  }
}

void removePeerById(const String& id) {
  for (size_t i = 0; i < peerCount; i++) {
    if (peers[i].id == id) {
      for (size_t j = i; j + 1 < peerCount; j++) peers[j] = peers[j + 1];
      peerCount--;
      return;
    }
  }
}

void sendEspNowJson(const uint8_t* mac, const String& msg) {
  esp_now_send(mac, (const uint8_t*)msg.c_str(), msg.length() + 1);
}

void broadcastEspNowJson(const String& msg) {
  uint8_t bcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  sendEspNowJson(bcast, msg);
}

void processIncomingJson(const uint8_t* mac, const String& data) {
#if HAS_ARDUINO_JSON
  StaticJsonDocument<1024> doc;
  if (deserializeJson(doc, data) != DeserializationError::Ok) return;

  String type = doc["type"] | "";
  String senderId = doc["id"] | "";
  addOrUpdatePeer(senderId, mac);

  if (type == "pair_request" && currentRole == ROLE_MASTER) {
    StaticJsonDocument<256> reply;
    reply["type"] = "pair_accept";
    reply["id"] = moduleId;
    String payload;
    serializeJson(reply, payload);
    sendEspNowJson(mac, payload);
  } else if (type == "sensor_data") {
    for (size_t i = 0; i < peerCount; i++) {
      if (peers[i].id == senderId) peers[i].lastData = millis();
    }
    publishMqtt(mqttPrefix + "/" + senderId + "/sensors", data, false);
    publishDynamicDiscovery(data);
  } else if (type == "proof_of_life") {
    StaticJsonDocument<256> ack;
    ack["type"] = "proof_of_life_ack";
    ack["id"] = moduleId;
    String payload;
    serializeJson(ack, payload);
    sendEspNowJson(mac, payload);
  } else if (type == "get_data") {
    String sensorPayload = buildSensorJson(true);
    StaticJsonDocument<1024> out;
    out["type"] = "sensor_data";
    out["id"] = moduleId;
    out["payload"] = serialized(sensorPayload);
    String answer;
    serializeJson(out, answer);
    sendEspNowJson(mac, answer);
  } else if (type == "command") {
    String target = doc["target"] | "";
    if (target == moduleId || target == "all") {
      String cmd = doc["cmd"] | "";
      if (cmd == "relay_on") digitalWrite(relayPin, HIGH);
      if (cmd == "relay_off") digitalWrite(relayPin, LOW);
      if (cmd == "sleep_now" && deepSleepEnabled) esp_deep_sleep(deepSleepSeconds * 1000000ULL);
    }
  }
#endif
}

void onEspNowRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  if (!data || len <= 0) return;
  String incoming = String((const char*)data);
  processIncomingJson(info->src_addr, incoming);
}

void onEspNowSent(const uint8_t*, esp_now_send_status_t) {}

void setupEspNow() {
  WiFi.mode(WIFI_AP_STA);
  if (esp_now_init() != ESP_OK) return;
  esp_now_register_recv_cb(onEspNowRecv);
  esp_now_register_send_cb(onEspNowSent);

  esp_now_peer_info_t peerInfo = {};
  memset(peerInfo.peer_addr, 0xFF, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);
}

void setupLoRa() {
#if HAS_LORA
  LoRa.setPins(5, 14, 2);
  if (!LoRa.begin(915E6)) {
    Serial.println("[⚠] LoRa init failed");
  } else {
    Serial.println("[✓] LoRa ready");
  }
#else
  Serial.println("[⚠] LoRa library missing, ESP-NOW mesh only");
#endif
}

String htmlHeader(const String& title) {
  String out;
  out += "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>";
  out += "<title>" + title + "</title><style>body{font-family:Arial;margin:16px}input,select{padding:6px;margin:4px 0;width:100%}button{padding:8px 12px}code{background:#eee;padding:2px 4px}.card{border:1px solid #ddd;padding:12px;margin-bottom:12px;border-radius:8px}</style></head><body>";
  out += "<h2>📡 " + CODE_NAME + " <small>" + CODE_VERSION + "</small></h2>";
  return out;
}

String gpioOptions(int selected) {
  String out;
  for (int i = 0; i <= 48; i++) {
    out += "<option value='" + String(i) + "'";
    if (i == selected) out += " selected";
    out += ">GPIO" + String(i) + "</option>";
  }
  return out;
}

void handleRoot() {
  String html = htmlHeader("ESC_LoRa Dashboard");
  html += "<div class='card'><h3>🧭 Module</h3>";
  html += "<p><b>ID:</b> <code>" + moduleId + "</code></p>";
  html += "<p><b>Mode:</b> " + roleToString(currentRole) + "</p>";
  html += "<p><b>Réseau AP:</b> " + effectiveApSsid + "</p>";
  html += "<p><b>IP:</b> " + WiFi.localIP().toString() + "</p>";
  html += "<p><a href='/config'>Configuration</a> | <a href='/peers'>Pairing</a> | <a href='/sensors'>Capteurs</a> | <a href='/gps'>GPS</a></p></div>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleConfig() {
  if (server.method() == HTTP_POST) {
    MODULE_NAME = server.arg("moduleName");
    CODE_VERSION = server.arg("version");
    LORA_NETWORK_NAME = server.arg("loraName");
    apSsid = server.arg("apSsid");
    apPassword = server.arg("apPwd");
    staSsid = server.arg("staSsid");
    staPassword = server.arg("staPwd");
    maskPasswords = server.hasArg("maskPwd");
    HAS_OLED = server.hasArg("hasOled");
    deepSleepEnabled = server.hasArg("sleepEn");
    deepSleepSeconds = server.arg("sleepSec").toInt();
    heartbeatIntervalSec = server.arg("hbSec").toInt();
    staleRequestSec = server.arg("staleSec").toInt();
    currentRole = stringToRole(server.arg("role"));
    dhtPin = server.arg("dhtPin").toInt();
    relayPin = server.arg("relayPin").toInt();
    batteryAdcPin = server.arg("batPin").toInt();
    mqttHost = server.arg("mqttHost");
    mqttPort = (uint16_t)server.arg("mqttPort").toInt();
    mqttUser = server.arg("mqttUser");
    mqttPass = server.arg("mqttPass");
    saveSettings();
    server.sendHeader("Location", "/config");
    server.send(303, "text/plain", "Saved");
    return;
  }

  String html = htmlHeader("Configuration");
  html += "<form method='post'><div class='card'><h3>⚙️ Général</h3>";
  html += "Nom module <input name='moduleName' value='" + escapeHtml(MODULE_NAME) + "'>";
  html += "Version <input name='version' value='" + escapeHtml(CODE_VERSION) + "'>";
  html += "Nom réseau LoRa <input name='loraName' value='" + escapeHtml(LORA_NETWORK_NAME) + "'>";
  html += "Mode <select name='role'><option value='master'" + String(currentRole == ROLE_MASTER ? " selected" : "") + ">Master</option><option value='slave'" + String(currentRole == ROLE_SLAVE ? " selected" : "") + ">Slave</option><option value='relay'" + String(currentRole == ROLE_RELAY ? " selected" : "") + ">Relais</option></select>";
  html += "<label><input type='checkbox' name='hasOled'" + String(HAS_OLED ? " checked" : "") + "> OLED présent</label><br>";
  html += "</div><div class='card'><h3>📶 WiFi</h3>";
  html += "AP SSID <input name='apSsid' value='" + escapeHtml(apSsid) + "'>";
  html += "AP Password <input name='apPwd' type='" + String(maskPasswords ? "password" : "text") + "' value='" + escapeHtml(apPassword) + "'>";
  html += "STA SSID <input name='staSsid' value='" + escapeHtml(staSsid) + "'>";
  html += "STA Password <input name='staPwd' type='" + String(maskPasswords ? "password" : "text") + "' value='" + escapeHtml(staPassword) + "'>";
  html += "<label><input type='checkbox' name='maskPwd'" + String(maskPasswords ? " checked" : "") + "> Masquer les mots de passe</label>";
  html += "</div><div class='card'><h3>🔋 Energie</h3>";
  html += "<label><input type='checkbox' name='sleepEn'" + String(deepSleepEnabled ? " checked" : "") + "> Deep sleep</label><br>";
  html += "Durée deep sleep (sec) <input name='sleepSec' value='" + String(deepSleepSeconds) + "'>";
  html += "Heartbeat (sec) <input name='hbSec' value='" + String(heartbeatIntervalSec) + "'>";
  html += "Demande données stale (sec) <input name='staleSec' value='" + String(staleRequestSec) + "'>";
  html += "</div><div class='card'><h3>📡 MQTT</h3>";
  html += "Host <input name='mqttHost' value='" + escapeHtml(mqttHost) + "'>";
  html += "Port <input name='mqttPort' value='" + String(mqttPort) + "'>";
  html += "User <input name='mqttUser' value='" + escapeHtml(mqttUser) + "'>";
  html += "Password <input name='mqttPass' type='" + String(maskPasswords ? "password" : "text") + "' value='" + escapeHtml(mqttPass) + "'>";
  html += "</div><div class='card'><h3>🧩 GPIO</h3>";
  html += "DHT22 <select name='dhtPin'>" + gpioOptions(dhtPin) + "</select>";
  html += "Relais <select name='relayPin'>" + gpioOptions(relayPin) + "</select>";
  html += "Batterie ADC <select name='batPin'>" + gpioOptions(batteryAdcPin) + "</select>";
  html += "</div><button type='submit'>💾 Sauvegarder</button> <a href='/'>Retour</a></form></body></html>";
  server.send(200, "text/html", html);
}

void handleGps() {
  if (server.method() == HTTP_POST) {
    gpsBaud = server.arg("baud").toInt();
    gpsMode = server.arg("mode");
    saveSettings();
    server.sendHeader("Location", "/gps");
    server.send(303, "text/plain", "Saved");
    return;
  }
  String html = htmlHeader("GPS");
  html += "<form method='post'><div class='card'><h3>🛰️ GPS</h3>";
  html += "Baudrate <input name='baud' value='" + String(gpsBaud) + "'>";
  html += "Mode <select name='mode'><option" + String(gpsMode == "NMEA" ? " selected" : "") + ">NMEA</option><option" + String(gpsMode == "UBX" ? " selected" : "") + ">UBX</option></select>";
  html += "</div><button type='submit'>💾 Enregistrer</button> <a href='/'>Retour</a></form></body></html>";
  server.send(200, "text/html", html);
}

void handlePeers() {
  if (server.hasArg("remove")) {
    removePeerById(server.arg("remove"));
  }

  if (server.hasArg("pair") && currentRole != ROLE_MASTER) {
#if HAS_ARDUINO_JSON
    StaticJsonDocument<256> req;
    req["type"] = "pair_request";
    req["id"] = moduleId;
    String payload;
    serializeJson(req, payload);
    broadcastEspNowJson(payload);
#endif
  }

  String html = htmlHeader("Pairing");
  html += "<div class='card'><h3>🔗 Pairing</h3>";
  html += "<a href='/peers?pair=1'><button>Envoyer une demande d'appairage</button></a>";
  html += "<ul>";
  for (size_t i = 0; i < peerCount; i++) {
    html += "<li>" + peers[i].id + " (" + macToString(peers[i].mac) + ") - ";
    html += peers[i].online ? "🟢 online" : "🔴 offline";
    html += " <a href='/peers?remove=" + peers[i].id + "'>❌ supprimer</a></li>";
  }
  html += "</ul></div><a href='/'>Retour</a></body></html>";
  server.send(200, "text/html", html);
}

void handleSensors() {
  String html = htmlHeader("Capteurs");
  html += "<div class='card'><h3>📊 Données capteurs</h3><pre>" + escapeHtml(buildSensorJson(true)) + "</pre></div>";
  html += "<a href='/'>Retour</a></body></html>";
  server.send(200, "text/html", html);
}

void setupWeb() {
  server.on("/", handleRoot);
  server.on("/config", HTTP_ANY, handleConfig);
  server.on("/gps", HTTP_ANY, handleGps);
  server.on("/peers", HTTP_GET, handlePeers);
  server.on("/sensors", HTTP_GET, handleSensors);
  server.begin();
}

void ensureMqtt() {
  if (mqtt.connected()) return;
  mqtt.setServer(mqttHost.c_str(), mqttPort);
  String clientId = "esc_" + moduleId;
  if (mqtt.connect(clientId.c_str(), mqttUser.c_str(), mqttPass.c_str(), (mqttPrefix + "/" + moduleId + "/status").c_str(), 1, true, "offline")) {
    publishMqtt(mqttPrefix + "/" + moduleId + "/status", "online", true);
    publishMqtt(mqttPrefix + "/" + moduleId + "/info/name", MODULE_NAME, true);
    publishMqtt(mqttPrefix + "/" + moduleId + "/info/version", CODE_VERSION, true);
    publishMqtt(mqttPrefix + "/" + moduleId + "/info/mode", roleToString(currentRole), true);
    mqtt.subscribe((mqttPrefix + "/" + moduleId + "/cmd").c_str());
  }
}

void setupOTA() {
  ArduinoOTA.setHostname((CODE_NAME + "-" + moduleId).c_str());
  ArduinoOTA.begin();
}

void sendProofOfLifeToPeers() {
#if HAS_ARDUINO_JSON
  StaticJsonDocument<256> doc;
  doc["type"] = "proof_of_life";
  doc["id"] = moduleId;
  String payload;
  serializeJson(doc, payload);
  broadcastEspNowJson(payload);
#endif
}

void requestStalePeersData() {
  uint32_t now = millis();
#if HAS_ARDUINO_JSON
  for (size_t i = 0; i < peerCount; i++) {
    if (now - peers[i].lastData > staleRequestSec * 1000UL) {
      StaticJsonDocument<256> req;
      req["type"] = "get_data";
      req["id"] = moduleId;
      String payload;
      serializeJson(req, payload);
      sendEspNowJson(peers[i].mac, payload);
    }
  }
#endif
}

void sendSensorIfChanged() {
  String payload = buildSensorJson(true);
  if (payload == lastSensorPayload) return;
  lastSensorPayload = payload;

#if HAS_ARDUINO_JSON
  StaticJsonDocument<1200> doc;
  doc["type"] = "sensor_data";
  doc["id"] = moduleId;
  doc["sensors"] = serialized(payload);
  String frame;
  serializeJson(doc, frame);
  broadcastEspNowJson(frame);
#endif

  publishMqtt(mqttPrefix + "/" + moduleId + "/sensors", payload);
  publishDynamicDiscovery(payload);
}

void setupWifi() {
  uint64_t chip = ESP.getEfuseMac();
  moduleId = String((uint32_t)(chip & 0xFFFFFF), HEX);
  moduleId.toUpperCase();
  effectiveApSsid = apSsid + moduleId;

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(effectiveApSsid.c_str(), apPassword.c_str());

  if (staSsid.length() > 0) {
    WiFi.begin(staSsid.c_str(), staPassword.c_str());
    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) delay(200);
  }

  Serial.println("==============================");
  Serial.println("Nom réseau AP      : " + effectiveApSsid);
  Serial.println("IP locale          : " + WiFi.localIP().toString());
  Serial.println("ID module          : " + moduleId);
  Serial.println("Code               : " + CODE_NAME + " " + CODE_VERSION);
  Serial.println("Mode               : " + roleToString(currentRole));
  Serial.println("==============================");
}

void setup() {
  Serial.begin(115200);
  delay(300);
  loadSettings();

  pinMode(relayPin, OUTPUT);
  analogReadResolution(12);

  setupWifi();
  setupEspNow();
  setupLoRa();
  setupOTA();
  setupWeb();

  mqtt.setBufferSize(2048);
}

void loop() {
  server.handleClient();
  ArduinoOTA.handle();
  ensureMqtt();
  mqtt.loop();

  if (currentRole == ROLE_MASTER) {
    if (millis() - lastHeartbeatMs > heartbeatIntervalSec * 1000UL) {
      sendProofOfLifeToPeers();
      lastHeartbeatMs = millis();
    }

    if (millis() - lastStaleCheckMs > 10000) {
      requestStalePeersData();
      lastStaleCheckMs = millis();
    }
  } else {
    sendSensorIfChanged();
  }

  if (deepSleepEnabled && currentRole == ROLE_SLAVE) {
    static uint32_t awakeStart = millis();
    if (millis() - awakeStart > 120000) {
      publishMqtt(mqttPrefix + "/" + moduleId + "/status", "sleeping", true);
      delay(200);
      esp_deep_sleep(deepSleepSeconds * 1000000ULL);
    }
  }

  delay(200);
}
