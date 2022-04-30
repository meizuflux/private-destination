TIME_UNITS = {
    "minutes": 60,
    "hours": 60 * 60,
    "days": 60 * 60 * 24,
    "weeks": 60 * 60 * 24 * 7,
    "months": 60 * 60 * 24 * 30,
}


def get_seconds(amount: int, unit: str) -> int:
    return amount * TIME_UNITS[unit]


def get_amount_and_unit(seconds: int) -> tuple[int, str]:
    print(seconds)
    possible_answers: list[tuple[int, str]] = []
    for unit, to_divide in TIME_UNITS.items():
        computed = seconds / to_divide
        if computed.is_integer() and computed >= 1:
            possible_answers.append((int(computed), unit))

    return min(possible_answers)
