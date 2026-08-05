/* main/tusb_config.h */
#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

//--------------------------------------------------------------------
// COMMON CONFIGURATION
//--------------------------------------------------------------------
#define CFG_TUD_ENABLED         1

// 端点0大小
#ifndef CFG_TUD_ENDPOINT0_SIZE
#define CFG_TUD_ENDPOINT0_SIZE  64
#endif

// 操作系统
#define CFG_TUSB_OS             OPT_OS_FREERTOS

// USB 速度
#define CFG_TUD_MAX_SPEED       OPT_MODE_FULL_SPEED

//--------------------------------------------------------------------
// DEVICE CLASS CONFIGURATION
//--------------------------------------------------------------------

// CDC (虚拟串口) - 使用 menuconfig 的配置
#include "sdkconfig.h"
#if defined(CONFIG_TINYUSB_CDC_COUNT)
#define CFG_TUD_CDC             CONFIG_TINYUSB_CDC_COUNT
#else
#define CFG_TUD_CDC             2
#endif
#if defined(CONFIG_TINYUSB_CDC_RX_BUFSIZE)
#define CFG_TUD_CDC_RX_BUFSIZE  CONFIG_TINYUSB_CDC_RX_BUFSIZE
#else
#define CFG_TUD_CDC_RX_BUFSIZE  256
#endif
#if defined(CONFIG_TINYUSB_CDC_TX_BUFSIZE)
#define CFG_TUD_CDC_TX_BUFSIZE  CONFIG_TINYUSB_CDC_TX_BUFSIZE
#else
#define CFG_TUD_CDC_TX_BUFSIZE  256
#endif
#if defined(CONFIG_TINYUSB_CDC_EP_BUFSIZE)
#define CFG_TUD_CDC_EP_BUFSIZE  CONFIG_TINYUSB_CDC_EP_BUFSIZE
#else
#define CFG_TUD_CDC_EP_BUFSIZE  64
#endif

// 禁用其他设备类
#define CFG_TUD_MSC             0
#define CFG_TUD_HID             0
#define CFG_TUD_MIDI            0
#define CFG_TUD_VENDOR          0

#ifdef __cplusplus
}
#endif

#endif /* _TUSB_CONFIG_H_ */
