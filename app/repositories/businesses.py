class InMemoryBusinessRepository:
    def __init__(self) -> None:
        self._businesses: list[dict[str, str]] = []

    def list(self) -> list[dict[str, str]]:
        return self._businesses

    def add(self, business: dict[str, str]) -> None:
        self._businesses.append(business)


_repository = InMemoryBusinessRepository()


def get_business_repository() -> InMemoryBusinessRepository:
    return _repository
