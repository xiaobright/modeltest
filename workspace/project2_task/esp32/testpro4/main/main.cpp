/* main/main.cpp */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "freertos/semphr.h"
#include <errno.h>

// TinyUSB 库 (esp_tinyusb 组件)
#include "tinyusb.h"
#include "tusb.h"

// TODO(v4): 网络回传尚未实现。当前固件仅通过 USB CDC 回传
// 传感器数据，缺少基于 Wi-Fi + MQTT 的远程回传能力。
// 协议规范请参考:
//   docs/protocol.md — "LAN 回传（MQTT 巴法云）" 章节
//   reference/espidf_protocol_contract.md — "MQTT" 章节
//   gateway/bed_config.py — topics_for() 函数，Topic 命名规范
// SDK 参考:
//   ESP-IDF Wi-Fi STA: esp_wifi.h, esp_event.h, esp_netif.h
//   ESP-IDF MQTT:      mqtt_client.h, espressif/mqtt 组件
//   Base64:            mbedtls/base64.h

// 自定义 C++ 库
#include "MLXManager.hpp"

// ==== 引脚定义 (请根据实际电路修改) ====
// I2C (MLX90640)
// 注意：I2C 初始化在 MLX90640_ESP32_Driver.c 中完成，这里仅作记录
// #define I2C_SDA 1
// #define I2C_SCL 2

// UART 1 (ToF Sensor 1 -> CDC 1)
#define UART1_TX_PIN 17
#define UART1_RX_PIN 18
#define UART1_PORT   UART_NUM_1

// UART 2 (ToF Sensor 2 -> CDC 2)
#define UART2_TX_PIN 47
#define UART2_RX_PIN 48
#define UART2_PORT   UART_NUM_2

static const char *TAG = "MAIN";

// TinyUSB descriptors (main/usb_descriptors.c)
extern const tusb_desc_device_t desc_device;
extern const uint8_t desc_configuration[];
extern const char *string_desc_arr[];
extern const int string_desc_arr_count;

static SemaphoreHandle_t s_usb_mutex = NULL;

static bool usb_lock(TickType_t ticks_to_wait) {
    if (s_usb_mutex == NULL) {
        return false;
    }
    return xSemaphoreTake(s_usb_mutex, ticks_to_wait) == pdTRUE;
}

static void usb_unlock(void) {
    if (s_usb_mutex != NULL) {
        xSemaphoreGive(s_usb_mutex);
    }
}

// CRC16-CCITT 校验函数
static uint16_t crc16_ccitt(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc <<= 1;
        }
    }
    return crc;
}

// 统一的数据包格式
// [0xAA, 0x55, SENSOR_TYPE, SENSOR_ID, LEN_LOW, LEN_HIGH] + DATA + [CRC_LOW, CRC_HIGH]
// SENSOR_TYPE: 0x01=MLX, 0x02=ToF
// SENSOR_ID: 传感器编号 (1, 2)
#define PACKET_SYNC1 0xAA
#define PACKET_SYNC2 0x55
#define SENSOR_TYPE_MLX 0x01
#define SENSOR_TYPE_TOF 0x02

// =====================
// Runtime config (NVS)
// =====================
// 固件只编译一次；WiFi、巴法云 UID、房间和床位通过 NVS 配置。
// 控制台命令:
//   CFG?
//   CFGSET room=R1203
//   CFGSET bed=B1
//   CFGSET ssid=your_wifi          (TODO: Wi-Fi + MQTT 补全后生效)
//   CFGSET password=your_password  (TODO: Wi-Fi + MQTT 补全后生效)
//   CFGSET uid=your_bemfa_uid      (TODO: Wi-Fi + MQTT 补全后生效)
//   CFGRESET
//   REBOOT
static const char *CONFIG_NS = "project2";
static const char *DEVICE_ROLE = "posture_sensors";

typedef struct {
    char wifi_ssid[33];
    char wifi_password[65];
    char bemfa_uid[96];
    char bemfa_host[64];
    uint16_t bemfa_mqtt_port;
    char room[16];
    char bed[16];
    char device_id[48];
} device_config_t;

static device_config_t s_device_config = {};
static bool s_device_config_ready = false;

// =====================
// 网络回传全局状态
// =====================
// TODO(v4): 补全 Wi-Fi/MQTT runtime state.

static bool s_uart_driver_installed[UART_NUM_MAX] = {};

static const int TOF_TARGET_BAUDRATE = 921600;
static const uint32_t TOF_COLD_BOOT_SETTLE_MS = 2000;
static const uint32_t TOF_UART_SWITCH_SETTLE_MS = 150;
static const uint32_t TOF_UART_RETRY_GAP_MS = 180;
static const uint32_t TOF_PROBE_TIMEOUT_MS = 700;
static const uint32_t TOF_PROBE_ATTEMPTS_PER_BAUD = 2;
static const uint32_t TOF_CMD_RETRIES = 2;

static const char *TOF_CMD_BAUD_QUERY = "AT+BAUD?\r\n";
static const char *TOF_CMD_DISP_OFF = "AT+DISP=0\r\n";
static const char *TOF_CMD_BAUD_921600 = "AT+BAUD=5\r\n";
static const char *TOF_CMD_ANTIMMI = "AT+ANTIMMI=-1\r\n";
static const char *TOF_CMD_FPS = "AT+FPS=8\r\n";
static const char *TOF_CMD_DISP_ON = "AT+DISP=4\r\n";

static void lower_copy(char *dst, size_t dst_len, const char *src) {
    if (dst == NULL || dst_len == 0) return;
    size_t i = 0;
    for (; i + 1 < dst_len && src != NULL && src[i] != '\0'; ++i) {
        dst[i] = (char)tolower((unsigned char)src[i]);
    }
    dst[i] = '\0';
}

static bool config_is_complete(void) {
    // TODO(v4): Wi-Fi + MQTT 补全后，检查 wifi_ssid / bemfa_uid 等是否非空
    // 当前只需要 room 和 bed 即可运行 USB 采集
    return s_device_config.room[0] != '\0' &&
           s_device_config.bed[0] != '\0';
}

