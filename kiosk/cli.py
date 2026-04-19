"""간단한 키오스크 CLI 인터페이스"""
from domain.services.order_domain_service import OrderDomainService
from domain.models.value_objects import UserId
from application.use_cases.get_menu import GetMenuUseCase
from application.use_cases.place_order import PlaceOrderUseCase, OrderItemRequest
from application.use_cases.process_payment import ProcessPaymentUseCase
from application.use_cases.cart_use_cases import (
    AddToCartUseCase, RemoveFromCartUseCase, UpdateQuantityUseCase, ViewCartUseCase, CheckoutUseCase
)
from application.use_cases.apply_coupon import ApplyCouponUseCase
from application.use_cases.validate_discount import ValidateDiscountUseCase
from application.use_cases.user_use_cases import CreateUserUseCase, GetUserUseCase, AuthenticateUserUseCase
from application.use_cases.order_history_use_cases import GetOrderHistoryUseCase, GetOrderDetailUseCase
from infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from infrastructure.repositories.in_memory_payment_repository import InMemoryPaymentRepository
from infrastructure.repositories.in_memory_discount_repository import InMemoryDiscountRepository
from infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from infrastructure.seed_data import seed_menu
from application.admin.manage_menu import AddMenuItemUseCase, UpdateMenuItemUseCase, DeleteMenuItemUseCase
from application.admin.change_menu_price import ChangeMenuPriceUseCase
from application.admin.mark_menu_unavailable import MarkMenuUnavailableUseCase
from application.admin.query_orders import QueryOrdersUseCase


def build_dependencies():
    menu_repo = InMemoryMenuItemRepository()
    order_repo = InMemoryOrderRepository()
    payment_repo = InMemoryPaymentRepository()
    discount_repo = InMemoryDiscountRepository()
    user_repo = InMemoryUserRepository()
    domain_service = OrderDomainService()

    seed_menu(menu_repo)

    get_menu = GetMenuUseCase(menu_repo)
    place_order = PlaceOrderUseCase(menu_repo, order_repo, domain_service)
    process_payment = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)

    add_to_cart = AddToCartUseCase(order_repo)
    remove_from_cart = RemoveFromCartUseCase(order_repo)
    update_quantity = UpdateQuantityUseCase(order_repo)
    view_cart = ViewCartUseCase(order_repo)
    checkout = CheckoutUseCase(order_repo)

    apply_coupon = ApplyCouponUseCase(order_repo, discount_repo)
    validate_discount = ValidateDiscountUseCase(discount_repo)

    create_user = CreateUserUseCase(user_repo)
    get_user = GetUserUseCase(user_repo)
    authenticate_user = AuthenticateUserUseCase(user_repo)
    get_order_history = GetOrderHistoryUseCase(order_repo)
    get_order_detail = GetOrderDetailUseCase(order_repo)

    admin_add_menu = AddMenuItemUseCase(menu_repo)
    admin_update_menu = UpdateMenuItemUseCase(menu_repo)
    admin_delete_menu = DeleteMenuItemUseCase(menu_repo)
    admin_change_price = ChangeMenuPriceUseCase(menu_repo)
    admin_mark_unavailable = MarkMenuUnavailableUseCase(menu_repo, order_repo)
    admin_query_orders = QueryOrdersUseCase(order_repo)

    return {
        'get_menu': get_menu,
        'place_order': place_order,
        'process_payment': process_payment,
        'menu_repo': menu_repo,
        'order_repo': order_repo,
        'discount_repo': discount_repo,
        'user_repo': user_repo,
        'add_to_cart': add_to_cart,
        'remove_from_cart': remove_from_cart,
        'update_quantity': update_quantity,
        'view_cart': view_cart,
        'checkout': checkout,
        'apply_coupon': apply_coupon,
        'validate_discount': validate_discount,
        'create_user': create_user,
        'get_user': get_user,
        'authenticate_user': authenticate_user,
        'get_order_history': get_order_history,
        'get_order_detail': get_order_detail,
        'admin_add_menu': admin_add_menu,
        'admin_update_menu': admin_update_menu,
        'admin_delete_menu': admin_delete_menu,
        'admin_change_price': admin_change_price,
        'admin_mark_unavailable': admin_mark_unavailable,
        'admin_query_orders': admin_query_orders,
    }


def display_menu(menu_items):
    print("\n[메뉴판]")
    for idx, item in enumerate(menu_items, 1):
        print(f"  {idx}. {item.name} - {item.price:,} {item.currency} ({item.category})")


def display_cart(cart_dto):
    print("\n[카트 내용]")
    if not cart_dto.items:
        print("  (비어있음)")
        return
    for item in cart_dto.items:
        print(f"  - {item.name} x{item.quantity} = {item.subtotal} {item.unit_price.split()[1]}")
    print(f"총액: {cart_dto.total_amount} / 총 수량: {cart_dto.item_count}개")
    print(f"카트 ID: {cart_dto.order_id}")


