"""간단한 키오스크 CLI 인터페이스"""
from domain.services.order_domain_service import OrderDomainService
from application.use_cases.get_menu import GetMenuUseCase
from application.use_cases.place_order import PlaceOrderUseCase, OrderItemRequest
from application.use_cases.process_payment import ProcessPaymentUseCase
from infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from infrastructure.repositories.in_memory_payment_repository import InMemoryPaymentRepository
from infrastructure.seed_data import seed_menu


def build_dependencies():
    menu_repo = InMemoryMenuItemRepository()
    order_repo = InMemoryOrderRepository()
    payment_repo = InMemoryPaymentRepository()
    domain_service = OrderDomainService()

    seed_menu(menu_repo)

    get_menu = GetMenuUseCase(menu_repo)
    place_order = PlaceOrderUseCase(menu_repo, order_repo, domain_service)
    process_payment = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)

    return get_menu, place_order, process_payment


def run():
    get_menu, place_order, process_payment = build_dependencies()

    print("=== 키오스크 시스템 ===")

    # 메뉴 조회
    menu_items = get_menu.execute()
    print("\n[메뉴판]")
    for idx, item in enumerate(menu_items, 1):
        print(f"  {idx}. {item.name} - {item.price:,} {item.currency} ({item.category})")

    # 주문 생성
    print("\n주문을 시작합니다...")
    requests = [
        OrderItemRequest(menu_item_id=menu_items[0].id, quantity=1),
        OrderItemRequest(menu_item_id=menu_items[2].id, quantity=2),
    ]
    result = place_order.execute(requests)
    print(f"주문 완료! 주문 ID: {result.order_id}")
    print(f"총 금액: {result.total_amount:,} {result.currency} / 수량: {result.item_count}개")

    # 결제 처리
    print("\n카드로 결제를 진행합니다...")
    payment_result = process_payment.execute(result.order_id, "카드")
    print(f"결제 완료! 결제 ID: {payment_result.payment_id}")
    print(f"결제 금액: {payment_result.amount_paid} / 결제 방법: {payment_result.method}")
    print("\n이용해 주셔서 감사합니다!")


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    run()