static void nvs_get_str_or_default(nvs_handle_t handle, const char *key,
                                   char *dst, size_t dst_len, const char *fallback) {
    if (dst == NULL || dst_len == 0) return;
    dst[0] = '\0';
    size_t required = dst_len;
    esp_err_t err = nvs_get_str(handle, key, dst, &required);
    if (err == ESP_ERR_NVS_NOT_FOUND || err == ESP_ERR_NVS_INVALID_LENGTH) {
        snprintf(dst, dst_len, "%s", fallback ? fallback : "");
        return;
    }
    if (err != ESP_OK) {
        snprintf(dst, dst_len, "%s", fallback ? fallback : "");
    }
}

static void load_device_config(void) {
    memset(&s_device_config, 0, sizeof(s_device_config));
    nvs_handle_t handle;
    esp_err_t err = nvs_open(CONFIG_NS, NVS_READONLY, &handle);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        snprintf(s_device_config.bemfa_host, sizeof(s_device_config.bemfa_host), "bemfa.com");
        s_device_config.bemfa_mqtt_port = 9501;
        s_device_config_ready = false;
        return;
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS config: %s", esp_err_to_name(err));
        s_device_config_ready = false;
        return;
    }

    nvs_get_str_or_default(handle, "wifi_ssid", s_device_config.wifi_ssid, sizeof(s_device_config.wifi_ssid), "");
    nvs_get_str_or_default(handle, "wifi_pass", s_device_config.wifi_password, sizeof(s_device_config.wifi_password), "");
    nvs_get_str_or_default(handle, "bemfa_uid", s_device_config.bemfa_uid, sizeof(s_device_config.bemfa_uid), "");
    nvs_get_str_or_default(handle, "bemfa_host", s_device_config.bemfa_host, sizeof(s_device_config.bemfa_host), "bemfa.com");
    nvs_get_str_or_default(handle, "room", s_device_config.room, sizeof(s_device_config.room), "");
    nvs_get_str_or_default(handle, "bed", s_device_config.bed, sizeof(s_device_config.bed), "");
    nvs_get_str_or_default(handle, "device_id", s_device_config.device_id, sizeof(s_device_config.device_id), "");
    uint16_t port = 9501;
    if (nvs_get_u16(handle, "bemfa_port", &port) != ESP_OK) {
        port = 9501;
    }
    s_device_config.bemfa_mqtt_port = port;
    nvs_close(handle);
    s_device_config_ready = config_is_complete();
}

static void print_config_help(void) {
    ESP_LOGI(TAG, "CFG commands:");
    ESP_LOGI(TAG, "  CFG?");
    ESP_LOGI(TAG, "  CFGSET room=R1203");
    ESP_LOGI(TAG, "  CFGSET bed=B1");
    ESP_LOGI(TAG, "  CFGSET ssid=your_wifi");
    ESP_LOGI(TAG, "  CFGSET password=your_password");
    ESP_LOGI(TAG, "  CFGSET uid=your_bemfa_uid");
    ESP_LOGI(TAG, "  CFGSET host=bemfa.com");
    ESP_LOGI(TAG, "  CFGSET port=9501");
    ESP_LOGI(TAG, "  CFGSET device_id=esp32-r1203-b1-posture-001");
    ESP_LOGI(TAG, "  CFGRESET");
    ESP_LOGI(TAG, "  REBOOT");
}

static void print_device_config(void) {
    ESP_LOGI(TAG, "Config role=%s ready=%s", DEVICE_ROLE, s_device_config_ready ? "yes" : "no");
    ESP_LOGI(TAG, "  device_id=%s", s_device_config.device_id[0] ? s_device_config.device_id : "(empty)");
    ESP_LOGI(TAG, "  room=%s bed=%s",
             s_device_config.room[0] ? s_device_config.room : "(empty)",
             s_device_config.bed[0] ? s_device_config.bed : "(empty)");
    ESP_LOGI(TAG, "  wifi_ssid=%s", s_device_config.wifi_ssid[0] ? s_device_config.wifi_ssid : "(empty)");
    ESP_LOGI(TAG, "  wifi_password=%s", s_device_config.wifi_password[0] ? "***" : "(empty)");
    ESP_LOGI(TAG, "  bemfa_uid=%s", s_device_config.bemfa_uid[0] ? "***" : "(empty)");
    ESP_LOGI(TAG, "  bemfa_host=%s port=%u",
             s_device_config.bemfa_host[0] ? s_device_config.bemfa_host : "(empty)",
             (unsigned)s_device_config.bemfa_mqtt_port);
}

static char *trim_in_place(char *s) {
    if (s == NULL) return s;
    while (*s && isspace((unsigned char)*s)) s++;
    char *end = s + strlen(s);
    while (end > s && isspace((unsigned char)*(end - 1))) {
        *(--end) = '\0';
    }
    return s;
}