def run():
    deps = build_dependencies()
    menu_repo = deps['menu_repo']
    order_repo = deps['order_repo']
    add_to_cart = deps['add_to_cart']
    remove_from_cart = deps['remove_from_cart']
    update_quantity = deps['update_quantity']
    view_cart = deps['view_cart']
    checkout = deps['checkout']
    process_payment = deps['process_payment']
    authenticate_user = deps['authenticate_user']
    create_user = deps['create_user']
    get_order_history = deps['get_order_history']
    get_order_detail = deps['get_order_detail']

    print("=== 키오스크 시스템 ===")

    menu_items = menu_repo.get_all()
    display_menu(menu_items)

    # 사용자 인증
    current_user_id = None
    print("\n[사용자 인증]")
    auth_choice = input("(1)로그인 (2)회원가입 (3)비회원 (선택): ").strip()

    if auth_choice == "1":  # 로그인
        email = input("이메일: ").strip()
        user = authenticate_user.execute(email)
        if user:
            current_user_id = user.user_id
            print(f"✓ {user.name}님 로그인되었습니다.")
        else:
            print("❌ 사용자를 찾을 수 없습니다.")
    elif auth_choice == "2":  # 회원가입
        email = input("이메일: ").strip()
        name = input("이름: ").strip()
        try:
            user = create_user.execute(email, name)
            current_user_id = user.user_id
            print(f"✓ {user.name}님 회원가입되었습니다.")
        except ValueError as e:
            print(f"❌ {e}")
    else:  # 비회원
        print("비회원으로 진행합니다.")

    # 카트 초기화
    current_order_id = None

    # 대화형 카트 루프
    while True:
        print("\n[명령어] (1)상품추가 (2)수량변경 (3)상품제거 (4)카트보기 (5)결제 (6)주문내역 (7)종료")
        cmd = input("선택: ").strip()

        try:
            if cmd == "1":  # 상품 추가
                display_menu(menu_items)
                idx = int(input("상품 번호: ")) - 1
                qty = int(input("수량: "))
                if 0 <= idx < len(menu_items):
                    item = menu_items[idx]
                    cart = add_to_cart.execute(current_order_id or "", str(item.id.value), item.name, str(item.price.amount), qty)
                    current_order_id = cart.order_id
                    display_cart(cart)
                else:
                    print("❌ 유효하지 않은 상품 번호")

            elif cmd == "2":  # 수량 변경
                if not current_order_id:
                    print("❌ 카트가 없습니다")
                    continue
                display_menu(menu_items)
                idx = int(input("상품 번호: ")) - 1
                qty = int(input("새 수량: "))
                if 0 <= idx < len(menu_items):
                    item = menu_items[idx]
                    cart = update_quantity.execute(current_order_id, str(item.id.value), qty)
                    display_cart(cart)
                else:
                    print("❌ 유효하지 않은 상품 번호")

            elif cmd == "3":  # 상품 제거
                if not current_order_id:
                    print("❌ 카트가 없습니다")
                    continue
                display_menu(menu_items)
                idx = int(input("상품 번호: ")) - 1
                if 0 <= idx < len(menu_items):
                    item = menu_items[idx]
                    cart = remove_from_cart.execute(current_order_id, str(item.id.value))
                    display_cart(cart)
                else:
                    print("❌ 유효하지 않은 상품 번호")

            elif cmd == "4":  # 카트 보기
                if not current_order_id:
                    print("❌ 카트가 없습니다")
                    continue
                cart = view_cart.execute(current_order_id)
                display_cart(cart)

            elif cmd == "5":  # 결제
                if not current_order_id:
                    print("❌ 카트가 없습니다")
                    continue
                cart = checkout.execute(current_order_id)
                print(f"\n✓ 주문 확정! 총액: {cart.total_amount}")
                method = input("결제 수단 (카드/현금): ").strip()
                payment = process_payment.execute(current_order_id, method)
                print(f"✓ 결제 완료! 결제 ID: {payment.payment_id}")
                print("이용해 주셔서 감사합니다!")
                break

            elif cmd == "6":  # 주문내역
                if not current_user_id:
                    print("❌ 로그인 후 주문내역을 조회할 수 있습니다.")
                    continue
                history = get_order_history.execute(current_user_id)
                if not history:
                    print("주문내역이 없습니다.")
                else:
                    print("\n[주문내역]")
                    for i, order in enumerate(history, 1):
                        print(f"  {i}. 주문 #{order.order_id[:8]}... - {order.status} ({order.total_amount} KRW)")

            elif cmd == "7":  # 종료
                print("프로그램을 종료합니다.")
                break

            else:
                print("❌ 유효하지 않은 명령어")

        except ValueError as e:
            print(f"❌ 입력 오류: {e}")
        except Exception as e:
            print(f"❌ 오류: {e}")


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    run()
