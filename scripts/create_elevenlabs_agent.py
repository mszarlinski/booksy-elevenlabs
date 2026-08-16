import os

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

TOOL_DEFINITIONS = [
    {
        "name": "search_services",
        "description": (
            "Search for bookable services by name, e.g. 'haircut'. Use this to find "
            "the service_id needed by search_employees and search_available_slots."
        ),
        "path": "/services",
        "query_params": {
            "name": {
                "type": "string",
                "description": "Free-text search term matched against service names.",
            },
        },
        "required_query_params": [],
    },
    {
        "name": "search_employees",
        "description": (
            "Search for employees who can perform a given service. Provide the "
            "service_id returned by search_services."
        ),
        "path": "/employees",
        "query_params": {
            "service_id": {
                "type": "string",
                "description": "The id of the service the employee must be able to perform.",
            },
        },
        "required_query_params": [],
    },
    {
        "name": "search_available_slots",
        "description": (
            "Find available appointment slots for a service on a given date, "
            "optionally narrowed by time range or a specific employee."
        ),
        "path": "/availability",
        "query_params": {
            "service_id": {
                "type": "string",
                "description": "The id of the service to book, from search_services.",
            },
            "date": {
                "type": "string",
                "description": "The date to search, formatted YYYY-MM-DD.",
            },
            "earliest_time": {
                "type": "string",
                "description": "Optional earliest allowed start time, formatted HH:MM.",
            },
            "latest_time": {
                "type": "string",
                "description": "Optional latest allowed start time, formatted HH:MM.",
            },
            "employee_id": {
                "type": "string",
                "description": "Optional id of a specific employee, from search_employees.",
            },
        },
        "required_query_params": ["service_id", "date"],
    },
    {
        "name": "get_booking",
        "description": "Look up a single existing booking by its id.",
        "path": "/bookings/{booking_id}",
        "path_params": {
            "booking_id": {
                "type": "string",
                "description": "The id of the booking to look up.",
            },
        },
    },
    {
        "name": "get_customer_bookings",
        "description": "List existing bookings for a customer by name.",
        "path": "/bookings",
        "query_params": {
            "customer_name": {
                "type": "string",
                "description": "The customer's name to search bookings for.",
            },
        },
        "required_query_params": [],
    },
    {
        "name": "create_booking",
        "description": (
            "Create a real, permanent booking. Only call this AFTER reading the full "
            "booking details (service, employee if one was chosen, and the exact date "
            "and time) back to the customer and receiving explicit confirmation, such "
            "as them saying 'yes' or 'book it'. Never call this speculatively or while "
            "still exploring options with the customer."
        ),
        "method": "POST",
        "path": "/bookings",
        "body_params": {
            "customer_name": {
                "type": "string",
                "description": "The customer's name.",
            },
            "service": {
                "type": "string",
                "description": "The name of the service being booked, e.g. 'Men's Haircut'.",
            },
            "slot": {
                "type": "string",
                "description": "The exact appointment start time, formatted YYYY-MM-DDTHH:MM.",
            },
            "employee_id": {
                "type": "string",
                "description": "Optional id of the employee performing the service.",
            },
            "confirmed": {
                "type": "boolean",
                "description": (
                    "Must be true. Set this only after the customer has explicitly "
                    "confirmed the booking details out loud; the backend rejects the "
                    "request otherwise."
                ),
            },
        },
        "required_body_params": ["customer_name", "service", "slot", "confirmed"],
    },
]

SYSTEM_PROMPT = (
    "You are a booking assistant for a salon. Use search_services to find a "
    "service_id matching what the customer wants. Use search_employees if the "
    "customer asks for a specific staff member. Use search_available_slots to "
    "find open appointment times before suggesting one. Use get_booking or "
    "get_customer_bookings to answer questions about existing bookings. Do not "
    "invent services, employees, or slots that were not returned by a tool. "
    "Before booking, always read back the full details -- service, employee if "
    "one was chosen, and the exact date and time -- and ask the customer to "
    "confirm. Only call create_booking, with confirmed set to true, after the "
    "customer has clearly said yes; if they hesitate, decline, or give an "
    "ambiguous answer, do not call create_booking."
)


def build_tool_configs(base_url: str) -> list[dict]:
    configs = []
    for tool in TOOL_DEFINITIONS:
        api_schema = {
            "url": f"{base_url}{tool['path']}",
            "method": tool.get("method", "GET"),
        }
        if "path_params" in tool:
            api_schema["path_params_schema"] = tool["path_params"]
        if "query_params" in tool:
            api_schema["query_params_schema"] = {
                "properties": tool["query_params"],
                "required": tool.get("required_query_params", []),
            }
        if "body_params" in tool:
            api_schema["request_body_schema"] = {
                "type": "object",
                "properties": tool["body_params"],
                "required": tool.get("required_body_params", []),
            }

        configs.append(
            {
                "type": "webhook",
                "name": tool["name"],
                "description": tool["description"],
                "api_schema": api_schema,
            }
        )
    return configs


def main() -> None:
    load_dotenv()
    api_key = os.environ["ELEVENLABS_API_KEY"]
    # No localhost default: ElevenLabs' hosted webhook tools call this URL over
    # the public internet, so a silently-applied localhost fallback would look
    # like it worked here and then fail to reach the backend during a real call.
    base_url = os.environ["API_BASE_URL"]

    client = ElevenLabs(api_key=api_key)

    tool_ids = []
    for config in build_tool_configs(base_url):
        tool = client.conversational_ai.tools.create(request={"tool_config": config})
        tool_ids.append(tool.id)

    agent = client.conversational_ai.agents.create(
        conversation_config={
            "agent": {
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "tool_ids": tool_ids,
                }
            }
        }
    )
    print(f"Created agent: {agent.agent_id}")


if __name__ == "__main__":
    main()