static bool save_config_value(const char *key_in, const char *value) {
    if (key_in == NULL || value == NULL) return false;
    char key[32];
    lower_copy(key, sizeof(key), key_in);

    nvs_handle_t handle;
    esp_err_t err = nvs_open(CONFIG_NS, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS for write: %s", esp_err_to_name(err));
        return false;
    }

    bool known = true;
    if (strcmp(key, "ssid") == 0 || strcmp(key, "wifi_ssid") == 0) {
        err = nvs_set_str(handle, "wifi_ssid", value);
    } else if (strcmp(key, "password") == 0 || strcmp(key, "pass") == 0 || strcmp(key, "wifi_password") == 0) {
        err = nvs_set_str(handle, "wifi_pass", value);
    } else if (strcmp(key, "uid") == 0 || strcmp(key, "bemfa_uid") == 0) {
        err = nvs_set_str(handle, "bemfa_uid", value);
    } else if (strcmp(key, "host") == 0 || strcmp(key, "bemfa_host") == 0) {
        err = nvs_set_str(handle, "bemfa_host", value);
    } else if (strcmp(key, "port") == 0 || strcmp(key, "bemfa_port") == 0) {
        long port = strtol(value, NULL, 10);
        if (port <= 0 || port > 65535) {
            known = false;
            err = ESP_ERR_INVALID_ARG;
        } else {
            err = nvs_set_u16(handle, "bemfa_port", (uint16_t)port);
        }
    } else if (strcmp(key, "room") == 0) {
        err = nvs_set_str(handle, "room", value);
    } else if (strcmp(key, "bed") == 0) {
        err = nvs_set_str(handle, "bed", value);
    } else if (strcmp(key, "device_id") == 0) {
        err = nvs_set_str(handle, "device_id", value);
    } else {
        known = false;
        err = ESP_ERR_INVALID_ARG;
    }

    if (known && err == ESP_OK) {
        err = nvs_commit(handle);
    }
    nvs_close(handle);
    load_device_config();
    return known && err == ESP_OK;
}

static void reset_device_config(void) {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(CONFIG_NS, NVS_READWRITE, &handle);
    if (err == ESP_OK) {
        nvs_erase_all(handle);
        nvs_commit(handle);
        nvs_close(handle);
    }
    load_device_config();
}

static void process_config_line(char *line) {
    char *cmd = trim_in_place(line);
    if (cmd[0] == '\0') return;

    if (strcmp(cmd, "HELP") == 0 || strcmp(cmd, "CFGHELP") == 0) {
        print_config_help();
        return;
    }
    if (strcmp(cmd, "CFG?") == 0) {
        print_device_config();
        return;
    }
    if (strcmp(cmd, "CFGRESET") == 0) {
        reset_device_config();
        ESP_LOGW(TAG, "Config cleared. Send REBOOT to restart.");
        return;
    }
    if (strcmp(cmd, "REBOOT") == 0) {
        ESP_LOGW(TAG, "Rebooting...");
        vTaskDelay(pdMS_TO_TICKS(200));
        esp_restart();
        return;
    }
    if (strncmp(cmd, "CFGSET ", 7) == 0) {
        char *pair = trim_in_place(cmd + 7);
        char *eq = strchr(pair, '=');
        if (eq == NULL || eq == pair) {
            ESP_LOGW(TAG, "Invalid CFGSET. Use CFGSET key=value");
            return;
        }
        *eq = '\0';
        char *key = trim_in_place(pair);
        char *value = trim_in_place(eq + 1);
        bool ok = save_config_value(key, value);
        ESP_LOGI(TAG, "%s", ok ? "Config saved. Send REBOOT to apply network config." : "Config save failed or unknown key.");
        print_device_config();
        return;
    }

    ESP_LOGW(TAG, "Unknown command. Send CFGHELP for help.");
}

static void config_console_task(void *pvParameters) {
    (void)pvParameters;
    setvbuf(stdin, NULL, _IONBF, 0);
    char line[384];
    size_t pos = 0;
    while (1) {
        int ch = getchar();
        if (ch == EOF) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }
        if (ch == '\r' || ch == '\n') {
            line[pos] = '\0';
            process_config_line(line);
            pos = 0;
        } else if (pos + 1 < sizeof(line)) {
            line[pos++] = (char)ch;
        }
    }
}

// ==========================================================
// TODO(v4): 网络回传链路 — 需要补全
//
// 当前固件仅通过 USB CDC 回传传感器数据。需要恢复 Wi-Fi STA
// 连接 + 巴法云 MQTT 客户端，并与 USB CDC 保持并行回传。
//
// 协议规范:
//   docs/protocol.md — "LAN 回传（MQTT 巴法云）" 章节
//   reference/espidf_protocol_contract.md — "MQTT" 章节
//   gateway/bed_config.py — topics_for() 函数，Topic 命名规范
//
// NVS 配置读写已经在设备配置逻辑中预留。
// ==========================================================

// ==========================================================
// 任务 1: ToF 传感器数据回传 (单任务处理 UART1/2，共用 CDC 1)
// ESP32 主动接收 UART 数据并通过 USB CDC1 持续回传
// ==========================================================
struct TofStreamParams {
    uart_port_t uart_num; // 物理串口编号
    uint8_t src_id;       // ToF 数据来源 ID
};

static const TofStreamParams s_tof_params[] = {
    { .uart_num = UART1_PORT, .src_id = 1 },
    { .uart_num = UART2_PORT, .src_id = 2 },
};

static void usb_send_tof_payload(uint8_t src_id, const uint8_t *payload, uint16_t len) {
    bool usb_connected = false;
    if (usb_lock(pdMS_TO_TICKS(2))) {
        usb_connected = tud_cdc_n_connected(1);
        if (usb_connected) {
            // 统一包头格式: [0xAA, 0x55, SENSOR_TYPE, SENSOR_ID, LEN_LOW, LEN_HIGH]
            uint8_t header[6] = {
                PACKET_SYNC1, PACKET_SYNC2, SENSOR_TYPE_TOF, src_id,
                (uint8_t)(len & 0xFF), (uint8_t)((len >> 8) & 0xFF)
            };
            tud_cdc_n_write(1, header, sizeof(header));
            tud_cdc_n_write_flush(1);
        }
        usb_unlock();
    }

    if (usb_connected) {
        uint32_t sent = 0;
        while (sent < len) {
            if (!usb_lock(pdMS_TO_TICKS(2))) {
                vTaskDelay(1);
                continue;
            }
            int avail = tud_cdc_n_write_available(1);
            if (avail > 0) {
                int chunk = (len - sent) > (uint32_t)avail ? avail : (int)(len - sent);
                int written = tud_cdc_n_write(1, payload + sent, chunk);
                sent += written;
                tud_cdc_n_write_flush(1);
            }
            usb_unlock();
            vTaskDelay(1);
        }

        // 发送CRC校验
        uint16_t crc = crc16_ccitt(payload, len);
        uint8_t crc_bytes[2] = {
            (uint8_t)(crc & 0xFF), (uint8_t)((crc >> 8) & 0xFF)
        };
        if (usb_lock(pdMS_TO_TICKS(2))) {
            tud_cdc_n_write(1, crc_bytes, 2);
            tud_cdc_n_write_flush(1);
            usb_unlock();
        }
    }


    // TODO(v4): mirror this payload to the configured network backhaul.
    // NOTE: when encoding MQTT JSON, a small fixed buffer is a common mistake:
    // char b64_buf[256];  // too small for full ToF payload_b64 JSON
}

