"""Publish a system-update notice without exposing any admin UI."""

import argparse

from app.db.session import SessionLocal
from app.models.system_update import SystemUpdate


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a system update")
    parser.add_argument("title", help="Short update title")
    parser.add_argument("description", help="What changed")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        update = SystemUpdate(
            title=args.title.strip(),
            description=args.description.strip(),
        )
        db.add(update)
        db.commit()
        print(f"Published system update: {update.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
