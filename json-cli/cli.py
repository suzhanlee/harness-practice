"""
JSON CLI - json 파일 CRUD 연습용 CLI
사용법: python cli.py --help
"""

import json
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(help="JSON 파일 CRUD 연습용 CLI")

DATA_FILE = Path(__file__).parent / "data.json"


# ── 파일 I/O 헬퍼 ──────────────────────────────────────────────

def load() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def find_task(tasks: list, task_id: int) -> Optional[dict]:
    return next((t for t in tasks if t["id"] == task_id), None)


# ── Commands ───────────────────────────────────────────────────

@app.command()
def list_tasks():
    """전체 task 목록 출력"""
    data = load()
    tasks = data["tasks"]

    if not tasks:
        typer.echo("task가 없습니다.")
        return

    typer.echo(f"{'ID':<5} {'TITLE':<25} {'STATUS':<10} {'PRIORITY'}")
    typer.echo("-" * 55)
    for t in tasks:
        typer.echo(f"{t['id']:<5} {t['title']:<25} {t['status']:<10} {t['priority']}")


@app.command()
def get(task_id: int = typer.Argument(..., help="조회할 task ID")):
    """특정 task 조회"""
    data = load()
    task = find_task(data["tasks"], task_id)

    if task is None:
        typer.echo(f"ID {task_id} 에 해당하는 task가 없습니다.", err=True)
        raise typer.Exit(1)

    typer.echo(json.dumps(task, indent=2, ensure_ascii=False))


@app.command()
def add(
    title: str = typer.Option(..., "--title", "-t", help="task 제목"),
    status: str = typer.Option("pending", "--status", "-s", help="상태 (pending/done)"),
    priority: str = typer.Option("medium", "--priority", "-p", help="우선순위 (low/medium/high)"),
):
    """새 task 추가"""
    data = load()
    tasks = data["tasks"]

    new_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {"id": new_id, "title": title, "status": status, "priority": priority}

    tasks.append(new_task)
    save(data)

    typer.echo(f"추가 완료:")
    typer.echo(json.dumps(new_task, indent=2, ensure_ascii=False))


@app.command()
def update(
    task_id: int = typer.Argument(..., help="수정할 task ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="새 제목"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="새 상태"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="새 우선순위"),
):
    """특정 task 수정 (변경할 필드만 입력)"""
    data = load()
    task = find_task(data["tasks"], task_id)

    if task is None:
        typer.echo(f"ID {task_id} 에 해당하는 task가 없습니다.", err=True)
        raise typer.Exit(1)

    if title is not None:
        task["title"] = title
    if status is not None:
        task["status"] = status
    if priority is not None:
        task["priority"] = priority

    save(data)
    typer.echo(f"수정 완료:")
    typer.echo(json.dumps(task, indent=2, ensure_ascii=False))


@app.command()
def delete(
    task_id: int = typer.Argument(..., help="삭제할 task ID"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 삭제"),
):
    """특정 task 삭제"""
    data = load()
    task = find_task(data["tasks"], task_id)

    if task is None:
        typer.echo(f"ID {task_id} 에 해당하는 task가 없습니다.", err=True)
        raise typer.Exit(1)

    if not force:
        typer.confirm(f"'{task['title']}' 을 삭제하시겠습니까?", abort=True)

    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    save(data)
    typer.echo(f"ID {task_id} 삭제 완료.")


if __name__ == "__main__":
    app()
