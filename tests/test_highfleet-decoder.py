import os
import sys
from unittest import mock

sys.path.append(os.getcwd())
from highfleet_decoder import generate_suggestions, get_potential_targets, is_clear_text, ordinal, process_text, suggest
from src.support import AppendOnlyFileBackedSet


def test_get_potential_targets() -> None:
    test_frequency = {
        "NORTH": 6,
        "SOUTH": 5,
        "EAST": 4,
        "WEST": 4,
        "GO": 3,
        "STOP": 3,
        "HEAVY": 2,
        "CARGO": 2,
        "PLEASE": 2,
        "OBTAIN": 1,
        "BRASS": 1,
        "GOING": 1,
        "MACHINERY": 1,
    }
    expected = [
        [
            "WEST",
            ["EAST", "WEST", "STOP"],
        ],
        ["AAAAA", ["NORTH", "SOUTH", "HEAVY", "CARGO", "BRASS", "GOING"]],
        [
            "AAAAAA",
            ["PLEASE", "OBTAIN"],
        ],
        ["AAAAAAAAA", ["MACHINERY"]],
    ]
    for word, expected_targets in expected:
        targets = list(get_potential_targets(word, test_frequency))
        assert targets == expected_targets, f"get_potential_targets({word}) should have returned {expected_targets}"


def test_suggest() -> None:
    expected = [
        [
            "1",
            (
                "the source type",  # source type
                "URASB",  # source word
                "BRASS",  # target word
                (19, 0, 0, 0),  # code diff
                [2, 4, 8, 16],  # original knobs
            ),
            [
                "We think the source type 'URASB' is 'BRASS', using a code difference of (19, 0, 0, 0).",
                "Therefore, we think the code is 21-4-8-16.",
            ],
        ],
        [
            "2",
            (
                "another source type",  # source type
                "VIHFRVJP7",  # source word
                "MACHINERY",  # target word
                (9, 8, 5, -2),  # code diff
                [2, 4, 8, 16],  # original knobs
            ),
            [
                "We think another source type 'VIHFRVJP7' is 'MACHINERY', using a code difference of (9, 8, 5, -2).",
                "Therefore, we think the code is 12-13-14-11.",
            ],
        ],
    ]
    for case, (
        ask_side_effect,
        (source_type, source_word, target_word, code_diff, original_knobs),
        expected_suggestion,
    ) in enumerate(expected):
        with mock.patch("highfleet_decoder.print") as mock_print:
            with mock.patch("highfleet_decoder.ask") as mock_ask:
                mock_ask.side_effect = ask_side_effect
                suggest(source_type, source_word, target_word, code_diff, original_knobs)
                assert mock_ask.call_count == 1, f"suggest() should have called ask() once for case {case}"
                assert mock_print.call_count == 2, f"suggest() should have called print() twice for case {case}"
                assert mock_print.call_args_list[0][0][0] == expected_suggestion[0], (
                    f"suggest() should have printed first line of suggestion for case {case}"
                )
                assert mock_print.call_args_list[1][0][0] == expected_suggestion[1], (
                    f"suggest() should have printed second line of suggestion for case {case}"
                )


