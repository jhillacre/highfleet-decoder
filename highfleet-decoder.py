import shutil
import string
import textwrap
from operator import itemgetter
from typing import Optional, Sequence

from src.globals import GROUP_COUNT
from src.message import Message
from src.support import AppendOnlyFileBackedSet, JSONBackedDict


class Main:
    dictionary_words: set[str]
    seen_messages: set[str]
    receiver_frequency: dict[str, int]
    sender_frequency: dict[str, int]
    word_frequency: dict[str, int]

    def __init__(self):
        self.dictionary_words: set[str] = AppendOnlyFileBackedSet(
            "words_alpha.txt", "dictionary words", " words", upper_case=True
        )
        self.seen_messages: set[str] = AppendOnlyFileBackedSet(
            "seen_messages.txt", "seen messages", " messages", is_json=True
        )
        self.receiver_frequency: dict[str, int] = JSONBackedDict(
            "receiver_frequency.json", "receiver frequency", " receivers"
        )
        self.sender_frequency: dict[str, int] = JSONBackedDict("sender_frequency.json", "sender frequency", " senders")
        self.word_frequency: dict[str, int] = JSONBackedDict("word_frequency.json", "word frequency", " words")
        self.dictionary_words.load()
        self.seen_messages.load()
        self.receiver_frequency.load()
        self.sender_frequency.load()
        self.word_frequency.load()

    def is_clear_text(self, words: Sequence) -> bool:
        # is this clear text or cipher text?
        # if a good part of words are in the dictionary or are numbers, it's clear text
        clear_words = 0
        # get the receiver and sender without the equals sign
        for word in words:
            if word and word in self.dictionary_words or word.isdigit():
                clear_words += 1
        if clear_words > len(words) / 4:
            return True
        return False

    def handle_clear_text(self, message: Message):
        self.seen_messages.add(message.text)
        for word in message.body:
            self.word_frequency[word] = self.word_frequency.get(word, 0) + 1
        if message.receiver:
            self.receiver_frequency[message.receiver] = self.receiver_frequency.get(message.receiver, 0) + 1
        if message.sender:
            self.sender_frequency[message.sender] = self.sender_frequency.get(message.sender, 0) + 1

    @staticmethod
    def get_potential_targets(word: str, frequency: dict[str, int]) -> list[str]:
        return map(
            itemgetter(0),
            reversed(
                sorted(
                    [(word, frequency) for word, frequency in frequency.items() if len(word) == len(word)],
                    key=itemgetter(1),
                )
            ),
        )

    @staticmethod
    def custom_ord(char: str) -> int:
        # custom ord function that puts does uppercase letters then numbers (0-35)
        if char.isupper():
            return ord(char) - 64
        if char.isdigit():
            return int(char) + 26
        raise ValueError(f"Invalid char {char}")

    @staticmethod
    def custom_chr(ord: int) -> str:
        # custom chr function that puts does uppercase letters then numbers (0-35)
        if ord < 27:
            return chr(ord + 64)
        if ord < 36:
            return str(ord - 26)
        raise ValueError(f"Invalid ord {ord}")

    @staticmethod
    def make_groups(word: str) -> tuple[tuple[str]]:
        # divide letters in groups of GROUP_COUNT, via round robin
        return tuple(tuple(word[i::GROUP_COUNT]) for i in range(GROUP_COUNT))

    @staticmethod
    def make_diffs(groups: tuple[tuple[str]]) -> tuple[tuple[int]]:
        # get the pattern of differences between character in a group, using custom ord
        return tuple(
            tuple(Main.custom_ord(x) - Main.custom_ord(y) for x, y in zip(group, group[1:])) for group in groups
        )

    @staticmethod
    def code_diff_from_groups_with_same_diff(
        target_groups: tuple[tuple[str]], source_groups: tuple[tuple[str]]
    ) -> tuple[int]:
        # these groups have the same differences, so return the amount of shifts needed to get from source to target, once for each group
        # if the word isn't long enough return a partial code
        return tuple(
            Main.custom_ord(source_group[0]) - Main.custom_ord(target_group[0])
            for target_group, source_group in zip(target_groups, source_groups)
            if target_group and source_group
        )

    def handle_potential_match(
        self,
        source_type: str,
        source_word: str,
        target_word: str,
        code_diff: Sequence[int],
    ) -> Optional[bool]:
        print(
            f"We think {source_type} {source_word!r} is {target_word!r}, using a code difference of {' '.join(str(x) for x in code_diff)}."
        )
        if len(code_diff) < GROUP_COUNT:
            print("This is a partial code, which may help manual decryption.")
        if source_type == "the receiver":
            print("The order should be correct and the position should be correct.")
        else:
            print("The order should be correct, but the position may be wrong.")
        while True:
            print("What nob is the first letter of the target word on? (1,2,3,4)")
            nob = input()
            if nob not in "1234":
                print("Invalid input, please try again.")
                continue
            break
        # rotate the code_diff so the nob number is the first element
        code_diff = code_diff[-int(nob) + 1 :] + code_diff[: -int(nob) + 1]
        while True:
            print("What is the value of that nob? (0-35)")
            value = input()
            if not value.isdigit() or int(value) > 35:
                print("Invalid input, please try again.")
                continue
            value = int(value)
            break
        # using the value of the nob, turn the code_diff into a code
        code = tuple((x + value) % 36 for x in code_diff)
        print(f"The code is {' '.join(str(x) for x in code)}.")
        print(f"Keep looking at matches? (Y/n)")
        if input().lower() == "n":
            return True

    @staticmethod
    def get_clear_text_translator(code: Sequence[int], target_letter: str, source_letter: str) -> str:
        # get the clear text translator for a single letter, using custom ord & custom chr
        digits = string.ascii_uppercase + string.digits
        # rotate the soruce digits so the target letter is at the start
        source_digits = digits[digits.index(target_letter) :] + digits[: digits.index(target_letter)]
        # rotate the target digits so the target letter is at the start
        target_digits = digits[digits.index(target_letter) :] + digits[: digits.index(target_letter)]
        return str.maketrans(source_digits, target_digits)

    def handle_receiver_decoding(self, message: Message) -> Optional[bool]:
        # we can help decipher the receiver quite a bit, since we know there are no gaps in the sequence of rotations
        # find receiver words that match the length of the cipher receiver, sorted by most frequent first
        potential_receivers = self.get_potential_targets(message.receiver, self.receiver_frequency)
        # the pattern of differences between characters in a group must be the same for all groups to match a target word
        reciever_groups = self.make_groups(message.receiver)
        receiver_diffs = self.make_diffs(reciever_groups)
        for potential_receiver in potential_receivers:
            potential_receiver_groups = self.make_groups(potential_receiver)
            potential_receiver_diffs = self.make_diffs(potential_receiver_groups)
            if receiver_diffs == potential_receiver_diffs:
                code_diff = self.code_diff_from_groups_with_same_diff(potential_receiver_groups, reciever_groups)
                # we can only show the user the source word and target word, since we don't know the position of the code between words.
                if self.handle_potential_match("the receiver", message.receiver, potential_receiver, code_diff):
                    return True

    def handle_sender_decoding(self, message: Message) -> Optional[bool]:
        # the sender is a bit harder to decode, since we don't know where the code starts
        # find sender words that match the length of the cipher sender, sorted by most frequent first
        potential_senders = self.get_potential_targets(message.sender, self.sender_frequency)
        # the pattern of differences between characters in a group must be the same for all groups to match a target word
        sender_groups = self.make_groups(message.sender)
        sender_diffs = self.make_diffs(sender_groups)
        for potential_sender in potential_senders:
            potential_sender_groups = self.make_groups(potential_sender)
            potential_sender_diffs = self.make_diffs(potential_sender_groups)
            if sender_diffs == potential_sender_diffs:
                code_diff = self.code_diff_from_groups_with_same_diff(potential_sender_groups, sender_groups)
                # we can only show the user the source word and target word, since we don't know the position of the code between words.
                if self.handle_potential_match("the sender", message.sender, potential_sender, code_diff):
                    return True

    def handle_body_decoding(self, message: Message) -> Optional[bool]:
        # similar to the sender, but we have a list of words to find targets for.
        # we should check words largest to smallest, since the larger words should produce less false positives (less calls to is_clear_text)

        # check the bigest words first, since they are more likely to get a full code
        sorted_body_words = sorted(message.body, key=len, reverse=True)
        for body_word in sorted_body_words:
            potential_body_words = self.get_potential_targets(body_word, self.word_frequency)
            # the pattern of differences between characters in a group must be the same for all groups to match a target word
            body_word_groups = self.make_groups(body_word)
            body_word_diffs = self.make_diffs(body_word_groups)
            for potential_body_word in potential_body_words:
                potential_body_word_groups = self.make_groups(potential_body_word)
                potential_body_word_diffs = self.make_diffs(potential_body_word_groups)
                if body_word_diffs == potential_body_word_diffs:
                    code_diff = self.code_diff_from_groups_with_same_diff(potential_body_word_groups, body_word_groups)
                    # we can only show the user the source word and target word, since we don't know the position of the code between words.
                    if self.handle_potential_match("a body word", body_word, potential_body_word, code_diff):
                        return True

    def handle_cipher_text(self, message: Message):
        if (
            message.receiver
            and self.handle_receiver_decoding(message)
            or message.sender
            and self.handle_sender_decoding(message)
            or message.body
            and self.handle_body_decoding(message)
        ):
            # only add seen cipher text if we found a match, so the user can try again with more information
            print("Adding cipher message to seen message, you should get a screen of the clear text.")
            self.seen_messages.add(message.text)
            return
        print("We couldn't find a match for the captured cipher text.")
        print(f"The captured cipher text was:\n{message.text}")

    def handle_message_seems_off(self, message: Message) -> Optional[bool]:
        if not message.receiver and not message.sender:
            print("Captured text doesn't have a receiver or sender.")
            print("Is this text a message? (y/N)")
            print(f"The captured text is:\n{message.corrected_text}")
            if input() != "y":
                return True

    def handle_confirm_message(self, message: Message):
        # sometimes the ocr is just bad, so we should confirm all words
        # todo: we should be able to clean up ORC a bit using the frequency of words and levenstein distance, or at least make suggestions
        # todo: we don't want to store coordinates in the message, since there can be alot of unique values.
        while True:
            print("Please confirm the following words are correct:")
            words_selection_text = " ".join(f"{i}:{word}" for i, word in enumerate(message.corrected_words) if word)
            console_width = min(shutil.get_terminal_size().columns, 100)
            print(textwrap.fill(words_selection_text, width=console_width))
            print("Enter a word that you want to correct or remove, or blank to continue.")
            word_index = input()
            if not word_index:
                break
            try:
                word_index = int(word_index)
            except ValueError:
                print("Please enter a number.")
                continue
            if word_index < 0 or word_index > len(message.corrected_words):
                print("Please enter a number between 0 and the number of words.")
                continue
            word = message.corrected_words[word_index]
            if not word:
                print("Cannot update removed words, we don't know where to find them in the text.")
                continue
            new_word = message.handle_replacement_word(word)
            message.update_corrected_word(word_index, new_word)

    def main(self):
        while True:
            # wait for the user to tell us there is new cipher text or clear text, or if they want to quit
            print("Enter q to quit or anything else to grab a new image.")
            if input() == "q":
                break
            message = Message()
            if not message.text:
                print("We couldn't find any text in the image.")
                continue
            print("\n\t".join(message.text.split("\n")))
            if message.text in self.seen_messages:
                print("This message has already been seen.")
                continue
            # todo: validate the case were we capture text doesn't seem like a message
            self.handle_confirm_message(message)
            if self.handle_message_seems_off(message):
                continue
            if self.is_clear_text(message.body):
                print("This message is clear text.")
                print("Confirm? (Y/n)")
                if input() == "n":
                    continue
                self.handle_clear_text(message)
            else:
                print("This message seems like cipher text.")
                print("Confirm? (Y/n)")
                if input() == "n":
                    continue
                self.handle_cipher_text(message)
            self.receiver_frequency.save()
            self.sender_frequency.save()
            self.word_frequency.save()
            self.seen_messages.save()


if __name__ == "__main__":
    Main().main()
