// MLXManager.hpp
#ifndef MLXMANAGER_H
#define MLXMANAGER_H

#include <functional>
#include <string>
#include <thread>
#include <atomic>
#include <mutex>
#include <vector>

// 包含你提供的原始 MLX 库的头文件
#include "MLX90640_API.h" //
#include "MLX90640_I2C_Driver.h" //

// C++ 内部的日志回调
using CppLogCallback = std::function<void(const std::string&)>;

// C++ 版本的 MLX90640Manager 类
class MLXManager {
public:
    MLXManager(CppLogCallback log_cb);
    ~MLXManager();

    // 公共控制函数
    bool initialize();
    void start();
    void stop();

    // 线程安全的数据获取
    void get_temperature_data(float* out_temps1, float* out_temps2);

private:
    // 内部函数
    void _log(const std::string& message);
    void _update_loop(); //
    
    // 传感器参数 (来自 MLX90640_API.h)
    paramsMLX90640 params1;
    paramsMLX90640 params2;

    // 原始帧数据
    uint16_t frame1[834];
    uint16_t frame2[834];
    
    // 计算出的温度数据 (768个像素)
    float temperatures1[768];
    float temperatures2[768];

    // 线程和状态 - 注意：顺序必须与构造函数初始化列表一致
    CppLogCallback log_callback;  // 先声明 log_callback
    std::atomic<bool> is_running; // 再声明 is_running
    std::thread update_thread;
    std::mutex data_mutex; // *重要*: 确保线程安全

    // 常量 (来自 datacollect.py)
    static const uint8_t MLX_I2C_ADDR_1 = 0x33;
    static const uint8_t MLX_I2C_ADDR_2 = 0x34;
    static const int FPS = 2;
    static const uint8_t FPS_MAP_VALUE = 0b100; // 对应 4Hz
};

#endif // MLXMANAGER_H
