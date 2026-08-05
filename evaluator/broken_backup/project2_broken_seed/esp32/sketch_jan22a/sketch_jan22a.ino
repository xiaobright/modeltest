#include <Arduino.h>
#include <WiFi.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <ctype.h>
#include <stdint.h>
#include <string.h>
#include <sys/time.h>

// ===================== Runtime config (NVS / Preferences) =====================
// 固件只编译一次；WiFi、巴法云 UID、房间和床位通过串口命令写入 NVS。
// 串口命令:
//   CFG?
//   CFGSET ssid=your_wifi
//   CFGSET password=your_password
//   CFGSET uid=your_bemfa_uid
//   CFGSET room=R1203
//   CFGSET bed=B1
//   CFGRESET
//   REBOOT
static const char *CONFIG_NS = "project2";
static const char *DEVICE_ROLE = "radar_env_audio";

struct DeviceConfig {
  char wifi_ssid[33];
  char wifi_password[65];
  char bemfa_uid[96];
  char bemfa_host[64];
  uint16_t bemfa_mqtt_port;
  char room[16];
  char bed[16];
  char device_id[48];
};

DeviceConfig cfg;
bool config_ready = false;

// Topic (自动拼接，格式: r1203b1radar / r1203b1env / r1203b1audio)
char topic_radar[32];
char topic_env[32];
char topic_audio[32];

// ===================== Radar UART =====================
static const int RADAR_RX_PIN = 18;
static const int RADAR_TX_PIN = 17;
static const uint32_t RADAR_BAUD = 115200;

// ===================== Runtime state =====================
uint8_t heartbeat = 75;
uint8_t breath = 0;
uint8_t tidong = 0;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
uint32_t t_upload_last = 0;

void copy_cstr(char *dst, size_t dst_len, const String &src) {
  if (!dst || dst_len == 0) return;
  snprintf(dst, dst_len, "%s", src.c_str());
}

void lower_copy(char *dst, size_t dst_len, const char *src) {
  if (!dst || dst_len == 0) return;
  size_t i = 0;
  for (; i + 1 < dst_len && src && src[i]; ++i) {
    dst[i] = (char)tolower((unsigned char)src[i]);
  }
  dst[i] = '\0';
}

bool config_is_complete() {
  return cfg.wifi_ssid[0] &&
         cfg.bemfa_uid[0] &&
         cfg.room[0] &&
         cfg.bed[0] &&
         cfg.bemfa_host[0] &&
         cfg.bemfa_mqtt_port > 0;
}

void load_device_config() {
  Preferences prefs;
  memset(&cfg, 0, sizeof(cfg));
  prefs.begin(CONFIG_NS, true);
  copy_cstr(cfg.wifi_ssid, sizeof(cfg.wifi_ssid), prefs.getString("wifi_ssid", ""));
  copy_cstr(cfg.wifi_password, sizeof(cfg.wifi_password), prefs.getString("wifi_pass", ""));
  copy_cstr(cfg.bemfa_uid, sizeof(cfg.bemfa_uid), prefs.getString("bemfa_uid", ""));
  copy_cstr(cfg.bemfa_host, sizeof(cfg.bemfa_host), prefs.getString("bemfa_host", "bemfa.com"));
  cfg.bemfa_mqtt_port = prefs.getUShort("bemfa_port", 9501);
  copy_cstr(cfg.room, sizeof(cfg.room), prefs.getString("room", ""));
  copy_cstr(cfg.bed, sizeof(cfg.bed), prefs.getString("bed", ""));
  copy_cstr(cfg.device_id, sizeof(cfg.device_id), prefs.getString("device_id", ""));
  prefs.end();
  config_ready = config_is_complete();
}

void print_config_help() {
  Serial.println("[CFG] Commands:");
  Serial.println("  CFG?");
  Serial.println("  CFGSET ssid=your_wifi");
  Serial.println("  CFGSET password=your_password");
  Serial.println("  CFGSET uid=your_bemfa_uid");
  Serial.println("  CFGSET room=R1203");
  Serial.println("  CFGSET bed=B1");
  Serial.println("  CFGSET host=bemfa.com");
  Serial.println("  CFGSET port=9501");
  Serial.println("  CFGSET device_id=esp32-r1203-b1-radar-001");
  Serial.println("  CFGRESET");
  Serial.println("  REBOOT");
}