// MaixSense帧解析器
typedef struct {
    uint8_t buffer[12000];  // 缓冲区 (留余量)
    uint32_t buffer_len;    // 当前缓冲区长度
    uint32_t frames_parsed; // 统计解析的帧数
} MaixSenseFrameParser;

// 查找并解析完整帧
// 返回: 找到的帧长度 (10002字节), 或 0 表示未找到完整帧
static uint32_t parse_maixsense_frame(MaixSenseFrameParser *parser, uint8_t *frame_out) {
    // MaixSense 帧格式: [00 FF] [LEN_L LEN_H] [DATA...] [CHECKSUM] [DD]
    
    // 查找帧头 0x00 0xFF
    for (uint32_t i = 0; i < parser->buffer_len - 1; i++) {
        if (parser->buffer[i] == 0x00 && parser->buffer[i + 1] == 0xFF) {
            // 找到帧头，检查是否有足够数据读取长度字段
            if (i + 4 > parser->buffer_len) {
                // 数据不足以读取长度，移除帧头之前的数据
                if (i > 0) {
                    uint32_t remaining = parser->buffer_len - i;
                    memmove(parser->buffer, &parser->buffer[i], remaining);
                    parser->buffer_len = remaining;
                }
                return 0;
            }
            
            // 读取数据长度（小端序）
            uint16_t data_len = parser->buffer[i + 2] | (parser->buffer[i + 3] << 8);
            uint32_t frame_len = 2 + 2 + data_len + 1 + 1;  // head + len + data + checksum + tail
            
            // 检查是否有完整帧
            if (i + frame_len <= parser->buffer_len) {
                // 检查帧尾
                if (parser->buffer[i + frame_len - 1] != 0xDD) {
                    // 帧尾不匹配，这是个假的帧头，跳过
                    continue;
                }
                
                // 复制完整帧
                memcpy(frame_out, &parser->buffer[i], frame_len);
                
                // 移除已处理的数据
                uint32_t remaining = parser->buffer_len - (i + frame_len);
                if (remaining > 0) {
                    memmove(parser->buffer, &parser->buffer[i + frame_len], remaining);
                }
                parser->buffer_len = remaining;
                parser->frames_parsed++;
                
                return frame_len;
            } else {
                // 找到帧头但数据不足，移除帧头之前的数据
                if (i > 0) {
                    uint32_t remaining = parser->buffer_len - i;
                    memmove(parser->buffer, &parser->buffer[i], remaining);
                    parser->buffer_len = remaining;
                }
                return 0;  // 等待更多数据
            }
        }
    }
    
    // 没找到帧头，保留最后1个字节（可能是0x00的开头）
    if (parser->buffer_len > 1) {
        parser->buffer[0] = parser->buffer[parser->buffer_len - 1];
        parser->buffer_len = 1;
    }
    
    return 0;
}

