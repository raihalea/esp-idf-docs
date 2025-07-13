WiFi API
========

The WiFi API provides functions for WiFi connectivity.

.. doxygenfunction:: esp_wifi_init
.. doxygenfunction:: esp_wifi_start
.. doxygenfunction:: esp_wifi_stop

Configuration
-------------

WiFi configuration example::

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "MySSID",
            .password = "MyPassword"
        }
    };

API Functions
-------------

.. doxygenstruct:: esp_wifi_config_t
    :members: