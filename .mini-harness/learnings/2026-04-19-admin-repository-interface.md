---
date: 2026-04-19
tags: [admin, repository, interface, use-case, delete, ddd]
---

## Problem
manage_menu.py의 DeleteMenuItemUseCase 작성 시 menu_repo.delete()를 호출했으나, MenuItemRepository 인터페이스에 delete() 메서드가 정의되지 않아 런타임 오류 위험이 있었다.

## Cause
use case 구현 전에 repository 인터페이스 메서드 목록을 먼저 확인하지 않고 바로 구현에 착수했음.

## Rule
관리자 use case처럼 새 repo 메서드가 필요한 경우, 먼저 domain/repositories/ 인터페이스 파일을 Read하여 존재하지 않는 메서드는 인터페이스와 인메모리 구현 양쪽에 추가한 뒤 use case를 작성한다.
