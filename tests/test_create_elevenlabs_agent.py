from scripts.create_elevenlabs_agent import build_tool_configs

BASE_URL = "http://localhost:8000"


def test_builds_one_config_per_tool():
    configs = build_tool_configs(BASE_URL)

    names = [config["name"] for config in configs]
    assert names == [
        "search_services",
        "search_employees",
        "search_available_slots",
        "get_booking",
        "get_customer_bookings",
    ]


def test_each_config_is_a_webhook_pointing_at_the_base_url():
    configs = build_tool_configs(BASE_URL)

    for config in configs:
        assert config["type"] == "webhook"
        assert config["api_schema"]["url"].startswith(BASE_URL)
        assert config["api_schema"]["method"] == "GET"


def test_search_available_slots_config_has_expected_query_params():
    configs = build_tool_configs(BASE_URL)
    slots_config = next(c for c in configs if c["name"] == "search_available_slots")

    assert slots_config["api_schema"]["url"] == f"{BASE_URL}/availability"
    query_params = slots_config["api_schema"]["query_params_schema"]
    assert set(query_params) == {
        "service_id",
        "date",
        "earliest_time",
        "latest_time",
        "employee_id",
    }


def test_get_booking_config_uses_a_path_param():
    configs = build_tool_configs(BASE_URL)
    get_booking_config = next(c for c in configs if c["name"] == "get_booking")

    assert get_booking_config["api_schema"]["url"] == f"{BASE_URL}/bookings/{{booking_id}}"
    assert "booking_id" in get_booking_config["api_schema"]["path_params_schema"]
