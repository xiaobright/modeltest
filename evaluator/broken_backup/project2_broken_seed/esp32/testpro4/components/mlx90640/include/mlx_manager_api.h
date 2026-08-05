// mlx_manager_api.h
#ifndef MLX_MANAGER_API_H
#define MLX_MANAGER_API_H

#include <stdint.h> // 用于 uint8_t

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Opaque handle to the MLX90640 Manager instance.
 * 一个指向 MLX90640 管理器实例的不透明句柄。
 */
typedef void* mlx_manager_t;

/**
 * @brief Log callback function pointer type.
 * 日志回调函数指针类型。
 * @param message The log message (UTF-8 encoded string).
 */
typedef void (*mlx_log_cb)(const char* message);

// 从 datacollect.py 中获取的常量
#define MLX_SENSOR_W 24
#define MLX_SENSOR_H 32
#define MLX_NUM_PIXELS (MLX_SENSOR_W * MLX_SENSOR_H) // 768

/**
 * @brief Creates a new MLX Manager instance.
 * 创建一个新的 MLX 管理器实例。
 * @param log_cb A callback function for logging. Can be NULL.
 * @return A handle to the manager, or NULL on failure.
 */
mlx_manager_t mlx_manager_create(mlx_log_cb log_cb);

/**
 * @brief Destroys an MLX Manager instance and frees resources.
 * 销毁一个 MLX 管理器实例并释放所有资源。
 * @param handle The manager handle.
 */
void mlx_manager_destroy(mlx_manager_t handle);

/**
 * @brief Initializes both MLX90640 sensors (0x33 and 0x34).
 * This function calls MLX90640_I2CInit, dumps EEPROM, and extracts parameters.
 * * 初始化两个 MLX90640 传感器（0x33 和 0x34）。
 * 本函数将调用 MLX90640_I2CInit、转储EEPROM并提取参数。
 * * @param handle The manager handle.
 * @return 0 on success, -1 on failure.
 */
int mlx_manager_initialize(mlx_manager_t handle);

/**
 * @brief Starts the background thread to continuously read sensor data.
 * 启动后台线程以连续读取传感器数据。
 * * @param handle The manager handle.
 */
void mlx_manager_start(mlx_manager_t handle);

/**
 * @brief Stops the background reading thread.
 * 停止后台读取线程。
 * * @param handle The manager handle.
 */
void mlx_manager_stop(mlx_manager_t handle);

/**
 * @brief Gets the latest temperature data from both sensors.
 * This function is thread-safe and copies the most recent data into the provided buffers.
 * Each buffer (out_temps1, out_temps2) must be at least MLX_NUM_PIXELS (768) elements long.
 * * 从两个传感器获取最新的温度数据。
 * 本函数是线程安全的，会将最新数据复制到你提供的缓冲区中。
 * 每个缓冲区（out_temps1, out_temps2）必须至少为 MLX_NUM_PIXELS (768) 个浮点数长。
 * * @param handle The manager handle.
 * @param out_temps1 Pointer to a float array to store data from sensor 1 (0x33).
 * @param out_temps2 Pointer to a float array to store data from sensor 2 (0x34).
 * @return 0 on success, -1 if inputs are invalid.
 */
int mlx_manager_get_temperatures(mlx_manager_t handle, float* out_temps1, float* out_temps2);

#ifdef __cplusplus
}
#endif

#endif // MLX_MANAGER_API_H