def test_generate_suggestions() -> None:
    expected = [
        [
            [
                # receiver_frequency
                {
                    "ALPHA": 1,
                    "BRAVO": 1,
                    "CHARLIE": 1,
                    "DELTA": 1,
                    "ECHO": 1,
                    "FOXTROT": 1,
                },
                # sender_frequency
                {
                    "QUEBEC": 1,
                    "ROMEO": 1,
                    "SIERRA": 1,
                    "TANGO": 1,
                    "UNIFORM": 1,
                    "VICTOR": 1,
                },
                # word_frequency
                {
                    "NORTH": 6,
                    "SOUTH": 5,
                    "EAST": 4,
                    "WEST": 4,
                    "GO": 3,
                    "STOP": 3,
                    "HEAVY": 2,
                    "CARGO": 2,
                    "PLEASE": 2,
                    "OBTAIN": 1,
                    "BRASS": 1,
                    "GOING": 1,
                    "MACHINERY": 1,
                },
                # words, pre-sorted longest to shortest
                ["OEKXKRM70", "RPMQUI", "QF1QKR", "ISQ31", "PSZ9J", "EEZWQ", "JIIB0", "DVI8U", "YI09"],
                # corrected_text
                # "BRAVO=\nGOING NORTH WEST CARGO HEAVY MACHINERY PLEASE OBTAIN BRASS\n=TANGO"
                "DVIBQ=\nISQ31 PSZ9J YI09 EEZWQ JIIB0 OEKXKRM70 RPMQUI QF1QKR DVI8U\n=VEVWQ",
                # sender
                "VEVWQ",
                # receiver
                "DVIBQ",
            ],
            [
                # ask_knobs_side_effect
                [3, 6, 9, 12],
                # ask_side_effects
                ["1", "y", "2", "y", "3", "y", "4", "n"],
                # ask_calls
                [
                    mock.call(
                        "Original knobs: 3-6-9-12. Which knob corresponds to the first letter of the receiver(DVIBQ)?",
                        choices=["1", "2", "3", "4"],
                        default="1",
                    ),
                    mock.call("Continue generating suggestions?", choices=["y", "n"], default="y"),
                    mock.call(
                        "Original knobs: 3-6-9-12. Which knob corresponds to the first letter of the sender(VEVWQ)?",
                        choices=["1", "2", "3", "4"],
                        default="1",
                    ),
                    mock.call("Continue generating suggestions?", choices=["y", "n"], default="y"),
                    mock.call(
                        "Original knobs: 3-6-9-12. Which knob corresponds to the first letter of the word(OEKXKRM70)?",
                        choices=["1", "2", "3", "4"],
                        default="1",
                    ),
                    mock.call("Continue generating suggestions?", choices=["y", "n"], default="y"),
                    mock.call(
                        "Original knobs: 3-6-9-12. Which knob corresponds to the first letter of the word(RPMQUI)?",
                        choices=["1", "2", "3", "4"],
                        default="1",
                    ),
                    mock.call("Continue generating suggestions?", choices=["y", "n"], default="y"),
                ],
                # print_calls
                [
                    mock.call("We think the receiver 'DVIBQ' is 'BRAVO', using a code difference of (2, 4, 8, 16)."),
                    mock.call("Therefore, we think the code is 5-10-17-28."),
                    mock.call("We think the sender 'VEVWQ' is 'TANGO', using a code difference of (2, 4, 8, 16)."),
                    mock.call("Therefore, we think the code is 10-17-28-5."),
                    mock.call(
                        "We think the word 'OEKXKRM70' is 'MACHINERY', using a code difference of (2, 4, 8, 16)."
                    ),
                    mock.call("Therefore, we think the code is 17-28-5-10."),
                    mock.call("We think the word 'RPMQUI' is 'PLEASE', using a code difference of (2, 4, 8, 16)."),
                    mock.call("Therefore, we think the code is 28-5-10-17."),
                ],
            ],
        ],
        [
            [
                {},
                {},
                {},
                ["CYPHERTEXT", "DUMMY"],
                "DUMMY CYPHERTEXT",
                None,
                None,
            ],
            [
                [1, 2, 3, 4],
                [],
                [],
                [
                    mock.call("We couldn't find a match for the captured cipher text."),
                    mock.call("The captured cipher text was:\nDUMMY CYPHERTEXT"),
                ],
            ],
        ],
    ]
    for case, [
        [receiver_frequency, sender_frequency, word_frequency, words, corrected_text, sender, receiver],
        [ask_knobs_side_effect, ask_side_effects, ask_calls, print_calls],
    ] in enumerate(expected):
        with mock.patch("highfleet_decoder.print") as mock_print:
            with mock.patch("highfleet_decoder.ask") as mock_ask:
                mock_ask.side_effect = ask_side_effects
                with mock.patch("highfleet_decoder.ask_knobs") as mock_ask_knobs:
                    mock_ask_knobs.side_effect = [ask_knobs_side_effect]
                    generate_suggestions(
                        receiver_frequency, sender_frequency, word_frequency, words, corrected_text, sender, receiver
                    )
                    assert mock_ask_knobs.call_count == 1, (
                        f"generate_suggestions() should have called ask_knobs() once for case {case}"
                    )
                    assert mock_ask.call_count == len(ask_side_effects), (
                        f"generate_suggestions() should have called ask() {len(ask_side_effects)} times for case {case}"
                    )
                    assert mock_ask_knobs.call_args_list == [[]], (
                        f"generate_suggestions() should have called ask_knobs() with no arguments for case {case}"
                    )
                    assert mock_ask.call_args_list == ask_calls, (
                        f"generate_suggestions() should have called ask() with the correct arguments for case {case}"
                    )
                    assert mock_print.call_count == len(print_calls), (
                        f"generate_suggestions() should have called print() {len(print_calls)} times for case {case}"
                    )
                    assert mock_print.call_args_list == print_calls, (
                        f"generate_suggestions() should have called print() with the correct arguments for case {case}"
                    )


def test_process_text() -> None:
    expected = [
        [
            "DVIBQ=\nISQ31 PSZ9J YI09 EEZWQ JIIB0 OEKXKRM70 RPMQUI QF1QKR DVI8U\n=VEVWQ",
            ("DVIBQ", "VEVWQ", ["OEKXKRM70", "RPMQUI", "QF1QKR", "ISQ31", "PSZ9J", "EEZWQ", "JIIB0", "DVI8U", "YI09"]),
        ]
    ]
    for text, expected_result in expected:
        result = process_text(text)
        assert result == expected_result, f"process_text({text}) should have returned {expected_result}"


def test_process_text_normalizes_numeric_tokens() -> None:
    receiver, sender, words = process_text("REC= SPEED II0 90 =SND")
    assert receiver == "REC"
    assert sender == "SND"
    assert words == ["SPEED", "110", "90"]


