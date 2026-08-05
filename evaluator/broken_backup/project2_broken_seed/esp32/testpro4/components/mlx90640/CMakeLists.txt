idf_component_register(
    SRCS 
        "src/MLXManager.cpp"
        "src/mlx_manager_api.cpp"
        "src/MLX90640_API.cpp"
        "src/MLX90640_ESP32_Driver.c"
    INCLUDE_DIRS 
        "include"
    REQUIRES 
        driver
)

# Keep upstream MLX90640 logic untouched; only relax this warning in this component.
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-error=type-limits)
