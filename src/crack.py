from .globals import CODE_BASE, GROUP_COUNT


def custom_ord(char: str) -> int:
    """
    Custom ord function that puts does uppercase letters then numbers (0-35)
    """
    if len(char) != 1:
        raise TypeError(f"Expected 1 character, got {len(char)} characters")
    if char.isupper():
        return ord(char) - 65
    if char.isdigit():
        return int(char) + 26
    raise ValueError(f"Invalid char {char}")


def custom_chr(code: int) -> str:
    """
    Custom chr function that puts does uppercase letters then numbers (0-35)
    """
    if not isinstance(code, int):
        raise TypeError(f"Expected int, got {type(code)}")
    if code < 0:
        raise ValueError(f"Expected positive int, got {code}")
    if code > 35:
        raise ValueError(f"Expected int less than 36, got {code}")
    if code < 26:
        return chr(code + 65)
    if code < 36:
        return str(code - 26)
    raise ValueError(f"Invalid code {code}")


def make_letter_groups(word: str) -> tuple[tuple[str]]:
    """
    Divide letters in groups of GROUP_COUNT, via round robin
    """
    return tuple(tuple(word[i::GROUP_COUNT]) for i in range(GROUP_COUNT))


def intra_letter_groups_diff(groups: tuple[tuple[str]]) -> tuple[tuple[int]]:
    """
    Get the pattern of differences between characters in a group, using custom ord.

    This is used as a signature for words that can be rotated to by altering the knobs.
    """
    try:
        return tuple(
            tuple(custom_ord(x) - custom_ord(y) for x, y in zip(group, group[1:], strict=False)) for group in groups
        )
    except ValueError as e:
        raise ValueError(f"Invalid group {groups}") from e


def inter_letter_groups_diff(first_groups: tuple[tuple[str]], second_groups: tuple[tuple[str]]) -> tuple[tuple[int]]:
    """
    Get the pattern of differences between characters in two groups, using custom ord.

    This is used as the desired knob difference to get from the first word to the second word.

    If the intra letter groups diff for both words is the same, then the values in each inter letter group will be the same.
    """
    try:
        return tuple(
            tuple(custom_ord(x) - custom_ord(y) for x, y in zip(first_group, second_group, strict=False))
            for first_group, second_group in zip(first_groups, second_groups, strict=False)
        )
    except ValueError as e:
        raise ValueError(f"Invalid groups {first_groups} and {second_groups}") from e


def identical_inter_letter_groups_diff(first_groups: tuple[tuple[str]], second_groups: tuple[tuple[str]]) -> tuple[int]:
    """
    Optimized version of inter_letter_groups_diff that assumes you already checked that intra letter groups diffs are the same.
    """
    try:
        return tuple(custom_ord(x[0]) - custom_ord(y[0]) for x, y in zip(first_groups, second_groups, strict=False))
    except ValueError as e:
        raise ValueError(f"Invalid groups {first_groups} and {second_groups}") from e


def add_tuples_in_base(first_tuple: tuple[int], second_tuple: tuple[int]) -> tuple[int]:
    """
    Get the knob sum between two knob states.

    """
    return tuple((current + knob) % CODE_BASE for current, knob in zip(second_tuple, first_tuple, strict=False))


def subtract_tuples_in_base(first_tuple: tuple[int], second_tuple: tuple[int]) -> tuple[int]:
    """
    Get the knob difference between two knob states (first - second)
    """
    return tuple((first - second) % CODE_BASE for first, second in zip(first_tuple, second_tuple, strict=False))


def rotate_tuple(tup: tuple[int], rotate: int) -> tuple[int]:
    """
    Rotate a tuple by rotate
    positive is all the items go towards the start by x with items wrapping around to the end
    negative is all the items go towards the end by x with items wrapping around to the start
    """
    return tup[rotate:] + tup[:rotate]


def get_first_of_diffs_or_none(group: tuple[tuple[int]]) -> tuple[int]:
    """
    Get the first item of a group of diffs, or None if there is no first item
    """
    return tuple(next(iter(group), None) for group in group)


def normalize_intra_letter_groups_diff(diff: tuple[tuple[int]]) -> tuple[tuple[int]]:
    """
    Normalize the intra letter groups diff to remove negative values. Since the knobs wrap, all negative values can be expressed as positive values.

    If the value is negative, modulo it by CODE_BASE and then add CODE_BASE to it to make it positive and within range.
    """
    return tuple(tuple((value + CODE_BASE) % CODE_BASE for value in group) for group in diff)


def normalize_inter_letter_groups_diff(diff: tuple[int]) -> tuple[int]:
    """
    Normalize the inter letter groups diff to remove negative values. Since the knobs wrap, all negative values can be expressed as positive values.

    If the value is negative, modulo it by CODE_BASE and then add CODE_BASE to it to make it positive and within range.
    """
    return tuple((value + CODE_BASE) % CODE_BASE for value in diff)


def apply_inter_letter_groups_diff_to_word(word: str, diff: tuple[int]) -> str:
    """
    Apply the inter letter groups diff to a word to get the target word, for every letter in the word.
    """
    return "".join(
        custom_chr((custom_ord(letter) + diff[index % GROUP_COUNT]) % CODE_BASE) for index, letter in enumerate(word)
    )


if __name__ == "__main__":
    # print(intra_letter_groups_diff(make_letter_groups("VIHFRVJP7")))
    # print(intra_letter_groups_diff(make_letter_groups("MACHINERY")))
    # print(identical_inter_letter_groups_diff(make_letter_groups("VIHFRVJP7"), make_letter_groups("MACHINERY")))
    # print(add_tuples_in_base((9, 8, 5, -2), (2, 4, 8, 16)))
    # print('***')
    # print(intra_letter_groups_diff(make_letter_groups("URASB")))
    # print(intra_letter_groups_diff(make_letter_groups("BRASS")))
    # print(identical_inter_letter_groups_diff(make_letter_groups("URASB"), make_letter_groups("BRASS")))
    # print(add_tuples_in_base((-17, 0, 0, 0), (2, 4, 8, 16)))
    # print(add_tuples_in_base((19, 0, 0, 0), (2, 4, 8, 16)))
    # print(normalize_intra_letter_groups_diff(intra_letter_groups_diff(make_letter_groups("URASB"))))
    # print(normalize_intra_letter_groups_diff(intra_letter_groups_diff(make_letter_groups("BRASS"))))
    test_code = (2, 4, 8, 16)
    test_words = [
        "BRAVO",
        "TANGO",
        "NORTH",
        "SOUTH",
        "EAST",
        "WEST",
        "GO",
        "STOP",
        "HEAVY",
        "CARGO",
        "PLEASE",
        "OBTAIN",
        "BRASS",
        "GOING",
        "MACHINERY",
    ]
    for word in test_words:
        print(word, apply_inter_letter_groups_diff_to_word(word, test_code))
