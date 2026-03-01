#include <WiFi.h>
#include <WebServer.h>
#include <esp_now.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <Preferences.h>
#include <ArduinoOTA.h>
#include <esp_sleep.h>

// Optional sensors/drivers
#include <DHT.h>
#include <Wire.h>

// ===========================
// ESC_LoRa v2.0.0
// ===========================
static const char *CODE_NAME = "ESC_LoRa";
static const char *CODE_VERSION = "v2.0.0";

// Editable branding / options
String moduleName = "ESC_LoRa_Module";
bool hasOLED = false;         // true if OLED is physically installed
bool batteryInstalled = true; // true if battery monitor is available

// Network defaults
String loraNetworkName = "ESC_LoRa_NET";
String mqttHost = "192.168.4.2";
uint16_t mqttPort = 1883;
String mqttUser = "";
String mqttPass = "";
String wifiSTA_SSID = "";
String wifiSTA_PASS = "";

enum NodeRole : uint8_t { ROLE_MASTER = 0, ROLE_SLAVE = 1, ROLE_RELAY = 2 };
NodeRole nodeRole = ROLE_SLAVE;

Preferences prefs;
WebServer web(80);
WiFiClient espClient;
PubSubClient mqtt(espClient);

String moduleId;
String apSSID;
String apPASS = "12345678";

// GPIO user selectable defaults
int gpioDHT = 4;
int gpioRelay = 25;
int gpioBatteryAdc = 35;
int gpioCurrentAdc = 34;

// DHT
#define DHTTYPE DHT22
DHT dht(gpioDHT, DHTTYPE);

// Timing
unsigned long heartbeatIntervalMs = 30UL * 60UL * 1000UL; // default 30 min (editable)
unsigned long lastHeartbeatMs = 0;
unsigned long staleRequestMs = 10UL * 60UL * 1000UL;
unsigned long lastStaleCheckMs = 0;
unsigned long sensorPublishPeriodMs = 5000;
unsigned long lastSensorPollMs = 0;

// GPS parameters editable on web
bool gpsEnabled = true;
uint32_t gpsBaud = 9600;

struct PeerNode {
  uint8_t mac[6];
  String id;
  unsigned long lastSeen;
  bool paired;
};

constexpr uint8_t MAX_PEERS = 20;
PeerNode peers[MAX_PEERS];

struct SensorSnapshot {
  float temp = NAN;
  float hum = NAN;
  float batteryV = NAN;
  float currentA = NAN;
  int rssi = 0;
};

SensorSnapshot currentValues;
SensorSnapshot lastSentValues;

enum MsgType : uint8_t {
  MSG_PAIR_REQ = 1,
  MSG_PAIR_ACK = 2,
  MSG_UNPAIR = 3,
  MSG_SENSOR = 4,
  MSG_HEARTBEAT = 5,
  MSG_PING = 6,
  MSG_PONG = 7,
  MSG_FORCE_REPORT = 8,
  MSG_CMD = 9
};

struct MeshMessage {
  uint8_t type;
  char fromId[24];
  char toId[24];
  char payload[200];
};

void saveConfig() {
  prefs.begin("esc_lora", false);
  prefs.putString("moduleName", moduleName);
  prefs.putUInt("role", nodeRole);
  prefs.putString("loraNet", loraNetworkName);
  prefs.putString("staSSID", wifiSTA_SSID);
  prefs.putString("staPASS", wifiSTA_PASS);
  prefs.putString("mqttHost", mqttHost);
  prefs.putUInt("mqttPort", mqttPort);
  prefs.putString("mqttUser", mqttUser);
  prefs.putString("mqttPass", mqttPass);
  prefs.putBool("hasOLED", hasOLED);
  prefs.putBool("bat", batteryInstalled);
  prefs.putUInt("hbMs", heartbeatIntervalMs);
  prefs.putUInt("gpsBaud", gpsBaud);
  prefs.putBool("gpsOn", gpsEnabled);
  prefs.end();
}

