/* main/usb_descriptors.c */
#include "tusb.h"
#include "sdkconfig.h"
#include <string.h>

// 定义两个 CDC 端口的接口编号
enum {
    ITF_NUM_CDC_0 = 0, ITF_NUM_CDC_0_DATA, // ToF 1
    ITF_NUM_CDC_1,     ITF_NUM_CDC_1_DATA, // ToF 2
    ITF_NUM_TOTAL
};

// 描述符长度 - 必须在使用前定义
#define TUSB_DESC_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN * 2)

// 设备描述符
tusb_desc_device_t const desc_device = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,
    .bDeviceClass       = TUSB_CLASS_MISC,
    .bDeviceSubClass    = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol    = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor           = 0x303A, // Espressif VID
    .idProduct          = 0x4001, // 自定义 PID
    .bcdDevice          = 0x0100,
    .iManufacturer      = 0x01,
    .iProduct           = 0x02,
    .iSerialNumber      = 0x03,
    .bNumConfigurations = 0x01
};

// 配置描述符 (包含2个CDC接口)
uint8_t const desc_configuration[] = {
    // Config number, interface count, string index, total length, attribute, power in mA
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, TUSB_DESC_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),

    // CDC 0 (EP 0x81/0x02) - MLX90640 Stream
    // Interface number, string index, EP notification address and size, EP data address (out, in) and size.
    TUD_CDC_DESCRIPTOR(ITF_NUM_CDC_0, 4, 0x81, 8, 0x02, 0x82, 64),

    // CDC 1 (EP 0x83/0x04) - ToF Shared
    TUD_CDC_DESCRIPTOR(ITF_NUM_CDC_1, 5, 0x83, 8, 0x04, 0x84, 64),
};

// 字符串描述符 (厂商, 产品, 序列号, 接口名...)
char const* string_desc_arr[] = {
    (const char[]) { 0x09, 0x04 }, // 0: is supported language is English (0x0409)
    "Melexis & Espressif",         // 1: Manufacturer
    "Super Sensor Hub",            // 2: Product
    "123456",                      // 3: Serials
    "MLX90640 Stream",             // 4: CDC 0 Name
    "ToF Shared",                  // 5: CDC 1 Name
};
const int string_desc_arr_count = sizeof(string_desc_arr) / sizeof(string_desc_arr[0]);