void print_device_config() {
  Serial.println("[CFG] current:");
  Serial.print("  role="); Serial.println(DEVICE_ROLE);
  Serial.print("  device_id="); Serial.println(cfg.device_id[0] ? cfg.device_id : "(empty)");
  Serial.print("  room="); Serial.println(cfg.room[0] ? cfg.room : "(empty)");
  Serial.print("  bed="); Serial.println(cfg.bed[0] ? cfg.bed : "(empty)");
  Serial.print("  wifi_ssid="); Serial.println(cfg.wifi_ssid[0] ? cfg.wifi_ssid : "(empty)");
  Serial.print("  wifi_password="); Serial.println(cfg.wifi_password[0] ? "***" : "(empty)");
  Serial.print("  bemfa_uid="); Serial.println(cfg.bemfa_uid[0] ? "***" : "(empty)");
  Serial.print("  bemfa_host="); Serial.println(cfg.bemfa_host);
  Serial.print("  bemfa_port="); Serial.println(cfg.bemfa_mqtt_port);
  Serial.print("  ready="); Serial.println(config_ready ? "yes" : "no");
}

bool save_config_value(const String &key_in, const String &value) {
  String key = key_in;
  key.trim();
  key.toLowerCase();

  Preferences prefs;
  prefs.begin(CONFIG_NS, false);
  bool ok = true;
  if (key == "ssid" || key == "wifi_ssid") {
    ok = prefs.putString("wifi_ssid", value) > 0;
  } else if (key == "password" || key == "pass" || key == "wifi_password") {
    ok = prefs.putString("wifi_pass", value) > 0;
  } else if (key == "uid" || key == "bemfa_uid") {
    ok = prefs.putString("bemfa_uid", value) > 0;
  } else if (key == "host" || key == "bemfa_host") {
    ok = prefs.putString("bemfa_host", value) > 0;
  } else if (key == "port" || key == "bemfa_port") {
    long port = value.toInt();
    ok = port > 0 && port <= 65535;
    if (ok) prefs.putUShort("bemfa_port", (uint16_t)port);
  } else if (key == "room") {
    ok = prefs.putString("room", value) > 0;
  } else if (key == "bed") {
    ok = prefs.putString("bed", value) > 0;
  } else if (key == "device_id") {
    ok = prefs.putString("device_id", value) > 0;
  } else {
    ok = false;
  }
  prefs.end();

  load_device_config();
  return ok;
}

void reset_device_config() {
  Preferences prefs;
  prefs.begin(CONFIG_NS, false);
  prefs.clear();
  prefs.end();
  load_device_config();
}

void process_config_line(String line) {
  line.trim();
  if (!line.length()) return;

  if (line == "HELP" || line == "CFGHELP") {
    print_config_help();
    return;
  }
  if (line == "CFG?") {
    print_device_config();
    return;
  }
  if (line == "CFGRESET") {
    reset_device_config();
    Serial.println("[CFG] cleared. Send REBOOT to restart.");
    return;
  }
  if (line == "REBOOT") {
    Serial.println("[CFG] rebooting...");
    delay(200);
    ESP.restart();
    return;
  }
  if (line.startsWith("CFGSET ")) {
    String rest = line.substring(7);
    int eq = rest.indexOf('=');
    if (eq <= 0) {
      Serial.println("[CFG] invalid. Use CFGSET key=value");
      return;
    }
    String key = rest.substring(0, eq);
    String value = rest.substring(eq + 1);
    key.trim();
    value.trim();
    bool ok = save_config_value(key, value);
    Serial.println(ok ? "[CFG] saved. Send REBOOT to apply network config." : "[CFG] save failed or unknown key.");
    print_device_config();
    return;
  }

  Serial.println("[CFG] unknown command. Send CFGHELP for help.");
}