void loadConfig() {
  prefs.begin("esc_lora", true);
  moduleName = prefs.getString("moduleName", moduleName);
  nodeRole = static_cast<NodeRole>(prefs.getUInt("role", nodeRole));
  loraNetworkName = prefs.getString("loraNet", loraNetworkName);
  wifiSTA_SSID = prefs.getString("staSSID", wifiSTA_SSID);
  wifiSTA_PASS = prefs.getString("staPASS", wifiSTA_PASS);
  mqttHost = prefs.getString("mqttHost", mqttHost);
  mqttPort = prefs.getUInt("mqttPort", mqttPort);
  mqttUser = prefs.getString("mqttUser", mqttUser);
  mqttPass = prefs.getString("mqttPass", mqttPass);
  hasOLED = prefs.getBool("hasOLED", hasOLED);
  batteryInstalled = prefs.getBool("bat", batteryInstalled);
  heartbeatIntervalMs = prefs.getUInt("hbMs", heartbeatIntervalMs);
  gpsBaud = prefs.getUInt("gpsBaud", gpsBaud);
  gpsEnabled = prefs.getBool("gpsOn", gpsEnabled);
  prefs.end();
}

String roleToString(NodeRole role) {
  switch (role) {
    case ROLE_MASTER: return "master";
    case ROLE_SLAVE: return "slave";
    case ROLE_RELAY: return "relay";
    default: return "unknown";
  }
}

