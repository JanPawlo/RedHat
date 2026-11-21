from app.const.sql import LIKE_ESCAPE_CHAR, LIKE_WILDCARDS


def escape_like(value: str) -> str:
    escaped = value.replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)

    for wildcard in LIKE_WILDCARDS:
        escaped = escaped.replace(wildcard, f"{LIKE_ESCAPE_CHAR}{wildcard}")

    return escaped


def contains_pattern(value: str) -> str:
    return f"%{escape_like(value.strip())}%"
