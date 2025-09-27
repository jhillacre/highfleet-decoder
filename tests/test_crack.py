import os
import sys

sys.path.append(os.getcwd())

from src.crack import (
    add_tuples_in_base,
    custom_chr,
    custom_ord,
    get_first_of_diffs_or_none,
    identical_inter_letter_groups_diff,
    inter_letter_groups_diff,
    intra_letter_groups_diff,
    make_letter_groups,
    normalize_inter_letter_groups_diff,
    normalize_intra_letter_groups_diff,
    rotate_tuple,
    subtract_tuples_in_base,
)


def test_custom_ord():
    expected = {
        "A": 0,
        "Z": 25,
        "0": 26,
        "9": 35,
        "a": ValueError,
        "z": ValueError,
        "!": ValueError,
        ")": ValueError,
        "AA": TypeError,
        "15": TypeError,
    }
    for char, value in expected.items():
        if isinstance(value, type) and issubclass(value, Exception):
            try:
                custom_ord(char)
            except value:
                pass
            else:
                assert False, f"custom_ord({char}) should have raised {value}"
        else:
            assert custom_ord(char) == value, f"custom_ord({char}) should have returned {value}"


def test_custom_chr():
    expected = {
        0: "A",
        25: "Z",
        26: "0",
        35: "9",
        36: ValueError,
        -1: ValueError,
        "A": TypeError,
        "15": TypeError,
    }
    for value, char in expected.items():
        if isinstance(char, type) and issubclass(char, Exception):
            try:
                custom_chr(value)
            except char:
                pass
            else:
                assert False, f"custom_chr({value}) should have raised {char}"
        else:
            assert custom_chr(value) == char, f"custom_chr({value}) should have returned {char}"


def test_make_letter_groups():
    expected = {
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789": (
            ("A", "E", "I", "M", "Q", "U", "Y", "2", "6"),
            ("B", "F", "J", "N", "R", "V", "Z", "3", "7"),
            ("C", "G", "K", "O", "S", "W", "0", "4", "8"),
            ("D", "H", "L", "P", "T", "X", "1", "5", "9"),
        ),
        "AAAAAAAAAAAAAA": (
            (
                "A",
                "A",
                "A",
                "A",
            ),
            (
                "A",
                "A",
                "A",
                "A",
            ),
            (
                "A",
                "A",
                "A",
            ),
            (
                "A",
                "A",
                "A",
            ),
        ),
        "MACHINERY": (
            (
                "M",
                "I",
                "Y",
            ),
            (
                "A",
                "N",
            ),
            (
                "C",
                "E",
            ),
            (
                "H",
                "R",
            ),
        ),
        "WEST": (
            ("W",),
            ("E",),
            ("S",),
            ("T",),
        ),
        "GO": (
            ("G",),
            ("O",),
            (),
            (),
        ),
    }
    for chars, expected_groups in expected.items():
        groups = make_letter_groups(chars)
        assert groups == expected_groups, f"make_letter_groups({chars}) should have returned {expected_groups}"


def test_intra_letter_groups_diff():
    expected = [
        [
            (
                ("A", "E", "I", "M", "Q", "U", "Y", "2", "6"),
                ("B", "F", "J", "N", "R", "V", "Z", "3", "7"),
                ("C", "G", "K", "O", "S", "W", "0", "4", "8"),
                ("D", "H", "L", "P", "T", "X", "1", "5", "9"),
            ),
            (
                (-4, -4, -4, -4, -4, -4, -4, -4),
                (-4, -4, -4, -4, -4, -4, -4, -4),
                (-4, -4, -4, -4, -4, -4, -4, -4),
                (-4, -4, -4, -4, -4, -4, -4, -4),
            ),
        ],
        [
            (
                (
                    "A",
                    "A",
                    "A",
                    "A",
                ),
                (
                    "A",
                    "A",
                    "A",
                    "A",
                ),
                (
                    "A",
                    "A",
                    "A",
                ),
                (
                    "A",
                    "A",
                    "A",
                ),
            ),
            (
                (
                    0,
                    0,
                    0,
                ),
                (
                    0,
                    0,
                    0,
                ),
                (
                    0,
                    0,
                ),
                (
                    0,
                    0,
                ),
            ),
        ],
        [
            (
                ("W",),
                ("E",),
                ("S",),
                ("T",),
            ),
            (
                (),
                (),
                (),
                (),
            ),
        ],
        [
            (
                ("G",),
                ("O",),
                (),
                (),
            ),
            (
                (),
                (),
                (),
                (),
            ),
        ],
    ]
    for groups, expected_diff in expected:
        diff = intra_letter_groups_diff(groups)
        assert diff == expected_diff, f"intra_letter_groups_diff({groups}) should have returned {expected_diff}"


