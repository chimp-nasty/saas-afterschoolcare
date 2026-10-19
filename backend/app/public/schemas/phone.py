def normalise_au_phone(value: str) -> str:
    """
    An Australian phone number as 10 digits ("0400 000 000" and
    "+61 400 000 000" both become "0400000000"). Customer profiles and pickup
    people share this, so the same number always compares equal (a phone
    number belongs to one family, schema/0004).
    """
    digits = (
        value
        .strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if digits.startswith("+61"):
        digits = "0" + digits[3:]

    if not digits.isdigit() or len(digits) != 10:
        raise ValueError("Enter a valid Australian phone number")

    return digits
