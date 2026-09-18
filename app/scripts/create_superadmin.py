"""Интерактивное создание первого суперадминистратора.

Запускается вручную в контейнере API и не используется миграциями или стартом
приложения. Пароль вводится скрыто и не попадает в историю терминала.
"""

from getpass import getpass
import sys

from app.core.security import hash_password
from app.db.session import SessionLocal
# Регистрируем все модели до первого запроса: SQLAlchemy связывает отношения
# между ними лениво, а эта административная команда запускается вне FastAPI.
from app.models.behavior_record import BehaviorRecord  # noqa: F401
from app.models.parent_student import ParentStudent  # noqa: F401
from app.models.school import School  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.teacher_assignment import TeacherAssignment  # noqa: F401
from app.models.user import User


def prompt_required(label: str) -> str:
    value = input(f"{label}: ").strip()
    if not value:
        print(f"Поле «{label}» обязательно.")
        sys.exit(1)
    return value


def main() -> None:
    print("Создание суперадминистратора. Все поля обязательны.")
    last_name = prompt_required("Фамилия")
    first_name = prompt_required("Имя")
    middle_name = prompt_required("Отчество")
    login = prompt_required("Логин").lower()
    password = getpass("Пароль (минимум 12 символов): ")
    password_confirmation = getpass("Повторите пароль: ")

    if len(password) < 12:
        print("Пароль должен содержать не менее 12 символов.")
        sys.exit(1)
    if password != password_confirmation:
        print("Пароли не совпадают.")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(User).filter(User.login == login).first():
            print("Пользователь с таким логином уже существует.")
            sys.exit(1)

        user = User(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            login=login,
            hashed_password=hash_password(password),
            role="superadmin",
            is_blocked=False,
            school_id=None,
        )
        db.add(user)
        db.commit()
        print(f"Суперадминистратор {login} успешно создан.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