void tof_stream_task(void *pvParameters) {
    (void)pvParameters;
    
    // 为每个传感器分配帧解析器
    static MaixSenseFrameParser parser1 = {0};  // UART1
    static MaixSenseFrameParser parser2 = {0};  // UART2
    
    // 为每个传感器分配独立的帧缓冲区（交替发送）
    static uint8_t frame_buffer1[12000];        // UART1帧缓冲
    static uint8_t frame_buffer2[12000];        // UART2帧缓冲
    static bool frame1_ready = false;           // 帧1是否就绪
    static bool frame2_ready = false;           // 帧2是否就绪
    static uint16_t frame1_len = 0;
    static uint16_t frame2_len = 0;
    
    uint8_t uart_buf[512];                      // UART读取缓冲区
    
    // 调试计数器
    static uint32_t uart1_total_bytes = 0;
    static uint32_t uart2_total_bytes = 0;
    static uint32_t sent_frames = 0;            // 已发送帧数
    static uint32_t last_debug_time = 0;
    
    // 交替发送状态：true=下次发送传感器1, false=下次发送传感器2
    static bool send_sensor1_next = true;
    
    ESP_LOGI(TAG, "Starting ToF Stream Task with Alternating Frame Sending");

    while (1) {
        bool did_work = false;
        // ===== 阶段1：接收并解析数据 =====
        
        // 处理UART1（允许覆盖旧帧，保留最新帧）
        size_t buffered_len = 0;
        uart_get_buffered_data_len(UART1_PORT, &buffered_len);
        if (buffered_len > 0) {
            int len = uart_read_bytes(UART1_PORT, uart_buf,
                                      (buffered_len > sizeof(uart_buf)) ? sizeof(uart_buf) : buffered_len,
                                      pdMS_TO_TICKS(2));
            if (len > 0) {
                uart1_total_bytes += len;
                did_work = true;

                // 添加到解析器缓冲区；若溢出则丢弃旧数据保留最新块
                if (parser1.buffer_len + (uint32_t)len < sizeof(parser1.buffer)) {
                    memcpy(&parser1.buffer[parser1.buffer_len], uart_buf, len);
                    parser1.buffer_len += (uint32_t)len;
                } else {
                    ESP_LOGW(TAG, "UART1 buffer overflow, dropping old data");
                    if ((uint32_t)len >= sizeof(parser1.buffer)) {
                        memcpy(parser1.buffer, &uart_buf[len - sizeof(parser1.buffer)], sizeof(parser1.buffer));
                        parser1.buffer_len = sizeof(parser1.buffer);
                    } else {
                        memcpy(parser1.buffer, uart_buf, len);
                        parser1.buffer_len = (uint32_t)len;
                    }
                }

                // 尝试解析完整帧（覆盖旧帧）
                uint32_t parsed_len = parse_maixsense_frame(&parser1, frame_buffer1);
                if (parsed_len > 0) {
                    frame1_ready = true;
                    frame1_len = parsed_len;
                }
            }
        }
        
        // 处理UART2（允许覆盖旧帧，保留最新帧）
        buffered_len = 0;
        uart_get_buffered_data_len(UART2_PORT, &buffered_len);
        if (buffered_len > 0) {
            int len = uart_read_bytes(UART2_PORT, uart_buf,
                                      (buffered_len > sizeof(uart_buf)) ? sizeof(uart_buf) : buffered_len,
                                      pdMS_TO_TICKS(2));
            if (len > 0) {
                uart2_total_bytes += len;
                did_work = true;

                // 添加到解析器缓冲区；若溢出则丢弃旧数据保留最新块
                if (parser2.buffer_len + (uint32_t)len < sizeof(parser2.buffer)) {
                    memcpy(&parser2.buffer[parser2.buffer_len], uart_buf, len);
                    parser2.buffer_len += (uint32_t)len;
                } else {
                    ESP_LOGW(TAG, "UART2 buffer overflow, dropping old data");
                    if ((uint32_t)len >= sizeof(parser2.buffer)) {
                        memcpy(parser2.buffer, &uart_buf[len - sizeof(parser2.buffer)], sizeof(parser2.buffer));
                        parser2.buffer_len = sizeof(parser2.buffer);
                    } else {
                        memcpy(parser2.buffer, uart_buf, len);
                        parser2.buffer_len = (uint32_t)len;
                    }
                }

                // 尝试解析完整帧（覆盖旧帧）
                uint32_t parsed_len = parse_maixsense_frame(&parser2, frame_buffer2);
                if (parsed_len > 0) {
                    frame2_ready = true;
                    frame2_len = parsed_len;
                }
            }
        }
        
        // ===== 阶段2：交替发送帧 =====
        
        // 如果轮到发送传感器1且帧已就绪
        if (send_sensor1_next && frame1_ready) {
            usb_send_tof_payload(1, frame_buffer1, frame1_len);
            frame1_ready = false;
            send_sensor1_next = false;  // 下次发送传感器2
            sent_frames++;
            did_work = true;
        }
        // 如果轮到发送传感器2且帧已就绪
        else if (!send_sensor1_next && frame2_ready) {
            usb_send_tof_payload(2, frame_buffer2, frame2_len);
            frame2_ready = false;
            send_sensor1_next = true;   // 下次发送传感器1
            sent_frames++;
            did_work = true;
        }
        // 如果当前轮次的传感器没有帧，但另一个有，则跳过（保持严格交替）
        else if (send_sensor1_next && !frame1_ready && frame2_ready) {
            // 等待传感器1的帧，暂不发送传感器2
            vTaskDelay(pdMS_TO_TICKS(1));  // 短暂等待
        }
        else if (!send_sensor1_next && !frame2_ready && frame1_ready) {
            // 等待传感器2的帧，暂不发送传感器1
            vTaskDelay(pdMS_TO_TICKS(1));  // 短暂等待
        }
        
        // 每30秒打印状态统计
        uint32_t now = xTaskGetTickCount();
        if (now - last_debug_time > pdMS_TO_TICKS(30000)) {
            ESP_LOGI(TAG, "ToF Status: Sensor1=%lu frames, Sensor2=%lu frames, Sent=%lu frames", 
                     parser1.frames_parsed, parser2.frames_parsed, sent_frames);
            last_debug_time = now;
        }

        if (did_work) {
            vTaskDelay(pdMS_TO_TICKS(1));
        } else {
            vTaskDelay(pdMS_TO_TICKS(5));
        }
    }
}

