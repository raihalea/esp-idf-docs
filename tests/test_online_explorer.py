"""Tests for online ESP-IDF documentation explorer."""

import httpx
import pytest
import respx

from esp_idf_docs_mcp.config import ServerConfig
from esp_idf_docs_mcp.explorer import ESPIDFDocsExplorer
from esp_idf_docs_mcp.web_explorer import OnlineESPIDFExplorer


@pytest.fixture
def server_config():
    """Test server configuration."""
    return ServerConfig(
        base_url="https://docs.espressif.com/projects/esp-idf",
        esp_idf_version="latest",
        max_results=10,
        max_query_length=100,
    )


@pytest.fixture
def mock_html_content():
    """Mock HTML content for testing."""
    return """
    <html>
    <head><title>ESP-IDF Documentation</title></head>
    <body>
        <div class="document">
            <h1>WiFi API Guide</h1>
            <p>This guide describes the WiFi API for ESP32.</p>
            <a href="wifi/index.html">WiFi Configuration</a>
            <a href="bluetooth/index.html">Bluetooth Setup</a>
            <h2>Getting Started</h2>
            <p>To use WiFi on ESP32, you need to configure the network settings.</p>
            <nav>
                <a href="api-reference/wifi/">WiFi API Reference</a>
                <a href="api-reference/bluetooth/">Bluetooth API Reference</a>
            </nav>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_api_html():
    """Mock API reference HTML."""
    return """
    <html>
    <body>
        <div class="document">
            <h1>WiFi API Reference</h1>
            <h2>esp_wifi_init</h2>
            <p>Initialize WiFi subsystem.</p>
            <h2>esp_wifi_connect</h2>
            <p>Connect to WiFi network.</p>
        </div>
    </body>
    </html>
    """


class TestOnlineESPIDFExplorer:
    """Test OnlineESPIDFExplorer class."""

    @pytest.mark.asyncio
    async def test_init(self, server_config):
        """Test explorer initialization."""
        explorer = OnlineESPIDFExplorer(server_config)

        assert explorer.config == server_config
        assert explorer.base_url == "https://docs.espressif.com/projects/esp-idf"
        assert explorer.version == "latest"
        assert explorer.docs_url == "https://docs.espressif.com/projects/esp-idf/en/latest/esp32"

        await explorer.close()

    @pytest.mark.asyncio
    async def test_versioned_url(self):
        """Test versioned URL construction."""
        config = ServerConfig(esp_idf_version="v5.1")
        explorer = OnlineESPIDFExplorer(config)

        assert explorer.docs_url == "https://docs.espressif.com/projects/esp-idf/en/v5.1/esp32"

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_docs_basic(self, server_config, mock_html_content):
        """Test basic document search functionality."""
        # Mock HTTP responses
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32/hw-reference/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32/security/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/wifi/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/bluetooth/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/protocols/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))
        respx.get(
            "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/"
        ).mock(return_value=httpx.Response(200, text=mock_html_content))

        explorer = OnlineESPIDFExplorer(server_config)

        result = await explorer.search_docs("wifi", limit=5)

        assert result["query"] == "wifi"
        assert "results" in result
        assert "metadata" in result
        assert result["metadata"]["source"] == "esp-idf-online"
        assert result["metadata"]["version"] == "latest"

        # Should find WiFi-related content
        results = result["results"]
        assert len(results) > 0

        # Check that results contain relevant information
        wifi_found = any("wifi" in r.get("title", "").lower() for r in results)
        assert wifi_found

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_empty_query(self, server_config):
        """Test search with empty query."""
        explorer = OnlineESPIDFExplorer(server_config)

        with pytest.raises(Exception):  # Should raise validation error
            await explorer.search_docs("")

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_read_doc(self, server_config, mock_api_html):
        """Test reading a specific document."""
        doc_url = "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/wifi/"

        respx.get(doc_url).mock(return_value=httpx.Response(200, text=mock_api_html))

        explorer = OnlineESPIDFExplorer(server_config)

        result = await explorer.read_doc(doc_url)

        assert result is not None
        assert result["url"] == doc_url
        assert "WiFi API Reference" in result["title"]
        assert "content" in result
        assert "esp_wifi_init" in result["content"]

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_read_doc_relative_url(self, server_config, mock_api_html):
        """Test reading document with relative URL."""
        relative_url = "api-reference/wifi/"
        full_url = "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/wifi/"

        respx.get(full_url).mock(return_value=httpx.Response(200, text=mock_api_html))

        explorer = OnlineESPIDFExplorer(server_config)

        result = await explorer.read_doc(relative_url)

        assert result is not None
        assert result["url"] == full_url

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_doc_structure(self, server_config, mock_html_content):
        """Test getting documentation structure."""
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )

        explorer = OnlineESPIDFExplorer(server_config)

        result = await explorer.get_doc_structure()

        assert "sections" in result
        assert "metadata" in result
        assert result["metadata"]["version"] == "latest"
        assert (
            result["metadata"]["base_url"]
            == "https://docs.espressif.com/projects/esp-idf/en/latest/esp32"
        )

        # Should find some sections
        sections = result["sections"]
        assert len(sections) > 0

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_find_api_references(self, server_config, mock_api_html):
        """Test finding API references."""
        api_url = "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/"

        respx.get(api_url).mock(return_value=httpx.Response(200, text=mock_api_html))

        explorer = OnlineESPIDFExplorer(server_config)

        result = await explorer.find_api_references("wifi")

        assert result["component"] == "wifi"
        assert "results" in result
        assert "metadata" in result

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_handling(self, server_config):
        """Test HTTP error handling."""
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32/nonexistent").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        explorer = OnlineESPIDFExplorer(server_config)

        # read_doc returns None instead of raising exception on error
        result = await explorer.read_doc("nonexistent")
        assert result is None

        await explorer.close()

    @pytest.mark.asyncio
    async def test_caching(self, server_config):
        """Test page caching functionality."""
        explorer = OnlineESPIDFExplorer(server_config)

        # Manually add to cache
        test_url = "https://example.com/test"
        test_content = "<html>Test</html>"
        explorer._page_cache[test_url] = (test_content, 9999999999)  # Far future

        # Mock the fetch to ensure cache is used
        with respx.mock:
            respx.get(test_url).mock(return_value=httpx.Response(200, text="Should not be called"))

            content = await explorer._fetch_page(test_url)
            assert content == test_content

        await explorer.close()


class TestESPIDFDocsExplorer:
    """Test the main ESPIDFDocsExplorer wrapper class."""

    @pytest.mark.asyncio
    async def test_init(self, server_config):
        """Test explorer wrapper initialization."""
        explorer = ESPIDFDocsExplorer(server_config)

        assert explorer.config == server_config
        assert isinstance(explorer.online_explorer, OnlineESPIDFExplorer)

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_docs_wrapper(self, server_config, mock_html_content):
        """Test search docs through wrapper."""
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )

        explorer = ESPIDFDocsExplorer(server_config)

        result = await explorer.search_docs("bluetooth")

        assert result["query"] == "bluetooth"
        assert "results" in result

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_doc_structure_wrapper(self, server_config, mock_html_content):
        """Test get doc structure through wrapper."""
        respx.get("https://docs.espressif.com/projects/esp-idf/en/latest/esp32").mock(
            return_value=httpx.Response(200, text=mock_html_content)
        )

        explorer = ESPIDFDocsExplorer(server_config)

        result = await explorer.get_doc_structure()

        assert "sections" in result
        assert "metadata" in result

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_read_doc_wrapper(self, server_config, mock_api_html):
        """Test read doc through wrapper."""
        doc_url = "api-reference/wifi/"
        full_url = "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/wifi/"

        respx.get(full_url).mock(return_value=httpx.Response(200, text=mock_api_html))

        explorer = ESPIDFDocsExplorer(server_config)

        result = await explorer.read_doc(doc_url)

        assert result is not None
        assert result["url"] == full_url

        await explorer.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_find_api_references_wrapper(self, server_config, mock_api_html):
        """Test find API references through wrapper."""
        api_url = "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/"

        respx.get(api_url).mock(return_value=httpx.Response(200, text=mock_api_html))

        explorer = ESPIDFDocsExplorer(server_config)

        result = await explorer.find_api_references("esp32")

        assert result["component"] == "esp32"
        assert "results" in result

        await explorer.close()


class TestConfiguration:
    """Test configuration for online mode."""

    def test_server_config_defaults(self):
        """Test default server configuration."""
        config = ServerConfig()

        assert config.base_url == "https://docs.espressif.com/projects/esp-idf"
        assert config.esp_idf_version == "latest"
        assert config.max_results == 20
        assert config.request_timeout == 30.0

    def test_server_config_from_environment(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("ESP_IDF_VERSION", "v5.1")
        monkeypatch.setenv("ESP_IDF_BASE_URL", "https://custom.docs.com")
        monkeypatch.setenv("ESP_IDF_MAX_RESULTS", "50")

        config = ServerConfig.from_environment()

        assert config.esp_idf_version == "v5.1"
        assert config.base_url == "https://custom.docs.com"
        assert config.max_results == 50
