// mlx_manager_api.cpp
#include "mlx_manager_api.h"
#include "MLXManager.hpp"
#include <iostream>

// C/C++ 胶水层
extern "C" {

mlx_manager_t mlx_manager_create(mlx_log_cb log_cb) {
    // 创建一个 C++ lambda 来包装C回调
    CppLogCallback cpp_log_cb = [log_cb](const std::string& msg) {
        if (log_cb) {
            log_cb(msg.c_str());
        }
    };
    
    // new 一个 C++ 对象并返回句柄
    return new (std::nothrow) MLXManager(cpp_log_cb);
}

void mlx_manager_destroy(mlx_manager_t handle) {
    delete static_cast<MLXManager*>(handle);
}

int mlx_manager_initialize(mlx_manager_t handle) {
    if (!handle) return -1;
    bool success = static_cast<MLXManager*>(handle)->initialize();
    return success ? 0 : -1;
}

void mlx_manager_start(mlx_manager_t handle) {
    if (handle) {
        static_cast<MLXManager*>(handle)->start();
    }
}

void mlx_manager_stop(mlx_manager_t handle) {
    if (handle) {
        static_cast<MLXManager*>(handle)->stop();
    }
}

int mlx_manager_get_temperatures(mlx_manager_t handle, float* out_temps1, float* out_temps2) {
    if (!handle || !out_temps1 || !out_temps2) {
        return -1;
    }
    static_cast<MLXManager*>(handle)->get_temperature_data(out_temps1, out_temps2);
    return 0;
}

} // extern "C"