import os
import sys
from unittest import mock

sys.path.append(os.getcwd())
from highfleet_decoder import generate_suggestions, get_potential_targets, process_text, suggest


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
