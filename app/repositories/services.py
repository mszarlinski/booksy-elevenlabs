class InMemoryServiceRepository:
    def __init__(self) -> None:
        self._services: list[dict[str, str | int | float]] = [
            {
                "id": "svc-haircut",
                "name": "Men's Haircut",
                "duration_minutes": 30,
                "price": 40.0,
            },
            {
                "id": "svc-shave",
                "name": "Shave",
                "duration_minutes": 20,
                "price": 25.0,
            },
            {
                "id": "svc-manicure",
                "name": "Manicure",
                "duration_minutes": 45,
                "price": 35.0,
            },
        ]

    def search(self, name: str | None = None) -> list[dict[str, str | int | float]]:
        if name is None:
            return self._services
        needle = name.lower()
        return [service for service in self._services if needle in service["name"].lower()]

    def get(self, service_id: str) -> dict[str, str | int | float]:
        for service in self._services:
            if service["id"] == service_id:
                return service
        raise KeyError(service_id)


_repository = InMemoryServiceRepository()


def get_service_repository() -> InMemoryServiceRepository:
    return _repository
