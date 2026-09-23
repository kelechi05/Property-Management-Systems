def to_proper_case(value):
    if not value:
        return value
    return " ".join(part.capitalize() for part in str(value).split())
