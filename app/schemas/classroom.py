ALLOWED_CLASS_LETTERS = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
MIN_GRADE = 5
MAX_GRADE = 9


def validate_grade_range(value: int) -> int:
    if value < MIN_GRADE or value > MAX_GRADE:
        raise ValueError("Grade must be between 5 and 9")
    return value


def normalize_class_letter(value: str) -> str:
    letter = value.strip().upper()
    if len(letter) != 1 or letter not in ALLOWED_CLASS_LETTERS:
        raise ValueError("Class letter must be one Russian letter from А to Я")
    return letter