// ==========================================================
// 任务 2: MLX90640 数据发送
// 负责从 MLXManager 获取计算好的温度，发给 CDC 0
// ==========================================================
void mlx_sender_task(void *pvParameters) {
    MLXManager *mlx = (MLXManager *)pvParameters;
    
    // 分配大缓冲区用于存放浮点数据
    // 768 float * 4 bytes = 3072 bytes
    static float temp_buf1[768];
    static float temp_buf2[768];

    ESP_LOGI(TAG, "Starting MLX Sender Task on CDC 0");

    while (1) {
        // 1. 获取最新数据 (线程安全复制)
        mlx->get_temperature_data(temp_buf1, temp_buf2);
        const uint32_t total = sizeof(temp_buf1);

        // 2. 检查 USB 连接状态
        bool cdc0_connected = false;
        if (usb_lock(pdMS_TO_TICKS(2))) {
            cdc0_connected = tud_cdc_n_connected(0);
            usb_unlock();
        }
        if (cdc0_connected) {
            
            // --- 发送传感器 1 数据 ---
            // 发送统一包头: [0xAA, 0x55, TYPE, ID, LEN_LOW, LEN_HIGH]
            if (usb_lock(pdMS_TO_TICKS(2))) {
                uint8_t header1[6] = {
                    PACKET_SYNC1, PACKET_SYNC2, SENSOR_TYPE_MLX, 0x01,
                    (uint8_t)(total & 0xFF), (uint8_t)((total >> 8) & 0xFF)
                };
                tud_cdc_n_write(0, header1, sizeof(header1));
                tud_cdc_n_write_flush(0);
                usb_unlock();
            }
            
            // 发送 3072 字节的 Body
            // TinyUSB 的内部 FIFO 默认可能只有 64~256 字节，所以要分块发送或等待
            uint32_t sent = 0;
            uint8_t *p = (uint8_t*)temp_buf1;

            while (sent < total) {
                if (usb_lock(pdMS_TO_TICKS(2))) {
                    int avail = tud_cdc_n_write_available(0);
                    if (avail > 0) {
                        int chunk = (total - sent) > avail ? avail : (total - sent);
                        int written = tud_cdc_n_write(0, p + sent, chunk);
                        sent += written;
                        tud_cdc_n_write_flush(0);
                    }
                    usb_unlock();
                }
                vTaskDelay(1); // 等待 USB 主机取走数据
            }
            
            // 发送CRC校验
            uint16_t crc1 = crc16_ccitt((uint8_t*)temp_buf1, total);
            if (usb_lock(pdMS_TO_TICKS(2))) {
                uint8_t crc_bytes[2] = {
                    (uint8_t)(crc1 & 0xFF), (uint8_t)((crc1 >> 8) & 0xFF)
                };
                tud_cdc_n_write(0, crc_bytes, 2);
                tud_cdc_n_write_flush(0);
                usb_unlock();
            }

            // --- 发送传感器 2 数据 ---
            // 发送统一包头
            if (usb_lock(pdMS_TO_TICKS(2))) {
                uint8_t header2[6] = {
                    PACKET_SYNC1, PACKET_SYNC2, SENSOR_TYPE_MLX, 0x02,
                    (uint8_t)(total & 0xFF), (uint8_t)((total >> 8) & 0xFF)
                };
                tud_cdc_n_write(0, header2, sizeof(header2));
                tud_cdc_n_write_flush(0);
                usb_unlock();
            }
            
            sent = 0;
            p = (uint8_t*)temp_buf2;
            while (sent < total) {
                if (usb_lock(pdMS_TO_TICKS(2))) {
                    int avail = tud_cdc_n_write_available(0);
                    if (avail > 0) {
                        int chunk = (total - sent) > avail ? avail : (total - sent);
                        int written = tud_cdc_n_write(0, p + sent, chunk);
                        sent += written;
                        tud_cdc_n_write_flush(0);
                    }
                    usb_unlock();
                }
                vTaskDelay(1);
            }
            
            // 发送CRC校验
            uint16_t crc2 = crc16_ccitt((uint8_t*)temp_buf2, total);
            if (usb_lock(pdMS_TO_TICKS(2))) {
                uint8_t crc_bytes[2] = {
                    (uint8_t)(crc2 & 0xFF), (uint8_t)((crc2 >> 8) & 0xFF)
                };
                tud_cdc_n_write(0, crc_bytes, 2);
                tud_cdc_n_write_flush(0);
                usb_unlock();
            }
        }

        // TODO(v4): mirror both MLX payloads to the configured network backhaul.

        // 控制刷新率，例如 4Hz (250ms)，跟 MLXManager 内部的 FPS 匹配即可
        vTaskDelay(pdMS_TO_TICKS(250));
    }
}

