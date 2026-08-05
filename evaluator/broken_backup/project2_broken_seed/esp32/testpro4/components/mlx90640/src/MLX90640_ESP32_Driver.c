#include "MLX90640_I2C_Driver.h"
#include "driver/i2c.h"
#include "esp_log.h"
#include <string.h>

// 定义 I2C 硬件参数
#define I2C_MASTER_NUM  I2C_NUM_0
#define I2C_SDA_PIN     1   // 请根据实际接线修改
#define I2C_SCL_PIN     2   // 请根据实际接线修改
#define I2C_FREQ_HZ     400000 // 降低到 400kHz 更稳定

static const char *TAG = "MLX_I2C";

void MLX90640_I2CInit(void) {
    // 可以在这里初始化 I2C，也可以在 main 中统一初始化
    // 为了防止 MLXManager 多次调用报错，这里可以加个静态标志
    static int initialized = 0;
    if (initialized) return;

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA_PIN,
        .scl_io_num = I2C_SCL_PIN,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master = {
            .clk_speed = I2C_FREQ_HZ,
        },
        .clk_flags = 0,  // 添加缺失的初始化
    };
    
    esp_err_t ret = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C param config failed: %s", esp_err_to_name(ret));
        return;
    }
    
    ret = i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C driver install failed: %s", esp_err_to_name(ret));
        return;
    }
    
    ESP_LOGI(TAG, "I2C initialized successfully");
    initialized = 1;
}

int MLX90640_I2CRead(uint8_t slaveAddr, uint16_t startAddress, uint16_t nMemAddressRead, uint16_t *data) {
    // ESP32 I2C 读写实现
    uint8_t cmd[2] = { (startAddress >> 8) & 0xFF, startAddress & 0xFF };
    esp_err_t ret = i2c_master_write_read_device(I2C_MASTER_NUM, slaveAddr, 
                                                 cmd, 2, 
                                                 (uint8_t*)data, nMemAddressRead * 2, 
                                                 100 / portTICK_PERIOD_MS);
    
    if (ret != ESP_OK) return -1;

    // 大小端转换：MLX 发送的是 Big-Endian，ESP32 是 Little-Endian
    // 但 i2c_master_write_read_device 读到 buffer 里是按字节序的
    // data 是 uint16_t 指针，直接读入会导致字节序反转问题，我们需要手动交换
    uint8_t *p = (uint8_t*)data;
    for (int i = 0; i < nMemAddressRead; i++) {
        uint8_t msb = p[i*2];
        uint8_t lsb = p[i*2+1];
        data[i] = (msb << 8) | lsb;
    }
    return 0;
}

int MLX90640_I2CWrite(uint8_t slaveAddr, uint16_t writeAddress, uint16_t data) {
    uint8_t cmd[4];
    cmd[0] = (writeAddress >> 8) & 0xFF;
    cmd[1] = writeAddress & 0xFF;
    cmd[2] = (data >> 8) & 0xFF;
    cmd[3] = data & 0xFF;

    esp_err_t ret = i2c_master_write_to_device(I2C_MASTER_NUM, slaveAddr, cmd, 4, 100 / portTICK_PERIOD_MS);
    return (ret == ESP_OK) ? 0 : -1;
}

int MLX90640_I2CGeneralReset(void) {
    // I2C 通用复位命令 (0x00, 0x06)
    uint8_t cmd[2] = {0x00, 0x06};
    i2c_master_write_to_device(I2C_MASTER_NUM, 0x00, cmd, 2, 100 / portTICK_PERIOD_MS);
    return 0;
}

void MLX90640_I2CFreqSet(int freq) {
    // 运行时修改频率（可选）
}