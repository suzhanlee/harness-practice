# ADR: 관리자 백오피스 기능을 기존 DDD 구조에 어떻게 통합할 것인가

**날짜**: 2026-04-19
**상태**: Decided

---

## 결정

관리자 백오피스 use case를 `kiosk/application/admin/` 네임스페이스로 격리한다. 도메인 레이어(domain/models, domain/services, domain/repositories)와 infrastructure 레이어는 고객·관리자 공유를 유지한다. 별도 Bounded Context 분리 및 AdminMenuPolicyService 같은 관리자 전용 도메인 서비스 신설은 하지 않는다.

## 컨텍스트

관리자 백오피스 기능이 전혀 없어 메뉴 추가/수정/삭제, 가격 변경, 품절 처리, 주문 내역 조회가 불가능한 상태이며, 관리자로부터 불만/불편 보고를 받고 있다. 이에 5가지 관리자 기능을 백엔드 로직으로 구현하되 DDD domain/application/infrastructure 레이어 경계를 준수해야 한다. UI/프론트엔드는 구현 범위 외다.

핵심 설계 질문은 "관리자 use case를 기존 `application/use_cases/`에 통합(Option A)할 것인가, `application/admin/` 네임스페이스로 격리(Option B)할 것인가"이다.

## 분석 렌즈

| 번호 | 렌즈 | 이 렌즈가 중요한 이유 |
|------|------|------|
| 1 | 사용자 가치 / 요구사항 충족도 | success_criteria "모든 관리자 기능 테스트 케이스 통과" 달성 여부 |
| 2 | 도메인 경계 설계 | 관리자 기능이 별도 Bounded Context나 도메인 서비스를 요구하는가 |
| 3 | Application 레이어 격리 | actor별 워크플로우 분리가 유지보수성·탐색성에 기여하는가 |
| 4 | 테스트 가능성 | 관리자 기능 테스트 케이스 전량 통과 여부를 구조적으로 보장하는가 |
| 5 | 도메인 모델 순수성 | 관리자 조작이 기존 Order/MenuItem 도메인 불변식을 오염시키지 않는가 |

## 패널 최종 포지션

| 패널리스트 | 역할 | 최종 입장 | Shift |
|-----------|------|----------|-------|
| product-owner | 관리자 사용자 요구사항·성공 기준 대변 | Option B(application/admin/ 격리) — 행위자 분리는 요구사항에서 이미 확정된 사실이며 구조에 투명하게 반영해야 함 | yes |
| ddd-architect | DDD Bounded Context·Aggregate 설계 원칙 | Option B(application/admin/ 격리) — AdminMenuPolicyService 신설 철회, application 레이어 분리만 유지 | yes |
| devils-advocate | 지배적 의견 도전·과잉 설계 지적 | Option A(admin_*.py prefix) 고수 — 분리는 투기적 설계이며 파일명 prefix로 충분 | 부분(파일명 prefix 양보) |

## 토론 로그

### product-owner → devils-advocate

- **반박**: "CRUD·조회는 사용자 가치에 0 기여"라는 주장에 대해, 관리자와 고객은 스펙에서 이미 구분된 행위자이므로 application 레이어 분리는 가상이 아니라 확정된 요구사항을 구현 구조에 투명하게 반영하는 것
- **응답**: shift: no — "행위자 구분은 네임스페이스가 아닌 파일명 prefix로 충분히 표현 가능"이라며 거부

### ddd-architect → devils-advocate

- **반박**: AdminMenuPolicyService는 cross-aggregate 가드(품절 메뉴 PENDING Order 처리)를 위한 것으로, invariant를 단일 애그리거트에 내장할 수 없는 경우를 다룸
- **응답**: shift: yes — `OrderItem.unit_price` 값 객체 복사가 가격 스냅샷을 이미 구조적으로 보장하므로, cross-aggregate 정책 논거가 약화됨을 수용. AdminMenuPolicyService 신설 제안 철회

### devils-advocate → ddd-architect

