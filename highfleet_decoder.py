import sys
from collections.abc import Sequence
from operator import itemgetter

import inflect

from src.cli import ERROR_COLOR, ask, edit_lines
from src.crack import (
    add_tuples_in_base,
    identical_inter_letter_groups_diff,
    intra_letter_groups_diff,
    make_letter_groups,
    normalize_inter_letter_groups_diff,
    normalize_intra_letter_groups_diff,
    rotate_tuple,
)
from src.globals import BBOX
from src.support import AppendOnlyFileBackedSet, JSONBackedDict


def is_clear_text(words: list[str], dictionary_words: AppendOnlyFileBackedSet) -> bool:
    """
    Determine if the message is clear text or cipher text, by checking if a good part of words are in the dictionary or are numbers
    """
    clear_words = 0
    # get the receiver and sender without the equals sign
    for word in words:
        if word and word in dictionary_words or word.isdigit():
            clear_words += 1
    if clear_words > len(words) / 4:
        return True
    return False


def ask_if_clear(words: list[str], dictionary_words: AppendOnlyFileBackedSet) -> bool:
    """
    Ask the user if the message is clear text or cipher text
    """
    think_clear_text = is_clear_text(words, dictionary_words)
    if think_clear_text:
        print("This message is clear text.")
    else:
        print("This message seems like cipher text.")
    return think_clear_text if ask("Confirm? (Y/n)", choices=["y", "n"], default="y") == "y" else not think_clear_text


inflect_engine = inflect.engine()


def ask_knobs() -> list[int]:
    """
    Ask the user for the current knob positions
    """
    knobs = [0, 0, 0, 0]
    while True:
        for index, knob in enumerate(knobs):
            while True:
                knob_label = inflect_engine.ordinal(index + 1)
                knob = ask(f"What is the value of the {knob_label} knob?[0-35]")
                if knob.isdigit() and 0 <= int(knob) <= 35:
                    knobs[index] = int(knob)
                    break
                else:
                    print(ERROR_COLOR(f"Invalid choice: {knob!r}"), file=sys.stderr)
                    continue
        confirm_knobs = ask(f"Confirm knobs are correct? {knobs}", choices=["y", "n"], default="y")
        if confirm_knobs == "y":
            break
    return knobs


def get_potential_targets(word: str, frequency: dict[str, int]) -> list[str]:
    """
    Get the potential targets for a word, sorted by most frequent first
    """
    items = [(target_word, freq) for target_word, freq in frequency.items() if len(word) == len(target_word)]
    sorted_items = sorted(items, key=itemgetter(1), reverse=True)
    return [word for word, _ in sorted_items]


def suggest(
    source_type: str, source_word: str, target_word: str, code_diff: Sequence[int], original_knobs: Sequence[int]
):
    """ """
    # we don't know the knob corresponding to the first letter of the word
    first_knob = ask(
        f"Original knobs: {'-'.join([str(x) for x in original_knobs])}. Which knob corresponds to the first letter of {source_type}({source_word})?",
        choices=["1", "2", "3", "4"],
        default="1",
    )
    # rotate the code_diff so the knob number is the first element
    rotated_code_diff = rotate_tuple(code_diff, int(first_knob) - 1)
    knobs = rotate_tuple(original_knobs, int(first_knob) - 1)
    desired_knobs = add_tuples_in_base(knobs, rotated_code_diff)
    print(f"We think {source_type} {source_word!r} is {target_word!r}, using a code difference of {code_diff!r}.")
    print(f"Therefore, we think the code is {'-'.join(str(x) for x in desired_knobs)}.")