String macToString(const uint8_t *mac) {
  char b[18];
  snprintf(b, sizeof(b), "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(b);
}

void printBootInfo() {
  Serial.println("====================================");
  Serial.printf("%s %s\n", CODE_NAME, CODE_VERSION);
  Serial.printf("Module ID: %s\n", moduleId.c_str());
  Serial.printf("AP SSID: %s\n", apSSID.c_str());
  Serial.printf("AP IP: %s\n", WiFi.softAPIP().toString().c_str());
  Serial.printf("Role: %s\n", roleToString(nodeRole).c_str());
  Serial.println("====================================");
}

int findPeerByMac(const uint8_t *mac) {
  for (uint8_t i = 0; i < MAX_PEERS; i++) {
    if (peers[i].paired && memcmp(peers[i].mac, mac, 6) == 0) return i;
  }
  return -1;
}

int findEmptyPeer() {
  for (uint8_t i = 0; i < MAX_PEERS; i++) {
    if (!peers[i].paired) return i;
  }
  return -1;
}

void addOrRefreshPeer(const uint8_t *mac, const String &id) {
  int idx = findPeerByMac(mac);
  if (idx < 0) idx = findEmptyPeer();
  if (idx < 0) return;
  memcpy(peers[idx].mac, mac, 6);
  peers[idx].id = id;
  peers[idx].lastSeen = millis();
  peers[idx].paired = true;

  esp_now_peer_info_t p{};
  memcpy(p.peer_addr, mac, 6);
  p.channel = 0;
  p.encrypt = false;
  if (!esp_now_is_peer_exist(mac)) esp_now_add_peer(&p);
}

void removePeer(const uint8_t *mac) {
  int idx = findPeerByMac(mac);
  if (idx >= 0) {
    peers[idx].paired = false;
    peers[idx].id = "";
  }
  if (esp_now_is_peer_exist(mac)) esp_now_del_peer(mac);
}

void sendMeshMessage(const uint8_t *to, MsgType type, const String &payload, const String &toId = "*") {
  MeshMessage msg{};
  msg.type = type;
  strncpy(msg.fromId, moduleId.c_str(), sizeof(msg.fromId) - 1);
  strncpy(msg.toId, toId.c_str(), sizeof(msg.toId) - 1);
  strncpy(msg.payload, payload.c_str(), sizeof(msg.payload) - 1);
  esp_now_send(to, reinterpret_cast<const uint8_t *>(&msg), sizeof(msg));
}

void mqttPublish(const String &topic, const String &payload, bool retained = false) {
  if (!mqtt.connected()) return;
  mqtt.publish(topic.c_str(), payload.c_str(), retained);
}

String baseTopic() {
  return "esc_lora/" + moduleId;
}

void publishDiscovery(const JsonObject &sensorDef) {
  if (!mqtt.connected()) return;
  String key = sensorDef["key"].as<String>();
  String name = sensorDef["name"].as<String>();
  String unit = sensorDef["unit"].as<String>();
  String deviceClass = sensorDef["device_class"].as<String>();

  String cfgTopic = "homeassistant/sensor/" + moduleId + "/" + key + "/config";
  StaticJsonDocument<512> cfg;
  cfg["name"] = moduleName + " " + name;
  cfg["uniq_id"] = moduleId + "_" + key;
  cfg["state_topic"] = baseTopic() + "/sensor/" + key;
  cfg["availability_topic"] = baseTopic() + "/status";
  cfg["payload_available"] = "online";
  cfg["payload_not_available"] = "offline";
  cfg["unit_of_meas"] = unit;
  cfg["dev_cla"] = deviceClass;

  JsonObject dev = cfg.createNestedObject("device");
  dev["name"] = moduleName;
  dev["sw"] = CODE_VERSION;
  dev["mf"] = "LilyGO";
  dev["mdl"] = "T3-S3 LR1121 / T-Beam SX1276";
  JsonArray ids = dev.createNestedArray("ids");
  ids.add(moduleId);

  String out;
  serializeJson(cfg, out);
  mqttPublish(cfgTopic, out, true);
}

void publishDynamicDiscoveryFromJson(const String &jsonSensors) {
  StaticJsonDocument<2048> doc;
  if (deserializeJson(doc, jsonSensors) != DeserializationError::Ok) return;
  JsonArray arr = doc["sensors"].as<JsonArray>();
  for (JsonObject item : arr) {
    publishDiscovery(item);
  }
}

void publishStatus(const char *status) {
  mqttPublish(baseTopic() + "/status", status, true);
}

void publishSensorValue(const char *key, float value) {
  if (isnan(value)) return;
  mqttPublish(baseTopic() + "/sensor/" + key, String(value, 3), false);
}

float readBatteryVoltage() {
  if (!batteryInstalled) return NAN;
  uint16_t raw = analogRead(gpioBatteryAdc);
  float v = (raw / 4095.0f) * 3.3f * 2.0f;
  return v;
}

float readCurrent() {
  uint16_t raw = analogRead(gpioCurrentAdc);
  return (raw / 4095.0f) * 20.0f;
}

bool changed(float a, float b, float threshold) {
  if (isnan(a) && isnan(b)) return false;
  if (isnan(a) != isnan(b)) return true;
  return fabs(a - b) >= threshold;
}

String sensorJson() {
  StaticJsonDocument<512> doc;
  doc["id"] = moduleId;
  doc["role"] = roleToString(nodeRole);
  doc["name"] = moduleName;
  doc["version"] = CODE_VERSION;
  doc["rssi"] = currentValues.rssi;

  JsonObject sensors = doc.createNestedObject("sensors");
  sensors["temperature"] = currentValues.temp;
  sensors["humidity"] = currentValues.hum;
  sensors["battery_v"] = currentValues.batteryV;
  sensors["current_a"] = currentValues.currentA;

  String out;
  serializeJson(doc, out);
  return out;
}

void publishAllToMQTT() {
  publishSensorValue("temperature", currentValues.temp);
  publishSensorValue("humidity", currentValues.hum);
  publishSensorValue("battery_v", currentValues.batteryV);
  publishSensorValue("current_a", currentValues.currentA);
  mqttPublish(baseTopic() + "/meta/role", roleToString(nodeRole), true);
  mqttPublish(baseTopic() + "/meta/name", moduleName, true);
  mqttPublish(baseTopic() + "/meta/version", CODE_VERSION, true);
}

void handleCommandTopic(char *topic, byte *payload, unsigned int length) {
  String t = String(topic);
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += static_cast<char>(payload[i]);

  if (t.endsWith("/cmd/reboot")) {
    ESP.restart();
  } else if (t.endsWith("/cmd/ping_all") && nodeRole == ROLE_MASTER) {
    for (uint8_t i = 0; i < MAX_PEERS; i++) {
      if (!peers[i].paired) continue;
      sendMeshMessage(peers[i].mac, MSG_PING, "{}", peers[i].id);
    }
  } else if (t.endsWith("/cmd/deep_sleep")) {
    uint64_t sec = msg.toInt();
    if (sec == 0) sec = 60;
    publishStatus("sleeping");
    esp_sleep_enable_timer_wakeup(sec * 1000000ULL);
    delay(100);
    esp_deep_sleep_start();
  }
}

void mqttReconnect() {
  if (mqtt.connected()) return;
  mqtt.setServer(mqttHost.c_str(), mqttPort);
  mqtt.setCallback(handleCommandTopic);

  String clientId = moduleId + "-mqtt";
  bool ok;
  if (mqttUser.length()) {
    ok = mqtt.connect(clientId.c_str(), mqttUser.c_str(), mqttPass.c_str());
  } else {
    ok = mqtt.connect(clientId.c_str());
  }

  if (ok) {
    publishStatus("online");
    mqtt.subscribe((baseTopic() + "/cmd/#").c_str());

    const String defaultDynamicSensors = R"({
      "sensors":[
        {"key":"temperature","name":"Temperature","unit":"°C","device_class":"temperature"},
        {"key":"humidity","name":"Humidity","unit":"%","device_class":"humidity"},
        {"key":"battery_v","name":"Battery","unit":"V","device_class":"voltage"},
        {"key":"current_a","name":"Current","unit":"A","device_class":"current"},
        {"key":"rssi","name":"RSSI","unit":"dBm","device_class":"signal_strength"}
      ]
    })";
    publishDynamicDiscoveryFromJson(defaultDynamicSensors);
  }
}

