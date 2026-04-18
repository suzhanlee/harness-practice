# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**kiosk** is a Domain-Driven Design (DDD) implementation of a self-service kiosk ordering system. It demonstrates layered architecture with clear separation of concerns: domain models (entities, aggregates, value objects), application services (use cases), and infrastructure (in-memory repositories).

The system supports menu browsing, shopping cart operations, order confirmation, and payment processing.

---

## Quick Start

### Prerequisites

- Python 3.8+
- pytest (for testing)

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_order.py

# Single test
pytest tests/test_order.py::test_order_creation

# With coverage
pytest --cov=kiosk tests/
```

### Running the Kiosk CLI

```bash
cd kiosk
python cli.py
```

Interactive menu:
1. Add item to cart
2. Update quantity
3. Remove item
4. View cart
5. Checkout (confirm order)
6. Process payment
7. Exit

---

## DDD Architecture: Layered Design

### Layer Responsibilities

**domain/** — Business logic, unchanged by infrastructure choices
- `models/` — Entities (MenuItem, Order, Payment) and aggregate roots (Order)
- `value_objects.py` — Immutable concepts (Money, Quantity, IDs)
- `services/` — Domain services for cross-aggregate operations
- `repositories/` — Abstract interfaces, implementation-agnostic

**application/** — Workflows, orchestrating domain models
- `use_cases/` — One business operation per use case
- Dependency injection via constructor
- Return DTOs, never expose domain models

**infrastructure/** — Technical implementation
- `repositories/` — Concrete implementations (currently in-memory)
- `seed_data.py` — Initial data setup

---

## Domain Model: Order State Machine

**Three States** (`OrderStatus` enum in `kiosk/domain/models/order.py`):

| State | Description | Allowed Operations |
|---|---|---|
| **PENDING** | Cart phase: items being selected | `add_item()`, `remove_item()`, `update_item_quantity()` |
| **CONFIRMED** | Order finalized: ready for payment | None (read-only) |
| **PAID** | Payment complete | None (read-only) |
| **CANCELLED** | Order cancelled (from PENDING or CONFIRMED only) | None (read-only) |

**State Transitions** (enforced by guards):

```python
# PENDING → CONFIRMED (must have items)
order.confirm()

# CONFIRMED → PAID
order.mark_paid()

# PENDING or CONFIRMED → CANCELLED (not from PAID)
order.cancel()
```

**Key Insight**: Cart functionality is not a separate entity. A PENDING Order *is* the cart. This design minimizes duplication and simplifies state management. See `.dev/adr/2026-04-18-order-and-shopping-cart-inclusion.md` for the architectural rationale.

---

## Value Objects: Immutable Concepts

All frozen dataclasses in `kiosk/domain/models/value_objects.py`.

### Money
- **Fields**: `amount: Decimal`, `currency: str` (default "KRW")
- **Invariant**: `amount >= 0` — raises `ValueError` if violated
- **Operations**: Addition (same currency enforced), multiplication by quantity

### MenuItemId
- **Fields**: `value: UUID`
- **Factory Methods**: `.generate()`, `.from_str(value: str)`

### OrderId
- **Fields**: `value: UUID`
- **Factory Methods**: `.generate()`, `.from_str(value: str)`

### PaymentId
- **Fields**: `value: UUID`
- **Factory Method**: `.generate()`

### OrderItem (Line Item)
- **Fields**: `menu_item_id: MenuItemId`, `name: str`, `unit_price: Money`, `quantity: Quantity`
- **Quantity Constraints**: Between 1 and 10 (enforced in Quantity value object)
- **Mutable Quantity**: Uses `object.__setattr__()` to bypass frozen-ness when calling `increase_quantity()` or `set_quantity()` — see `.mini-harness/learnings/2026-04-18-frozen-dataclass-mutation.md` for pattern explanation
- **Subtotal**: `quantity.value * unit_price.amount`

---

## Use Cases: Application Services

Each use case accepts dependencies via constructor and implements `execute(...)` returning a DTO.

### Example: AddToCartUseCase

```python
def __init__(self, order_repo: OrderRepository):
    self.order_repo = order_repo

def execute(self, order_id: str, menu_item_id: str, name: str, price: str, quantity: int) -> CartDTO:
    # Get or create cart (PENDING order)
    order = self._get_or_create_cart(order_id)
    
    # Delegate duplicate handling to Order.add_item()
    item = OrderItem(MenuItemId.from_str(menu_item_id), name, Money(Decimal(price)), Quantity(quantity))
    order.add_item(item)
    
    # Save and return DTO
    self.order_repo.save(order)
    return CartDTO(...)