void handle_serial_config() {
  static String line;
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      process_config_line(line);
      line = "";
    } else if (line.length() < 256) {
      line += c;
    }
  }
}

// ===================== NTP =====================
const char *ntp_server = "ntp.aliyun.com";
const long gmt_offset_sec = 8 * 3600;
const int daylight_offset_sec = 0;
bool ntp_synced = false;

void setup_ntp() {
  configTime(gmt_offset_sec, daylight_offset_sec, ntp_server);
  Serial.println("[NTP] syncing...");
  uint32_t t0 = millis();
  struct timeval tv;
  while (millis() - t0 < 5000) {
    gettimeofday(&tv, nullptr);
    if (tv.tv_sec > 1600000000) {
      ntp_synced = true;
      Serial.println("[NTP] synced");
      return;
    }
    delay(200);
  }
  Serial.println("[NTP] sync failed, ts will be 0");
}

uint64_t get_timestamp_ms() {
  if (!ntp_synced) return 0;
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  return (uint64_t)tv.tv_sec * 1000ULL + (uint64_t)tv.tv_usec / 1000ULL;
}

// ===================== WiFi =====================
void setup_wifi() {
  Serial.println();
  Serial.print("[WiFi] Connecting to ");
  Serial.println(cfg.wifi_ssid);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(cfg.wifi_ssid, cfg.wifi_password);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    if (millis() - t0 > 30000) {
      Serial.println("\n[WiFi] timeout, retry...");
      t0 = millis();
    }
  }
  Serial.println();
  Serial.println("[WiFi] connected");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());
}

// ===================== MQTT (巴法云) =====================
void build_topic_names() {
  char room_l[16];
  char bed_l[16];
  lower_copy(room_l, sizeof(room_l), cfg.room);
  lower_copy(bed_l, sizeof(bed_l), cfg.bed);
  snprintf(topic_radar, sizeof(topic_radar), "%s%sradar", room_l, bed_l);
  snprintf(topic_env, sizeof(topic_env), "%s%senv", room_l, bed_l);
  snprintf(topic_audio, sizeof(topic_audio), "%s%saudio", room_l, bed_l);
}

void mqtt_reconnect() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to ");
    Serial.print(cfg.bemfa_host);
    Serial.print("... ");
    mqttClient.setServer(cfg.bemfa_host, cfg.bemfa_mqtt_port);
    mqttClient.setKeepAlive(60);

    // 巴法云: ClientID = 私钥, 用户名密码为空
    if (mqttClient.connect(cfg.bemfa_uid, "", "")) {
      Serial.println("connected");
      Serial.print("[MQTT] Topics: ");
      Serial.print(topic_radar);
      Serial.print("  ");
      Serial.print(topic_env);
      Serial.print("  ");
      Serial.println(topic_audio);
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" retry in 2s");
      delay(2000);
    }
  }
}

bool mqtt_publish_json(const char *topic, const char *json_str) {
  if (!mqttClient.connected()) return false;
  return mqttClient.publish(topic, json_str);
}

// ===================== 数据发布 =====================
void send_radar_packet() {
  float motion = (float)tidong / 4.0f;
  int turning = (tidong >= 3) ? 1 : 0;

  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"breath_bpm\":%u,\"heart_bpm\":%u,\"motion\":%.3f,\"turning\":%d,\"ts\":%llu}",
           (unsigned)breath, (unsigned)heartbeat, motion, turning, get_timestamp_ms());

  bool ok = mqtt_publish_json(topic_radar, payload);
  Serial.print("[MQTT] radar -> ");
  Serial.print(topic_radar);
  Serial.print(": ");
  Serial.println(ok ? "OK" : "FAIL");
}

void send_env_packet() {
  float temp_c = 24.0f + ((float)random(-15, 15)) / 10.0f;
  float rh = 52.0f + ((float)random(-80, 80)) / 10.0f;
  float noise_db = 30.0f + tidong * 4.0f + ((float)random(0, 30)) / 10.0f;
  int co2_ppm = 650 + tidong * 90 + random(-40, 40);

  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"co2_ppm\":%d,\"temp_c\":%.1f,\"rh\":%.1f,\"noise_db\":%.1f,\"ts\":%llu}",
           co2_ppm, temp_c, rh, noise_db, get_timestamp_ms());

  bool ok = mqtt_publish_json(topic_env, payload);
  Serial.print("[MQTT] env -> ");
  Serial.print(topic_env);
  Serial.print(": ");
  Serial.println(ok ? "OK" : "FAIL");
}