void onEspNowRecv(const esp_now_recv_info_t *recvInfo, const uint8_t *data, int len) {
  if (len != sizeof(MeshMessage)) return;
  const MeshMessage *msg = reinterpret_cast<const MeshMessage *>(data);
  String from = String(msg->fromId);
  addOrRefreshPeer(recvInfo->src_addr, from);

  switch (msg->type) {
    case MSG_PAIR_REQ:
      if (nodeRole == ROLE_MASTER || nodeRole == ROLE_RELAY) {
        sendMeshMessage(recvInfo->src_addr, MSG_PAIR_ACK, "{\"ok\":true}", from);
      }
      break;
    case MSG_PAIR_ACK:
      addOrRefreshPeer(recvInfo->src_addr, from);
      break;
    case MSG_UNPAIR:
      removePeer(recvInfo->src_addr);
      break;
    case MSG_SENSOR:
      if (nodeRole == ROLE_MASTER || nodeRole == ROLE_RELAY) {
        mqttPublish("esc_lora/mesh/" + from + "/sensor_json", String(msg->payload), false);
      }
      break;
    case MSG_HEARTBEAT:
      if (nodeRole == ROLE_MASTER) {
        sendMeshMessage(recvInfo->src_addr, MSG_PONG, "{\"alive\":true}", from);
      }
      break;
    case MSG_PING:
      sendMeshMessage(recvInfo->src_addr, MSG_PONG, "{\"pong\":true}", from);
      break;
    case MSG_FORCE_REPORT:
      sendMeshMessage(recvInfo->src_addr, MSG_SENSOR, sensorJson(), from);
      break;
    case MSG_CMD:
      if (String(msg->payload) == "relay_on") digitalWrite(gpioRelay, HIGH);
      if (String(msg->payload) == "relay_off") digitalWrite(gpioRelay, LOW);
      break;
    default:
      break;
  }
}

