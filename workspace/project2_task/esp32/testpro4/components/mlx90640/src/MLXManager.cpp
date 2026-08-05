// MLXManager.cpp
#include "MLXManager.hpp"
#include <chrono>
#include <cstring> // for memcpy
#include <map>
#include <iostream> // for std::cerr
#include "esp_log.h"

// 构造函数
MLXManager::MLXManager(CppLogCallback log_cb)
    : log_callback(log_cb), is_running(false) {
    // 初始化温度数组为0
    memset(temperatures1, 0, sizeof(temperatures1));
    memset(temperatures2, 0, sizeof(temperatures2));
}

// 析构函数 (自动停止)
MLXManager::~MLXManager() {
    stop();
}

void MLXManager::_log(const std::string& message) {
    if (log_callback) {
        log_callback(message);
    } else {
        // 使用 ESP_LOGI 打印到调试串口 (UART0)
        ESP_LOGI("MLXManager", "%s", message.c_str());
    }
}

// 初始化传感器 (来自 _initialize_sensors)
bool MLXManager::initialize() {
    _log("正在初始化I2C总线...");
    MLX90640_I2CInit(); //

    uint16_t eeMLX90640[832];
    int status;

    // --- 初始化传感器1 (0x33) ---
    _log("正在初始化地址为 0x33 的传感器 (long)...");
    status = MLX90640_SetRefreshRate(MLX_I2C_ADDR_1, FPS_MAP_VALUE); //
    if (status != 0) {
        _log("错误: 无法设置 0x33 传感器的刷新率");
        return false;
    }
    status = MLX90640_SetChessMode(MLX_I2C_ADDR_1); //
    if (status != 0) {
        _log("错误: 无法设置 0x33 传感器的棋盘模式");
        return false;
    }

    status = MLX90640_DumpEE(MLX_I2C_ADDR_1, eeMLX90640); //
    if (status != 0) {
        _log("错误: 无法从 0x33 传感器EEPROM读取数据!");
        return false;
    }

    status = MLX90640_ExtractParameters(eeMLX90640, &this->params1); //
    if (status != 0) {
        _log("错误: 无法从 0x33 传感器提取参数!");
        return false;
    }
    _log("0x33 传感器初始化成功。");

    // --- 初始化传感器2 (0x34) ---
    _log("正在初始化地址为 0x34 的传感器 (wide)...");
    status = MLX90640_SetRefreshRate(MLX_I2C_ADDR_2, FPS_MAP_VALUE); //
    if (status != 0) {
        _log("错误: 无法设置 0x34 传感器的刷新率");
        return false;
    }
    status = MLX90640_SetChessMode(MLX_I2C_ADDR_2); //
    if (status != 0) {
        _log("错误: 无法设置 0x34 传感器的棋盘模式");
        return false;
    }

    status = MLX90640_DumpEE(MLX_I2C_ADDR_2, eeMLX90640); //
    if (status != 0) {
        _log("错误: 无法从 0x34 传感器EEPROM读取数据!");
        return false;
    }

    status = MLX90640_ExtractParameters(eeMLX90640, &this->params2); //
    if (status != 0) {
        _log("错误: 无法从 0x34 传感器提取参数!");
        return false;
    }
    _log("0x34 传感器初始化成功。");
    
    _log("两个MLX90640传感器初始化成功。");
    return true;
}

void MLXManager::start() {
    if (is_running) {
        _log("警告: MLX 管理器已在运行。");
        return;
    }
    _log("启动 MLXManager 后台线程...");
    is_running.store(true);
    update_thread = std::thread(&MLXManager::_update_loop, this);
}

void MLXManager::stop() {
    if (!is_running.load()) {
        return;
    }
    _log("正在停止 MLXManager 后台线程...");
    is_running.store(false);
    if (update_thread.joinable()) {
        update_thread.join();
    }
    _log("MLXManager 后台线程已停止。");
}

// 线程安全的数据获取函数
void MLXManager::get_temperature_data(float* out_temps1, float* out_temps2) {
    // 使用互斥锁保护数据，防止在读取时被 _update_loop 写入
    std::lock_guard<std::mutex> lock(data_mutex);
    memcpy(out_temps1, this->temperatures1, 768 * sizeof(float));
    memcpy(out_temps2, this->temperatures2, 768 * sizeof(float));
}

// 后台线程循环 (来自 _update_loop)
void MLXManager::_update_loop() {
    while (is_running.load()) {
            // 局部缓冲区
            float local_temps1[768];
            float local_temps2[768];
            float ta;
            int status;

            // --- 读取传感器 1 ---
            status = MLX90640_GetFrameData(MLX_I2C_ADDR_1, this->frame1); //
            if (status >= 0) {
                ta = MLX90640_GetTa(this->frame1, &this->params1); //
                MLX90640_CalculateTo(this->frame1, &this->params1, 1.0, ta, local_temps1); //
                MLX90640_BadPixelsCorrection(this->params1.brokenPixels, local_temps1, 1, &this->params1); //
                MLX90640_BadPixelsCorrection(this->params1.outlierPixels, local_temps1, 1, &this->params1); //
            } else {
                _log("警告: 0x33 传感器 GetFrameData 失败");
            }

            // --- 读取传感器 2 ---
            status = MLX90640_GetFrameData(MLX_I2C_ADDR_2, this->frame2); //
            if (status >= 0) {
                ta = MLX90640_GetTa(this->frame2, &this->params2); //
                MLX90640_CalculateTo(this->frame2, &this->params2, 1.0, ta, local_temps2); //
                MLX90640_BadPixelsCorrection(this->params2.brokenPixels, local_temps2, 1, &this->params2); //
                MLX90640_BadPixelsCorrection(this->params2.outlierPixels, local_temps2, 1, &this->params2); //
            } else {
                _log("警告: 0x34 传感器 GetFrameData 失败");
            }

            // --- 线程安全地更新共享数据 ---
            {
                std::lock_guard<std::mutex> lock(data_mutex);
                memcpy(this->temperatures1, local_temps1, 768 * sizeof(float));
                memcpy(this->temperatures2, local_temps2, 768 * sizeof(float));
            }

            // 休眠 (1.0 / FPS)
            std::this_thread::sleep_for(std::chrono::milliseconds(1000 / FPS));

    }
}