def generate_suggestions(receiver_frequency, sender_frequency, word_frequency, words, corrected_text, sender, receiver):
    original_knobs = ask_knobs()
    keep_going = "y"
    for [target_words, frequency, source] in [
        [[receiver], receiver_frequency, "the receiver"],
        [[sender], sender_frequency, "the sender"],
        [words, word_frequency, "the word"],
    ]:
        for word in target_words:
            if not word:
                # receiver or sender can be None if no words looked like a receiver or sender
                continue
            potential_targets = get_potential_targets(word, frequency)
            groups = make_letter_groups(word)
            diff = normalize_intra_letter_groups_diff(intra_letter_groups_diff(groups))
            for potential_target in potential_targets:
                potential_groups = make_letter_groups(potential_target)
                potential_diff = normalize_intra_letter_groups_diff(intra_letter_groups_diff(potential_groups))
                if potential_diff == diff:
                    inter_diff = normalize_inter_letter_groups_diff(
                        identical_inter_letter_groups_diff(
                            groups,
                            potential_groups,
                        )
                    )
                    suggest(source, word, potential_target, inter_diff, original_knobs)
                    keep_going = ask("Continue generating suggestions?", choices=["y", "n"], default="y")
                if keep_going == "n":
                    break
            if keep_going == "n":
                break
        if keep_going == "n":
            break
    else:
        print("We couldn't find a match for the captured cipher text.")
        print(f"The captured cipher text was:\n{corrected_text}")


def process_text(text: str) -> tuple[str | None, str | None, list[str]]:
    """
    Process the text to get the receiver, sender, and words
    """
    # replace all non-alphanumeric characters with spaces, sans the equals sign
    processed_text = "".join(char if char.isalnum() or char == "=" else " " for char in text)
    words = processed_text.split()
    receiver_token = next((word for word in words if word.endswith("=")), None)
    sender_token = next((word for word in reversed(words) if word.startswith("=")), None)
    
    # Remove tokens from words list safely
    filtered_words = []
    for word in words:
        if word != receiver_token and word != sender_token:
            filtered_words.append(word)
    
    # Extract the actual receiver/sender without = signs
    receiver = receiver_token[:-1] if receiver_token else None
    sender = sender_token[1:] if sender_token else None
    
    filtered_words.sort(key=len, reverse=True)
    return receiver, sender, filtered_words


def main():
    """
    Main Program
    - Handles the user interface and flow of the program
    - Coordinates the interaction between the other modules

    Overall flow:
    - Wait for any key to capture a message
    - Help the user confirm the message is correct
    - Determine if the message is clear text or cipher text
    - If clear text, record the message then go back to waiting for a message
    - If cipher text, ask for the current the current knobs and start generating suggestions
    - Repeat generating suggestions until the user says they have the clear text
    - If the user is done generating suggestions, then go back to waiting for a message
    (The user records the clear text by hitting any key when the clear text is on the screen)
    """
    import pytesseract
    from PIL import ImageGrab

    dictionary_words = AppendOnlyFileBackedSet("words_alpha.txt", "dictionary words", " words", upper_case=True)
    receiver_frequency = JSONBackedDict("receiver_frequency.json", "receiver frequency", " receivers")
    sender_frequency = JSONBackedDict("sender_frequency.json", "sender frequency", " senders")
    word_frequency = JSONBackedDict("word_frequency.json", "word frequency", " words")
    dictionary_words.load()
    receiver_frequency.load()
    sender_frequency.load()
    word_frequency.load()

    while True:
        pressed = ask("Press q to quit or any other key to capture a message.", char_input=True)
        if pressed == "q":
            break
        full_screen = ImageGrab.grab(include_layered_windows=True)
        bbox = BBOX
        bbox = (
            int(bbox[0] * full_screen.width / 1920),
            int(bbox[1] * full_screen.height / 1200),
            int(bbox[2] * full_screen.width / 1920),
            int(bbox[3] * full_screen.height / 1200),
        )
        image = ImageGrab.grab(bbox=bbox, include_layered_windows=True).convert("L")
        text = pytesseract.image_to_string(image)
        print("Please correct the text, pressing ESC to continue.")
        corrected_text = edit_lines(text)
        receiver, sender, words = process_text(corrected_text)
        message_is_clear = ask_if_clear(words, dictionary_words)
        if message_is_clear:
            if receiver:
                receiver_frequency[receiver] = receiver_frequency.get(receiver, 0) + 1
            if sender:
                sender_frequency[sender] = sender_frequency.get(sender, 0) + 1
            for word in words:
                word_frequency[word] = word_frequency.get(word, 0) + 1
            receiver_frequency.save()
            sender_frequency.save()
            word_frequency.save()
        else:
            generate_suggestions(
                receiver_frequency, sender_frequency, word_frequency, words, corrected_text, sender, receiver
            )


if __name__ == "__main__":
    main()