void initEspNow() {
  WiFi.mode(WIFI_AP_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(onEspNowRecv);
}

String htmlHeader(const String &title) {
  return "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<style>body{font-family:Arial;background:#111;color:#eee;padding:12px}input,select,button{width:100%;padding:8px;margin:6px 0}"
         ".card{border:1px solid #444;padding:12px;border-radius:8px;margin:10px 0}a{color:#7dcfff}</style>"
         "<title>" + title + "</title></head><body>"
         "<h2>📡 " + String(CODE_NAME) + " " + CODE_VERSION + "</h2>";
}

void handleRoot() {
  String s = htmlHeader("ESC_LoRa Console");
  s += "<div class='card'><b>Module:</b> " + moduleName + "<br><b>ID:</b> " + moduleId + "<br><b>Role:</b> " + roleToString(nodeRole) +
       "<br><b>IP:</b> " + WiFi.softAPIP().toString() + "</div>";
  s += "<a href='/wifi'>WiFi</a><br><a href='/role'>Rôle</a><br><a href='/gps'>GPS</a><br><a href='/gpio'>GPIO</a><br><a href='/mesh'>Mesh</a><br><a href='/sensors'>Capteurs</a>";
  s += "</body></html>";
  web.send(200, "text/html", s);
}

void handleWifi() {
  if (web.method() == HTTP_POST) {
    moduleName = web.arg("moduleName");
    wifiSTA_SSID = web.arg("ssid");
    wifiSTA_PASS = web.arg("pass");
    mqttHost = web.arg("mqttHost");
    mqttPort = web.arg("mqttPort").toInt();
    saveConfig();
  }

  String s = htmlHeader("WiFi");
  s += "<form method='post'><div class='card'>"
       "Nom module<input name='moduleName' value='" + moduleName + "'>"
       "SSID<input name='ssid' value='" + wifiSTA_SSID + "'>"
       "Mot de passe<input id='pass' type='password' name='pass' value='" + wifiSTA_PASS + "'>"
       "<label><input type='checkbox' onclick=\"document.getElementById('pass').type=this.checked?'text':'password'\"> Afficher mot de passe</label>"
       "MQTT Host<input name='mqttHost' value='" + mqttHost + "'>"
       "MQTT Port<input name='mqttPort' value='" + String(mqttPort) + "'>"
       "<button>💾 Enregistrer</button></div></form><a href='/'>⬅ Retour</a></body></html>";
  web.send(200, "text/html", s);
}

void handleRole() {
  if (web.method() == HTTP_POST) {
    nodeRole = static_cast<NodeRole>(web.arg("role").toInt());
    heartbeatIntervalMs = web.arg("hb").toInt() * 60000UL;
    loraNetworkName = web.arg("loraName");
    saveConfig();
  }

  String s = htmlHeader("Role");
  s += "<form method='post'><div class='card'>"
       "Mode<select name='role'>"
       "<option value='0'" + String(nodeRole == ROLE_MASTER ? " selected" : "") + ">Master</option>"
       "<option value='1'" + String(nodeRole == ROLE_SLAVE ? " selected" : "") + ">Slave</option>"
       "<option value='2'" + String(nodeRole == ROLE_RELAY ? " selected" : "") + ">Relay</option>"
       "</select>"
       "Heartbeat (minutes)<input name='hb' value='" + String(heartbeatIntervalMs / 60000UL) + "'>"
       "Nom réseau LoRa<input name='loraName' value='" + loraNetworkName + "'>"
       "<button>💾 Enregistrer</button></div></form><a href='/'>⬅ Retour</a></body></html>";
  web.send(200, "text/html", s);
}

void handleGps() {
  if (web.method() == HTTP_POST) {
    gpsEnabled = web.arg("gps").toInt() == 1;
    gpsBaud = web.arg("baud").toInt();
    saveConfig();
  }

  String s = htmlHeader("GPS");
  s += "<form method='post'><div class='card'>"
       "GPS<select name='gps'><option value='1'" + String(gpsEnabled ? " selected" : "") + ">Activé</option><option value='0'" + String(!gpsEnabled ? " selected" : "") + ">Désactivé</option></select>"
       "Baud<input name='baud' value='" + String(gpsBaud) + "'>"
       "<button>💾 Enregistrer</button></div></form><a href='/'>⬅ Retour</a></body></html>";
  web.send(200, "text/html", s);
}

String gpioOptions(int selected) {
  String s;
  for (int i = 0; i <= 48; i++) {
    s += "<option value='" + String(i) + "'" + String(i == selected ? " selected" : "") + ">GPIO" + String(i) + "</option>";
  }
  return s;
}

void handleGpio() {
  if (web.method() == HTTP_POST) {
    gpioDHT = web.arg("gpioDHT").toInt();
    gpioRelay = web.arg("gpioRelay").toInt();
    gpioBatteryAdc = web.arg("gpioBat").toInt();
    gpioCurrentAdc = web.arg("gpioCur").toInt();
    saveConfig();
  }

  String s = htmlHeader("GPIO");
  s += "<form method='post'><div class='card'>DHT22<select name='gpioDHT'>" + gpioOptions(gpioDHT) + "</select>"
       "Relais<select name='gpioRelay'>" + gpioOptions(gpioRelay) + "</select>"
       "Battery ADC<select name='gpioBat'>" + gpioOptions(gpioBatteryAdc) + "</select>"
       "Current ADC<select name='gpioCur'>" + gpioOptions(gpioCurrentAdc) + "</select>"
       "<button>💾 Enregistrer</button></div></form><a href='/'>⬅ Retour</a></body></html>";
  web.send(200, "text/html", s);
}

void handleMesh() {
  if (web.hasArg("unpair")) {
    int i = web.arg("unpair").toInt();
    if (i >= 0 && i < MAX_PEERS && peers[i].paired) {
      sendMeshMessage(peers[i].mac, MSG_UNPAIR, "{}", peers[i].id);
      removePeer(peers[i].mac);
    }
  }

  String s = htmlHeader("Mesh");
  s += "<div class='card'><b>Pairing</b><br><form method='post' action='/pair'><button>🤝 Demander appairage</button></form></div>";
  s += "<div class='card'><b>Peers</b><ul>";
  for (uint8_t i = 0; i < MAX_PEERS; i++) {
    if (!peers[i].paired) continue;
    s += "<li>#" + String(i) + " " + peers[i].id + " (" + macToString(peers[i].mac) + ")"
         " <a href='/mesh?unpair=" + String(i) + "'>❌ Supprimer</a></li>";
  }
  s += "</ul></div><a href='/'>⬅ Retour</a></body></html>";
  web.send(200, "text/html", s);
}

void handlePair() {
  uint8_t broadcastMac[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};
  sendMeshMessage(broadcastMac, MSG_PAIR_REQ, "{\"request\":true}");
  web.sendHeader("Location", "/mesh");
  web.send(302, "text/plain", "pair requested");
}

void handleSensors() {
  String s = htmlHeader("Sensors");
  s += "<div class='card'><pre>" + sensorJson() + "</pre></div><a href='/'>⬅ Retour</a></body></html>";
  web.send(200, "text/html", s);
}

void initWeb() {
  web.on("/", handleRoot);
  web.on("/wifi", HTTP_ANY, handleWifi);
  web.on("/role", HTTP_ANY, handleRole);
  web.on("/gps", HTTP_ANY, handleGps);
  web.on("/gpio", HTTP_ANY, handleGpio);
  web.on("/mesh", HTTP_GET, handleMesh);
  web.on("/pair", HTTP_POST, handlePair);
  web.on("/sensors", HTTP_GET, handleSensors);
  web.begin();
}

void initWifi() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSSID.c_str(), apPASS.c_str());

  if (wifiSTA_SSID.length()) {
    WiFi.begin(wifiSTA_SSID.c_str(), wifiSTA_PASS.c_str());
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
      delay(300);
      Serial.print(".");
    }
    Serial.println();
  }
}