- **반박**: "별도 도메인 서비스" 신설은 `MenuItem.change_price()` 같은 행위가 service 레이어로 유출되는 Anemic Domain 안티패턴 유발
- **응답**: shift: yes — 도메인 서비스 철회하고, 필요 메서드는 애그리거트에 직접 추가하는 것으로 합의

### devils-advocate → product-owner

- **반박**: 파이썬에서 application 레이어 네임스페이스 분리는 invariant 강제력이 0이며 심리적 만족에 불과. "사회적 강제"는 파일명 prefix로도 동일하게 제공됨
- **응답**: shift: 부분 수용 — 가격 스냅샷 cross-aggregate 주장은 철회. 그러나 "행위자 분리의 구조적 표현"이라는 핵심 근거는 유지

## 트레이드오프

| 선택지 | 장점 | 단점 |
|--------|------|------|
| Option A (통합 + admin_*.py prefix) | 초기 파일 수 적음, YAGNI 원칙 부합, 이동 비용 낮음 | 관리자-고객 use case 혼재로 탐색 비용 증가, 구조로 행위자 경계 미표현, 파일 수 증가 시 드리프트 탐지 늦음 |
| Option B (application/admin/ 격리) | 행위자 경계 구조 표현, tests/admin/ 1:1 매핑으로 테스트 추적성 보장, 미래 권한/감사 추가 시 마이그레이션 비용 낮음 | 초기 파일/디렉터리 수 증가, domain/infrastructure 레이어 분리 유혹 생길 수 있음 |

## 최종 판정

**Option B 채택.** 결정적 렌즈는 **Application 레이어 격리**와 **사용자 가치/요구사항 충족도**였다.

product-owner와 ddd-architect는 핵심 쟁점(AdminMenuPolicyService 필요 여부)에서 devils-advocate 논증을 수용해 shift했고, 그 결과 "도메인 레이어 공유 + Application 레이어만 격리"라는 수렴안을 도출했다. 이는 devils-advocate가 우려한 Anemic Domain 리스크를 실제로 제거한다.

남은 이견(Application 레이어 디렉터리 분리 여부)에서 Option B가 선택된 이유:
1. **요구사항에서 이미 확정된 행위자 분리**(`users: 키오스크 관리자`)를 구현 구조에 투명하게 반영하는 것은 투기적 설계가 아니다.
2. CLAUDE.md "One business operation per use case" 원칙 하에서 5개 관리자 use case 개별 파일이 평면 `use_cases/`에 추가되면 기존 8개 파일과의 혼재가 탐색 비용을 높인다.
3. 분리는 application 레이어에서만 멈춘다. `domain/admin/` 또는 `infrastructure/admin/` 생성은 Ubiquitous Language를 훼손하므로 엄격히 금지한다.

devils-advocate가 제안한 **재평가 트리거**는 ADR 부록으로 채택한다:
- (a) 권한/RBAC 요구사항 등장
- (b) 감사 로그 요구사항 등장
- (c) 관리자/고객 별도 배포 단위 요구
- (d) use_cases/ 또는 admin/ 파일 수 20개 초과

### 실행 체크리스트

1. `kiosk/domain/models/menu_item.py`에 `change_price(new_price: Money)` 메서드 추가 (선행 작업)
2. `kiosk/domain/models/order.py`의 `Order.confirm()`에 품절 메뉴 가드 추가 (선행 작업)
3. `kiosk/application/admin/` 디렉터리 생성 + `__init__.py`
4. 관리자 use case 5개를 `application/admin/` 하위 개별 파일로 배치
   - `manage_menu.py` (메뉴 추가/수정/삭제)
   - `change_menu_price.py` (가격 변경)
   - `mark_menu_unavailable.py` (품절 처리)
   - `query_orders.py` (주문 내역 조회)
5. `tests/admin/` 디렉터리에 대응 테스트 파일 배치
6. `kiosk/cli.py`의 `build_dependencies()`에서 `admin_*` 키로 네임스페이싱