```

### Duplicate Item Handling

When the same `menu_item_id` is added twice:
- **Order.add_item()** searches for existing item with same ID
- If found: calls `existing.increase_quantity(new_qty)` — quantities **sum**
- If not found: appends as new item

Result: `add_item(item, qty=1)` then `add_item(item, qty=2)` → single item with `quantity = 3`

⚠️ **Test Discrepancy**: `tests/test_order.py::test_add_duplicate_item_raises` expects an exception on duplicate adds, but the implementation merges quantities instead. This test **will fail** against the current code. The integration test `test_cart_integration.py::TestAddToCart::test_add_duplicate_item_increases_quantity` reflects the actual behavior.

---

## Testing Strategy

### Fixtures in `tests/conftest.py`

| Fixture | Returns | Usage |
|---|---|---|
| `burger` | MenuItem("불고기버거", 5500 KRW) | Menu tests |
| `drink` | MenuItem("콜라", 2000 KRW) | Menu tests |
| `menu_repo` | `InMemoryMenuItemRepository()` (empty) | Use case tests |
| `order_repo` | `InMemoryOrderRepository()` (empty) | Order/cart tests |
| `payment_repo` | `InMemoryPaymentRepository()` (empty) | Payment tests |
| `domain_service` | `OrderDomainService()` | Domain service tests |
| `seeded_menu_repo` | `InMemoryMenuItemRepository()` with 6 items | Menu listing tests |

### Test Files by Concern

| File | Scenarios | Key Pattern |
|---|---|---|
| `test_value_objects.py` | Money arithmetic, ID generation/parsing | Invariant validation, immutability |
| `test_menu_item.py` | Create, mark available/unavailable, update price | Entity lifecycle |
| `test_order.py` | Order item constraints, state transitions, confirmation guards | **⚠️ Discrepancy in test_add_duplicate_item_raises** |
| `test_domain_service.py` | Create item from menu, validate payment, availability checks | Cross-aggregate logic |
| `test_use_cases.py` | GetMenuUseCase, PlaceOrderUseCase, ProcessPaymentUseCase | Use case orchestration, DTO contracts |
| `test_cart_integration.py` | Add/remove/update/checkout flow, duplicate handling, quantity limits | **Reference for actual duplicate behavior** |

### Running Tests

```bash
# All cart integration tests
pytest tests/test_cart_integration.py -v

# Just the duplicate item test (documents expected behavior)
pytest tests/test_cart_integration.py::TestAddToCart::test_add_duplicate_item_increases_quantity -v

# Domain model tests
pytest tests/test_order.py tests/test_value_objects.py -v
```

---

## Adding a New Use Case

1. Create file: `kiosk/application/use_cases/{use_case_name}.py`
2. Inject dependencies via `__init__`:
   ```python
   def __init__(self, order_repo: OrderRepository, menu_repo: MenuRepository):
       self.order_repo = order_repo
       self.menu_repo = menu_repo
   ```
3. Implement `execute(...)` returning a DTO (not domain model):
   ```python
   def execute(self, param1, param2) -> ResultDTO:
       # Orchestrate domain logic
       order = self.order_repo.find_by_id(...)
       menu_item = self.menu_repo.find_by_id(...)
       order.some_operation(menu_item)
       self.order_repo.save(order)
       return ResultDTO(...)
   ```
4. Write tests in `tests/test_use_cases.py`
5. Wire up in `kiosk/cli.py`'s `build_dependencies()` function:
   ```python
   def build_dependencies():
       ...
       new_use_case = NewUseCase(order_repo, menu_repo)
       return {..., 'new_use_case': new_use_case, ...}
   ```

---

## Repository Pattern

### Interface-First Design

Repositories are defined as abstract base classes in `domain/repositories/`:

```python
# domain/repositories/order_repository.py
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> None: ...
    
    @abstractmethod
    def find_by_id(self, order_id: OrderId) -> Optional[Order]: ...
    
    @abstractmethod
    def find_by_status(self, status: OrderStatus) -> List[Order]: ...
```

### Current Implementation: In-Memory

`infrastructure/repositories/in_memory_order_repository.py` stores orders in a dict:

```python
class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self._orders: Dict[OrderId, Order] = {}
```

**Important**: Dict key is the `OrderId` value object itself (not a UUID string), so equality relies on the frozen dataclass `__eq__`.

### Future: Database Migration

When adding persistence:
1. **Keep interface unchanged** — only swap implementation
2. **Load dependency in CLI's `build_dependencies()`** — do not hardcode concrete class
3. **Test against interface** — tests should use any `OrderRepository` implementation

---

## CLI Entry Point: Dependency Injection Container

`kiosk/cli.py` contains the DI setup:

```python
def build_dependencies():
    # Create repositories
    menu_repo = InMemoryMenuItemRepository()
    order_repo = InMemoryOrderRepository()
    payment_repo = InMemoryPaymentRepository()
    
    # Create domain service
    domain_service = OrderDomainService()
    
    # Create use cases
    get_menu = GetMenuUseCase(menu_repo)
    add_to_cart = AddToCartUseCase(order_repo)
    ...
    
    # Return dict for CLI access
    return {
        'menu_repo': menu_repo,
        'order_repo': order_repo,
        'get_menu': get_menu,
        'add_to_cart': add_to_cart,
        ...
    }