void send_audio_packet() {
  int snore_level = (tidong >= 3) ? 2 : ((tidong >= 1) ? 1 : 0);
  int snore_count_1min = snore_level * random(0, 4);

  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"snore_count_1min\":%d,\"snore_level\":%d,\"ts\":%llu}",
           snore_count_1min, snore_level, get_timestamp_ms());

  bool ok = mqtt_publish_json(topic_audio, payload);
  Serial.print("[MQTT] audio -> ");
  Serial.print(topic_audio);
  Serial.print(": ");
  Serial.println(ok ? "OK" : "FAIL");
}

void upload_every_3s() {
  uint32_t now = millis();
  if (now - t_upload_last < 3000) return;
  t_upload_last = now;

  if (!mqttClient.connected()) return;

  send_radar_packet();
  send_env_packet();
  send_audio_packet();
}

// ===================== Radar 解析 =====================
void radar_serial_rd_old_style() {
  int num = Serial1.available();
  if (num <= 0) return;

  uint8_t serial_data[num];
  memset(serial_data, 0, num);
  Serial1.readBytes(serial_data, num);

  int i = 0;
  while (i <= num - 2) {
    if (serial_data[i] == 0x53 && serial_data[i + 1] == 0x59) {
      i += 2;
      if (i + 3 >= num) break;

      if (serial_data[i] == 0x01) {
        i += 8;
        continue;
      }

      if (serial_data[i] == 0x81 && serial_data[i + 3] == 0x01) {
        i = i + 4;
        if (i >= num) break;
        breath = serial_data[i];
        i = i + 3;
        continue;
      }

      if (serial_data[i] == 0x80 && serial_data[i + 1] == 0x03) {
        i = i + 4;
        if (i >= num) break;
        uint8_t mv = serial_data[i];
        if (mv == 0x00) {
          tidong = 0;
        } else if (mv == 0x01) {
          tidong = 1;
        } else if (mv > 0x01 && mv <= 0x1E) {
          tidong = 2;
        } else if (mv > 0x1E && mv <= 0x3C) {
          tidong = 3;
        } else {
          tidong = 4;
        }
        i = i + 3;
        continue;
      }
      i++;
    } else {
      i++;
    }
  }
}

// ===================== Setup / Loop =====================
void setup() {
  Serial.begin(115200);
  delay(300);

  randomSeed((uint32_t)esp_random());
  load_device_config();
  print_device_config();

  Serial1.begin(RADAR_BAUD, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);

  if (!config_ready) {
    Serial.println("[CFG] incomplete config. Network/MQTT is disabled until configuration is saved.");
    print_config_help();
    return;
  }

  build_topic_names();

  setup_wifi();
  setup_ntp();

  mqttClient.setServer(cfg.bemfa_host, cfg.bemfa_mqtt_port);
  mqtt_reconnect();

  Serial.println();
  Serial.println("========================================");
  Serial.print("  ESP32 Radar → 巴法云 MQTT");
  Serial.println();
  Serial.print("  Room: ");
  Serial.print(cfg.room);
  Serial.print("  Bed: ");
  Serial.print(cfg.bed);
  Serial.println();
  Serial.print("  Topic: ");
  Serial.print(topic_radar);
  Serial.print(" / ");
  Serial.print(topic_env);
  Serial.print(" / ");
  Serial.println(topic_audio);
  Serial.println("========================================");
  Serial.println("Wiring: Radar TX->GPIO18, Radar RX->GPIO17");
}

void loop() {
  handle_serial_config();
  if (!config_ready) {
    delay(50);
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
  }

  if (!mqttClient.connected()) {
    mqtt_reconnect();
  }
  mqttClient.loop();

  radar_serial_rd_old_style();
  upload_every_3s();

  delay(1);
}