// ==========================================================
// 辅助函数: 初始化物理 UART (支持指定波特率)
// ==========================================================
void init_physical_uart(uart_port_t uart_num, int tx_pin, int rx_pin, int baud_rate) {
    uart_config_t uart_config = {
        .baud_rate = baud_rate,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .rx_flow_ctrl_thresh = 0,
        .source_clk = UART_SCLK_DEFAULT,
    };
    // Buffer 大小设大一点 (4096)，防止高速数据溢出
    if (!s_uart_driver_installed[uart_num]) {
        ESP_ERROR_CHECK(uart_driver_install(uart_num, 4096, 512, 0, NULL, 0));
        s_uart_driver_installed[uart_num] = true;
    }
    ESP_ERROR_CHECK(uart_param_config(uart_num, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(uart_num, tx_pin, rx_pin, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
}

// 辅助函数: 重新配置UART波特率
void reconfigure_uart_baudrate(uart_port_t uart_num, int new_baud_rate) {
    ESP_ERROR_CHECK(uart_set_baudrate(uart_num, new_baud_rate));
    ESP_LOGI(TAG, "UART%d baudrate changed to %d", uart_num, new_baud_rate);
}

// 辅助函数: 等待UART响应
// 返回true表示收到响应，false表示超时
bool uart_wait_response(uart_port_t uart_num, const char* expected, uint32_t timeout_ms) {
    uint8_t buf[256];
    int total_read = 0;
    uint32_t start = xTaskGetTickCount();
    
    while ((xTaskGetTickCount() - start) < pdMS_TO_TICKS(timeout_ms)) {
        int len = uart_read_bytes(uart_num, buf + total_read, sizeof(buf) - total_read - 1, pdMS_TO_TICKS(50));
        if (len > 0) {
            total_read += len;
            buf[total_read] = '\0';
            
            // 如果不需要匹配特定字符串，只要有数据就返回
            if (expected == NULL) {
                ESP_LOGI(TAG, "UART%d Response: %s", uart_num, buf);
                return true;
            }
            
            // 检查是否包含期望的字符串
            if (strstr((char*)buf, expected) != NULL) {
                ESP_LOGI(TAG, "UART%d Response: %s", uart_num, buf);
                return true;
            }
        }
    }
    
    if (total_read > 0) {
        buf[total_read] = '\0';
        ESP_LOGW(TAG, "UART%d Timeout, got: %s", uart_num, buf);
    } else {
        ESP_LOGW(TAG, "UART%d Timeout, no response", uart_num);
    }
    return false;
}

static void uart_clear_input(uart_port_t uart_num) {
    uart_flush_input(uart_num);
    vTaskDelay(pdMS_TO_TICKS(20));
}

static bool tof_send_command_with_retry(uart_port_t uart_num,
                                        const char *sensor_name,
                                        const char *cmd,
                                        const char *expected,
                                        uint32_t timeout_ms,
                                        uint32_t retries) {
    for (uint32_t attempt = 1; attempt <= retries; ++attempt) {
        uart_clear_input(uart_num);
        ESP_LOGI(TAG, "%s cmd attempt %lu/%lu: %s",
                 sensor_name,
                 (unsigned long)attempt,
                 (unsigned long)retries,
                 cmd);
        uart_write_bytes(uart_num, cmd, strlen(cmd));
        if (uart_wait_response(uart_num, expected, timeout_ms)) {
            return true;
        }
        vTaskDelay(pdMS_TO_TICKS(TOF_UART_RETRY_GAP_MS));
    }
    return false;
}

static bool probe_sensor_baudrate(uart_port_t uart_num,
                                  const char *sensor_name,
                                  int baud_rate,
                                  uint32_t attempts) {
    reconfigure_uart_baudrate(uart_num, baud_rate);
    vTaskDelay(pdMS_TO_TICKS(TOF_UART_SWITCH_SETTLE_MS));

    for (uint32_t attempt = 1; attempt <= attempts; ++attempt) {
        uart_clear_input(uart_num);
        ESP_LOGI(TAG, "%s probe %lu/%lu at %d baud",
                 sensor_name,
                 (unsigned long)attempt,
                 (unsigned long)attempts,
                 baud_rate);
        uart_write_bytes(uart_num, TOF_CMD_BAUD_QUERY, strlen(TOF_CMD_BAUD_QUERY));
        if (uart_wait_response(uart_num, "+BAUD", TOF_PROBE_TIMEOUT_MS)) {
            return true;
        }
        vTaskDelay(pdMS_TO_TICKS(TOF_UART_RETRY_GAP_MS));
    }
    return false;
}

static int detect_sensor_baudrate(uart_port_t uart_num, const char *sensor_name) {
    if (probe_sensor_baudrate(uart_num, sensor_name, 115200, TOF_PROBE_ATTEMPTS_PER_BAUD)) {
        return 115200;
    }
    if (probe_sensor_baudrate(uart_num, sensor_name, TOF_TARGET_BAUDRATE, TOF_PROBE_ATTEMPTS_PER_BAUD)) {
        return TOF_TARGET_BAUDRATE;
    }
    return 0;
}

static bool switch_sensor_to_target_baud(uart_port_t uart_num,
                                         const char *sensor_name,
                                         int *current_baudrate) {
    if (current_baudrate == NULL || *current_baudrate == TOF_TARGET_BAUDRATE) {
        return true;
    }

    ESP_LOGI(TAG, "%s switching from %d to %d",
             sensor_name, *current_baudrate, TOF_TARGET_BAUDRATE);
    if (!tof_send_command_with_retry(uart_num, sensor_name, TOF_CMD_BAUD_921600, "OK", 1000, TOF_CMD_RETRIES)) {
        ESP_LOGW(TAG, "%s did not ACK baudrate switch, still trying to verify at %d",
                 sensor_name, TOF_TARGET_BAUDRATE);
    }

    reconfigure_uart_baudrate(uart_num, TOF_TARGET_BAUDRATE);
    vTaskDelay(pdMS_TO_TICKS(TOF_UART_SWITCH_SETTLE_MS));

    if (!probe_sensor_baudrate(uart_num, sensor_name, TOF_TARGET_BAUDRATE, TOF_PROBE_ATTEMPTS_PER_BAUD)) {
        ESP_LOGE(TAG, "%s failed to verify %d baud", sensor_name, TOF_TARGET_BAUDRATE);
        return false;
    }

    *current_baudrate = TOF_TARGET_BAUDRATE;
    return true;
}

static bool initialize_tof_sensors(void) {
    ESP_LOGI(TAG, "=== Phase 1: Auto-detect sensor baudrate ===");
    ESP_LOGI(TAG, "Waiting for ToF sensors to complete cold boot (%ums)...", TOF_COLD_BOOT_SETTLE_MS);
    vTaskDelay(pdMS_TO_TICKS(TOF_COLD_BOOT_SETTLE_MS));

    init_physical_uart(UART1_PORT, UART1_TX_PIN, UART1_RX_PIN, 115200);
    init_physical_uart(UART2_PORT, UART2_TX_PIN, UART2_RX_PIN, 115200);
    vTaskDelay(pdMS_TO_TICKS(TOF_UART_SWITCH_SETTLE_MS));

    int uart1_baud = detect_sensor_baudrate(UART1_PORT, "UART1");
    int uart2_baud = detect_sensor_baudrate(UART2_PORT, "UART2");

    if (uart1_baud == 0 || uart2_baud == 0) {
        ESP_LOGE(TAG, "Failed to detect ToF sensors: uart1=%d uart2=%d", uart1_baud, uart2_baud);
        return false;
    }

    ESP_LOGI(TAG, "Detected ToF baudrates: uart1=%d uart2=%d", uart1_baud, uart2_baud);

    ESP_LOGI(TAG, "Stopping sensor data output...");
    tof_send_command_with_retry(UART1_PORT, "UART1", TOF_CMD_DISP_OFF, "OK", 1000, TOF_CMD_RETRIES);
    tof_send_command_with_retry(UART2_PORT, "UART2", TOF_CMD_DISP_OFF, "OK", 1000, TOF_CMD_RETRIES);
    vTaskDelay(pdMS_TO_TICKS(120));

    ESP_LOGI(TAG, "=== Phase 2: Switch baudrate to %d ===", TOF_TARGET_BAUDRATE);
    bool uart1_switched = switch_sensor_to_target_baud(UART1_PORT, "UART1", &uart1_baud);
    bool uart2_switched = switch_sensor_to_target_baud(UART2_PORT, "UART2", &uart2_baud);
    if (!uart1_switched || !uart2_switched) {
        return false;
    }

    ESP_LOGI(TAG, "=== Phase 3: Verify %d communication ===", TOF_TARGET_BAUDRATE);
    bool uart1_ok = probe_sensor_baudrate(UART1_PORT, "UART1", TOF_TARGET_BAUDRATE, TOF_PROBE_ATTEMPTS_PER_BAUD);
    bool uart2_ok = probe_sensor_baudrate(UART2_PORT, "UART2", TOF_TARGET_BAUDRATE, TOF_PROBE_ATTEMPTS_PER_BAUD);
    if (!uart1_ok || !uart2_ok) {
        ESP_LOGE(TAG, "Final baudrate verification failed! uart1=%d uart2=%d", uart1_ok, uart2_ok);
        return false;
    }

    vTaskDelay(pdMS_TO_TICKS(100));

    ESP_LOGI(TAG, "=== Phase 4: Configure sensors ===");
    if (!tof_send_command_with_retry(UART1_PORT, "UART1", TOF_CMD_ANTIMMI, "OK", 1000, TOF_CMD_RETRIES) ||
        !tof_send_command_with_retry(UART2_PORT, "UART2", TOF_CMD_ANTIMMI, "OK", 1000, TOF_CMD_RETRIES)) {
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(100));

    if (!tof_send_command_with_retry(UART1_PORT, "UART1", TOF_CMD_FPS, "OK", 1000, TOF_CMD_RETRIES) ||
        !tof_send_command_with_retry(UART2_PORT, "UART2", TOF_CMD_FPS, "OK", 1000, TOF_CMD_RETRIES)) {
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(100));

    ESP_LOGI(TAG, "Sending AT+DISP=4 to start UART output...");
    if (!tof_send_command_with_retry(UART1_PORT, "UART1", TOF_CMD_DISP_ON, "OK", 1000, TOF_CMD_RETRIES) ||
        !tof_send_command_with_retry(UART2_PORT, "UART2", TOF_CMD_DISP_ON, "OK", 1000, TOF_CMD_RETRIES)) {
        return false;
    }

    uart_clear_input(UART1_PORT);
    uart_clear_input(UART2_PORT);
    vTaskDelay(pdMS_TO_TICKS(200));

    ESP_LOGI(TAG, "MaixSense ToF sensors initialized successfully!");
    return true;
}

static void init_usb_bridge(void) {
    ESP_LOGI(TAG, "Initializing TinyUSB...");
    const tinyusb_config_t tusb_cfg = {
        .port = TINYUSB_PORT_FULL_SPEED_0,
        .phy = {
            .skip_setup = false,
            .self_powered = false,
            .vbus_monitor_io = -1,
        },
        .task = {
            .size = 8192,
            .priority = 6,
            .xCoreID = 0,
        },
        .descriptor = {
            .device = &desc_device,
            .qualifier = NULL,
            .string = string_desc_arr,
            .string_count = string_desc_arr_count,
            .full_speed_config = desc_configuration,
            .high_speed_config = NULL,
        },
        .event_cb = NULL,
        .event_arg = NULL,
    };
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));
    s_usb_mutex = xSemaphoreCreateMutex();
    ESP_ERROR_CHECK(s_usb_mutex ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_LOGI(TAG, "TinyUSB initialized");
}

// ==========================================================
// 主入口 (extern "C" 是必须的，因为 ESP-IDF 启动文件是 C)
// ==========================================================
extern "C" {
    void app_main(void);
}

void app_main(void) {
    // 1. 系统初始化
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_LOGI(TAG, "ESP32-S3 Multi-Sensor Bridge Starting...");
    ESP_LOGI(TAG, "Reset reason=%d", (int)esp_reset_reason());
    load_device_config();
    print_device_config();
    xTaskCreate(config_console_task, "cfg_console", 4096, NULL, 2, NULL);

    // 1.5 先初始化 USB，避免冷启动时 ToF 还没完全上电就开始发 AT 命令
    init_usb_bridge();

    // ================================================================
    // 2. MaixSense ToF 传感器初始化 (自动波特率检测 + 配置)
    // 传感器可能是115200或921600，需要先检测再配置
    // ================================================================
    bool tof_ready = initialize_tof_sensors();
    if (!tof_ready) {
        ESP_LOGW(TAG, "ToF sensors were not ready on first attempt, waiting 1500ms before retry...");
        vTaskDelay(pdMS_TO_TICKS(1500));
        tof_ready = initialize_tof_sensors();
    }
    if (!tof_ready) {
        ESP_LOGE(TAG, "ToF initialization failed after retry; stream task will start but sensors may stay offline");
    }

    // ================================================================
    // 3. TODO(v4): 网络回传初始化
    // 当前版本只有 USB CDC 回传，需要补全 Wi-Fi + MQTT 功能。
    // 协议规范请参考:
    //   docs/protocol.md — "LAN 回传（MQTT 巴法云）" 章节
    //   reference/espidf_protocol_contract.md — "MQTT" 章节
    //   gateway/bed_config.py — topics_for() 函数
    // ================================================================
    // TODO(v4): start the restored network backhaul here.

    // ================================================================
    // 4. 初始化 MLX 管理器 (C++ 对象)
    // ================================================================
    #if 1  // 启用 MLX 初始化
    // 使用 lambda 表达式将日志转发给 ESP_LOGI
    auto log_cb = [](const std::string& msg) {
        ESP_LOGI("MLX_LIB", "%s", msg.c_str());
    };

    MLXManager *mlx_manager = new MLXManager(log_cb);
    
    // 初始化 I2C 和传感器
    if (mlx_manager->initialize()) {
        mlx_manager->start(); // 启动计算线程
        ESP_LOGI(TAG, "MLXManager started successfully");
        
        // 创建任务发送处理好的数据到 CDC 0
        xTaskCreate(mlx_sender_task, "mlx_tx", 4096, mlx_manager, 5, NULL);
    } else {
        ESP_LOGE(TAG, "MLXManager initialization failed!");
    }
    #else
    ESP_LOGW(TAG, "MLX90640 initialization disabled for USB testing");
    #endif

    // 5. 创建 ToF 数据回传任务 (单任务处理 CDC1)
    BaseType_t task_ok = xTaskCreatePinnedToCore(tof_stream_task, "tof_stream", 8192, NULL, 4, NULL, 0);
    ESP_ERROR_CHECK(task_ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);

    ESP_LOGI(TAG, "System Ready (USB CDC only). MQTT uplink not yet implemented.");
}