def test_inter_letter_groups_diff():
    expected = (
        (
            (
                (
                    "M",
                    "I",
                    "Y",
                ),
                (
                    "A",
                    "N",
                ),
                (
                    "C",
                    "E",
                ),
                (
                    "H",
                    "R",
                ),
            ),
            (
                (
                    "O",
                    "K",
                    "0",
                ),
                (
                    "C",
                    "P",
                ),
                (
                    "E",
                    "G",
                ),
                (
                    "J",
                    "T",
                ),
            ),
            (
                (-2, -2, -2),
                (-2, -2),
                (-2, -2),
                (-2, -2),
            ),
        ),
    )
    for first_groups, second_groups, expected_diff in expected:
        diff = inter_letter_groups_diff(first_groups, second_groups)
        assert diff == expected_diff, (
            f"inter_letter_groups_diff({first_groups}, {second_groups}) should have returned {expected_diff}"
        )


def test_identical_inter_letter_groups_diff():
    expected = (
        (
            (
                (
                    "M",
                    "I",
                    "Y",
                ),
                (
                    "A",
                    "N",
                ),
                (
                    "C",
                    "E",
                ),
                (
                    "H",
                    "R",
                ),
            ),
            (
                (
                    "O",
                    "K",
                    "0",
                ),
                (
                    "C",
                    "P",
                ),
                (
                    "E",
                    "G",
                ),
                (
                    "J",
                    "T",
                ),
            ),
            (
                -2,
                -2,
                -2,
                -2,
            ),
        ),
    )
    for first_groups, second_groups, expected_diff in expected:
        diff = identical_inter_letter_groups_diff(first_groups, second_groups)
        assert diff == expected_diff, (
            f"identical_inter_letter_groups_diff({first_groups}, {second_groups}) should have returned {expected_diff}"
        )


def test_add_tuples_in_base():
    expected = (
        (
            (1, 2, 3),
            (4, 5, 6),
            (5, 7, 9),
        ),
        (
            (1, 1, 1, 1),
            (1, 1, 1, 1),
            (2, 2, 2, 2),
        ),
    )
    for first_tuple, second_tuple, expected_tuple in expected:
        assert add_tuples_in_base(first_tuple, second_tuple) == expected_tuple, (
            f"add_tuples_in_base({first_tuple}, {second_tuple}) should have returned {expected_tuple}"
        )


def test_subtract_tuples_in_base():
    expected = (
        (
            (5, 7, 9),
            (4, 5, 6),
            (1, 2, 3),
        ),
        (
            (2, 2, 2, 2),
            (1, 1, 1, 1),
            (1, 1, 1, 1),
        ),
    )
    for first_tuple, second_tuple, expected_tuple in expected:
        assert subtract_tuples_in_base(first_tuple, second_tuple) == expected_tuple, (
            f"subtract_tuples_in_base({first_tuple}, {second_tuple}) should have returned {expected_tuple}"
        )


def test_rotate_tuple():
    expected = (
        (
            (1, 2, 3),
            -3,
            (1, 2, 3),
        ),
        (
            (1, 2, 3),
            -2,
            (2, 3, 1),
        ),
        (
            (1, 2, 3),
            -1,
            (3, 1, 2),
        ),
        (
            (1, 2, 3),
            0,
            (1, 2, 3),
        ),
        (
            (1, 2, 3),
            1,
            (2, 3, 1),
        ),
        (
            (1, 2, 3),
            2,
            (3, 1, 2),
        ),
        (
            (1, 2, 3),
            3,
            (1, 2, 3),
        ),
    )
    for tuple, rotate, expected_tuple in expected:
        assert rotate_tuple(tuple, rotate) == expected_tuple, (
            f"rotate_tuple({tuple}, {rotate}) should have returned {expected_tuple}"
        )


def test_get_first_of_diffs_or_none():
    expected = (
        (
            (
                (-4, -4, -4, -4, -4, -4, -4, -4),
                (-4, -4, -4, -4, -4, -4, -4, -4),
                (-4, -4, -4, -4, -4, -4, -4, -4),
                (-4, -4, -4, -4, -4, -4, -4, -4),
            ),
            (-4, -4, -4, -4),
        ),
        (
            (
                (1, 2, 3),
                (4, 5, 6),
                (5, 7, 9),
            ),
            (1, 4, 5),
        ),
        (
            (
                (1, 2, 3),
                (),
                (),
            ),
            (1, None, None),
        ),
        (
            (
                (),
                (),
                (),
            ),
            (None, None, None),
        ),
    )
    for diffs, expected_diff in expected:
        assert get_first_of_diffs_or_none(diffs) == expected_diff, (
            f"get_first_of_diffs_or_none({diffs}) should have returned {expected_diff}"
        )


def test_normalize_intra_letter_groups_diff():
    expected = (
        (
            ((-17, -16), (-15, -14)),
            ((19, 20), (21, 22)),
        ),
    )
    for diff, expected_diff in expected:
        assert normalize_intra_letter_groups_diff(diff) == expected_diff, (
            f"normalize_intra_letter_groups_diff({diff}) should have returned {expected_diff}"
        )


def test_normalize_inter_letter_groups_diff():
    expected = (
        (
            (-17, -16),
            (19, 20),
        ),
    )
    for diff, expected_diff in expected:
        assert normalize_inter_letter_groups_diff(diff) == expected_diff, (
            f"normalize_inter_letter_groups_diff({diff}) should have returned {expected_diff}"
        )