def test_process_text_edge_cases() -> None:
    """Test process_text with edge cases: missing sender, receiver, or both."""
    test_cases = [
        # Missing receiver
        ("HELLO WORLD =SENDER", (None, "SENDER", ["HELLO", "WORLD"])),
        # Missing sender
        ("RECEIVER= HELLO WORLD", ("RECEIVER", None, ["HELLO", "WORLD"])),
        # Missing both
        ("HELLO WORLD", (None, None, ["HELLO", "WORLD"])),
        # Empty text
        ("", (None, None, [])),
        # Only sender
        ("=SENDER", (None, "SENDER", [])),
        # Only receiver
        ("RECEIVER=", ("RECEIVER", None, [])),
        # Words with special characters get filtered
        ("REC= HE@LLO WO!RLD =SEN", ("REC", "SEN", ["LLO", "RLD", "HE", "WO"])),
    ]

    for text, expected in test_cases:
        result = process_text(text)
        assert result == expected, f"process_text({text!r}) should return {expected}, got {result}"


def test_is_clear_text() -> None:
    """Test is_clear_text function with various message types."""
    # Create a mock dictionary with common English words
    dictionary = AppendOnlyFileBackedSet("test.txt", "test", "test")
    dictionary.update(
        [
            "THE",
            "AND",
            "TO",
            "OF",
            "A",
            "IN",
            "FOR",
            "IS",
            "ON",
            "THAT",
            "BY",
            "THIS",
            "WITH",
            "I",
            "YOU",
            "IT",
            "NOT",
            "OR",
            "BE",
            "ARE",
            "FROM",
            "AT",
            "AS",
            "YOUR",
            "ALL",
            "ANY",
            "CAN",
            "HAD",
            "HER",
            "WAS",
            "ONE",
            "OUR",
            "OUT",
            "DAY",
            "GET",
            "HAS",
            "HIM",
            "HIS",
            "HOW",
            "ITS",
            "MAY",
            "NEW",
            "NOW",
            "OLD",
            "SEE",
            "TWO",
            "WHO",
            "BOY",
            "DID",
            "HAS",
            "LET",
            "PUT",
            "SAY",
            "SHE",
            "TOO",
            "USE",
        ]
    )

    test_cases = [
        # Clear text - mostly dictionary words
        (["THE", "AND", "TO", "OF"], True),  # 100% dictionary words
        # Clear text - mix of dictionary words and numbers
        (["THE", "AND", "123", "456"], True),  # 50% dict + 50% numbers > 25%
        # Clear text - mostly numbers
        (["123", "456", "789", "000"], True),  # 100% numbers
        # Cipher text - no dictionary words
        (["XYZZY", "PLUGH", "QWERT", "ASDFG"], False),  # 0% dictionary words
        # Cipher text - very few dictionary words (< 25%)
        (["THE", "XYZZY", "PLUGH", "QWERT", "ASDFG"], False),  # 20% < 25%
        # Edge case - exactly 25% dictionary words (should be False)
        (["THE", "XYZZY", "PLUGH", "QWERT"], False),  # 25% = 25%
        # Edge case - just over 25% dictionary words (should be True)
        (["THE", "AND", "XYZZY", "PLUGH"], True),  # 50% > 25%
        # Empty word list
        ([], False),  # 0/0 handled gracefully
        # Single clear word
        (["THE"], True),  # 100% > 25%
        # Single cipher word
        (["XYZZY"], False),  # 0% < 25%
        # Mixed case with empty strings (should be filtered out)
        (["THE", "", "AND", "XYZZY"], True),  # 2/3 ≈ 67% > 25%
    ]

    for words, expected in test_cases:
        result = is_clear_text(words, dictionary)
        assert result == expected, f"is_clear_text({words}) should return {expected}, got {result}"


def test_get_potential_targets_edge_cases() -> None:
    """Test get_potential_targets with edge cases."""
    test_frequency = {
        "ABC": 10,
        "DEF": 5,
        "GHI": 1,
        "LONGER": 20,
    }

    test_cases = [
        # No matches - wrong length
        ("XY", []),
        ("TOOLONG", []),
        # Single match
        ("LONGER", ["LONGER"]),
        # Multiple matches, sorted by frequency
        ("ABC", ["ABC", "DEF", "GHI"]),
    ]

    # Test with normal frequency dict
    for word, expected in test_cases:
        targets = list(get_potential_targets(word, test_frequency))
        assert targets == expected, (
            f"get_potential_targets({word}, test_frequency) should return {expected}, got {targets}"
        )

    # Test with empty frequency dict
    empty_frequency = {}
    targets = list(get_potential_targets("ABC", empty_frequency))
    assert targets == [], f"get_potential_targets with empty frequency should return [], got {targets}"


def test_ordinal() -> None:
    """Test ordinal number conversion helper."""
    test_cases = [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (5, "5th"),
        (11, "11th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (101, "101st"),
    ]

    for number, expected in test_cases:
        result = ordinal(number)
        assert result == expected, f"ordinal({number}) should return {expected}, got {result}"
