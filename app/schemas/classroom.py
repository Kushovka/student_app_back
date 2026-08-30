ALLOWED_CLASS_LETTERS = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")


def validate_grade_range(value: int) -> int:
    if value < 1 or value > 11:
        raise ValueError("Grade must be between 1 and 11")
    return value


def normalize_class_letter(value: str) -> str:
    letter = value.strip().upper()
    if len(letter) != 1 or letter not in ALLOWED_CLASS_LETTERS:
        raise ValueError("Class letter must be one Russian letter from А to Я")
    return letter
