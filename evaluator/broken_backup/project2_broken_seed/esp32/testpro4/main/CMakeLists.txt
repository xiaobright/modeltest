idf_component_register(
    SRCS 
        "main.cpp" 
        "usb_descriptors.c"
    INCLUDE_DIRS 
        "."
    REQUIRES 
        mlx90640 
        esp_tinyusb 
        esp_driver_uart
        driver 
        nvs_flash
    # TODO(v4): network backhaul dependencies belong here after implementation.
)

    # Keep existing runtime behavior; only avoid build break from stricter C++ warnings in IDF 6.0.
    target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-error=missing-field-initializers)