```

Update this function when:
- Adding new repositories
- Creating new use cases
- Wiring CLI commands to use cases

---

## Code Organization & Paths

```
kiosk/
  __init__.py
  cli.py                      # Entry point: build_dependencies() + interactive loop
  domain/
    models/
      menu_item.py            # MenuItem entity
      order.py                # Order aggregate (cart + order logic)
      payment.py              # Payment entity
      value_objects.py        # Money, Quantity, MenuItemId, OrderId, PaymentId
    repositories/
      menu_item_repository.py # Interface only
      order_repository.py     # Interface only
      payment_repository.py   # Interface only
    services/
      order_domain_service.py # CreateOrderItem, ValidatePayment
  application/
    use_cases/
      get_menu.py
      place_order.py
      process_payment.py
      cart_use_cases.py       # AddToCart, RemoveFromCart, UpdateQuantity, ViewCart, Checkout
  infrastructure/
    repositories/
      in_memory_*.py          # Concrete implementations
    seed_data.py              # Initial menu data
```

---

## Important Constraints

### Order State Guards

Attempting invalid operations raises `ValueError`:

```python
# PENDING state required
order.add_item(...)         # ValueError if not PENDING
order.remove_item(...)      # ValueError if not PENDING
order.update_item_quantity(...)  # ValueError if not PENDING

# CONFIRMED state required
order.mark_paid()           # ValueError if not CONFIRMED

# PENDING + non-empty required
order.confirm()             # ValueError if PENDING but empty items
```

### Quantity Limits

`Quantity` value object enforces 1–10 range:

```python
Quantity(0)   # ValueError: "수량은 1 이상이어야 합니다."
Quantity(11)  # ValueError: "수량은 10 이하여야 합니다."
```

### Payment Amount Validation

`ProcessPaymentUseCase` validates that payment amount matches order total before marking paid.

---

## Architecture Decision Records

The project documents key decisions in `.dev/adr/`:

- **2026-04-18-order-and-shopping-cart-inclusion.md** — Architectural debate on whether to implement cart as a separate entity or as a PENDING Order. Decided: Cart = PENDING Order (simplifies design, avoids duplication).

Review ADRs before proposing changes to core domain model.

---

## Common Workflows

### Add a New Menu Item Property

1. Update `MenuItem` model in `domain/models/menu_item.py`
2. Seed in `infrastructure/seed_data.py`
3. Update DTO in use case output if needed
4. Test: `pytest tests/test_menu_item.py -v`

### Extend Order Aggregate

1. Add method to `Order` class with state guard (`if self.status != OrderStatus.PENDING: raise ValueError(...)`)
2. Write test in `tests/test_order.py`
3. Update use case if needed, test end-to-end in `test_use_cases.py`

### Add Payment Method Option

1. Add enum value to payment method in `domain/models/payment.py`
2. Update `ProcessPaymentUseCase` validation logic
3. Test: `pytest tests/test_payment.py -v`

---

## Debugging Tips

### Inspect Order Contents

```python
order = order_repo.find_by_id(order_id)
print(f"Status: {order.status.value}")
print(f"Items: {[(item.name, item.quantity.value) for item in order.items]}")
print(f"Total: {order.total_amount.amount}")
```

### Test Single Use Case

```bash
pytest tests/test_use_cases.py::TestAddToCartUseCase::test_add_item -vv
```

### Trace CLI Execution

Add print statements in:
- `execute()` methods of use cases
- Domain service methods
- Order state transition methods

---

## Harness & Development Workflow

This project includes a sophisticated development workflow system (mini-harness). For guidance on:
- Structured architectural debates (`/council`)
- Task specification and breakdown (`/mini-specify`, `/taskify`)
- Implementation planning (`/dependency-resolve`, `/mini-execute`)
- Learning capture (`/mini-compound`)

See `docs/harness.md`.

---

## References & Further Reading

- **DDD Patterns**: See domain models for entities, aggregates, value objects, repositories
- **Testing**: See `tests/` for unit and integration test examples
- **Architecture Decisions**: See `.dev/adr/` for rationale behind design choices
- **Learnings**: See `.mini-harness/learnings/` for reusable patterns discovered during development
