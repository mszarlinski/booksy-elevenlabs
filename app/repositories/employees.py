from __future__ import annotations


class InMemoryEmployeeRepository:
    def __init__(self) -> None:
        self._employees: list[dict[str, str | list[str]]] = [
            {
                "id": "emp-alice",
                "name": "Alice",
                "business_id": "biz-glow-salon",
                "service_ids": ["svc-haircut", "svc-shave"],
            },
            {
                "id": "emp-carol",
                "name": "Carol",
                "business_id": "biz-glow-salon",
                "service_ids": ["svc-manicure"],
            },
            {
                "id": "emp-dave",
                "name": "Dave",
                "business_id": "biz-glow-salon",
                "service_ids": ["svc-manicure"],
            },
            {
                "id": "emp-bob",
                "name": "Bob",
                "business_id": "biz-downtown-barber",
                "service_ids": ["svc-haircut", "svc-manicure"],
            },
            {
                "id": "emp-erin",
                "name": "Erin",
                "business_id": "biz-downtown-barber",
                "service_ids": ["svc-shave"],
            },
            {
                "id": "emp-frank",
                "name": "Frank",
                "business_id": "biz-downtown-barber",
                "service_ids": ["svc-shave"],
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
