from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.repositories.customers import (
    CustomerCreate,
    CustomerDuplicate,
    CustomerRecord,
    CustomerRepository,
)


class CustomerValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CreateCustomerResult:
    customer_id: int


class CustomerService:
    def __init__(self, database_path: Path) -> None:
        self._repository = CustomerRepository(database_path)

    def build_customer(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        notes: str,
        marketing_consent: bool,
    ) -> CustomerCreate:
        customer = CustomerCreate(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=self._optional(phone),
            email=self._optional(email),
            notes=self._optional(notes),
            marketing_consent=marketing_consent,
        )
        self._validate(customer)
        return customer

    def find_possible_duplicates(self, customer: CustomerCreate) -> list[CustomerDuplicate]:
        return self._repository.find_possible_duplicates(customer)

    def create_customer(self, customer: CustomerCreate) -> CreateCustomerResult:
        return CreateCustomerResult(customer_id=self._repository.create(customer))

    def update_customer(self, customer_id: int, customer: CustomerCreate) -> None:
        self._repository.update(customer_id, customer)

    def set_customer_active(self, customer_id: int, is_active: bool) -> None:
        self._repository.set_active(customer_id, is_active)

    def get_customer(self, customer_id: int) -> CustomerRecord | None:
        return self._repository.get(customer_id)

    def search_customers(self, term: str = "") -> list[CustomerRecord]:
        return self._repository.search(term)

    def _validate(self, customer: CustomerCreate) -> None:
        if not customer.first_name:
            raise CustomerValidationError("El nombre es obligatorio.")
        if not customer.last_name:
            raise CustomerValidationError("El apellido es obligatorio.")
        if not customer.phone and not customer.email:
            raise CustomerValidationError("Ingresá al menos un teléfono o un correo.")
        if customer.email and "@" not in customer.email:
            raise CustomerValidationError("El correo no parece válido.")

    @staticmethod
    def _optional(value: str) -> str | None:
        cleaned = value.strip()
        return cleaned or None
