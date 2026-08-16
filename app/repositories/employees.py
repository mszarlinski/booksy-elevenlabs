class InMemoryEmployeeRepository:
    def __init__(self) -> None:
        self._employees: list[dict[str, str | list[str]]] = [
            {
                "id": "emp-alice",
                "name": "Alice",
                "service_ids": ["svc-haircut", "svc-shave"],
            },
            {
                "id": "emp-bob",
                "name": "Bob",
                "service_ids": ["svc-haircut", "svc-manicure"],
            },
        ]

    def search(self, service_id: str | None = None) -> list[dict[str, str | list[str]]]:
        if service_id is None:
            return self._employees
        return [
            employee for employee in self._employees if service_id in employee["service_ids"]
        ]

    def list(self) -> list[dict[str, str | list[str]]]:
        return self._employees

    def get(self, employee_id: str) -> dict[str, str | list[str]]:
        for employee in self._employees:
            if employee["id"] == employee_id:
                return employee
        raise KeyError(employee_id)


_repository = InMemoryEmployeeRepository()


def get_employee_repository() -> InMemoryEmployeeRepository:
    return _repository
