# ESP-IDF Example Documentation

This is an example documentation file for testing the MCP server.

## WiFi Examples

The ESP-IDF provides several WiFi examples:

- WiFi Station mode
- WiFi Access Point mode  
- WiFi Scan example

## GPIO Examples

Basic GPIO operations:

```c
gpio_set_direction(GPIO_NUM_2, GPIO_MODE_OUTPUT);
gpio_set_level(GPIO_NUM_2, 1);
```

## API Reference

For detailed API reference, see:
- `esp_wifi.h` - WiFi APIs
- `driver/gpio.h` - GPIO driver APIs