void initOTA() {
  ArduinoOTA.setHostname(moduleName.c_str());
  ArduinoOTA.begin();
}

void setup() {
  Serial.begin(115200);
  delay(500);

  uint64_t mac = ESP.getEfuseMac();
  moduleId = String((uint32_t)(mac >> 24), HEX);
  moduleId.toUpperCase();
  apSSID = "ESC_LoRa" + moduleId;

  pinMode(gpioRelay, OUTPUT);

  loadConfig();
  initWifi();
  initEspNow();
  initWeb();
  initOTA();

  dht.begin();

  printBootInfo();
}

void pollSensors() {
  currentValues.temp = dht.readTemperature();
  currentValues.hum = dht.readHumidity();
  currentValues.batteryV = readBatteryVoltage();
  currentValues.currentA = readCurrent();
  currentValues.rssi = WiFi.RSSI();
}

void loopMaster() {
  if (millis() - lastHeartbeatMs > heartbeatIntervalMs) {
    for (uint8_t i = 0; i < MAX_PEERS; i++) {
      if (!peers[i].paired) continue;
      sendMeshMessage(peers[i].mac, MSG_HEARTBEAT, "{\"hb\":true}", peers[i].id);
    }
    lastHeartbeatMs = millis();
  }

  if (millis() - lastStaleCheckMs > staleRequestMs) {
    for (uint8_t i = 0; i < MAX_PEERS; i++) {
      if (!peers[i].paired) continue;
      if (millis() - peers[i].lastSeen > staleRequestMs) {
        sendMeshMessage(peers[i].mac, MSG_FORCE_REPORT, "{\"force\":true}", peers[i].id);
      }
    }
    lastStaleCheckMs = millis();
  }
}

void loopSlaveOrRelay() {
  bool shouldSend = changed(currentValues.temp, lastSentValues.temp, 0.2f) ||
                    changed(currentValues.hum, lastSentValues.hum, 1.0f) ||
                    changed(currentValues.batteryV, lastSentValues.batteryV, 0.05f) ||
                    changed(currentValues.currentA, lastSentValues.currentA, 0.1f);

  if (shouldSend) {
    for (uint8_t i = 0; i < MAX_PEERS; i++) {
      if (!peers[i].paired) continue;
      sendMeshMessage(peers[i].mac, MSG_SENSOR, sensorJson(), peers[i].id);
    }
    lastSentValues = currentValues;
  }
}

void loop() {
  web.handleClient();
  ArduinoOTA.handle();
  mqttReconnect();
  mqtt.loop();

  if (millis() - lastSensorPollMs > sensorPublishPeriodMs) {
    pollSensors();
    publishAllToMQTT();
    lastSensorPollMs = millis();
  }

  if (nodeRole == ROLE_MASTER) {
    loopMaster();
  } else {
    loopSlaveOrRelay();
  }
}
