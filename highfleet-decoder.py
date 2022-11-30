import bisect
import csv
import json
import re
import shutil
import string
import textwrap
from functools import lru_cache
from operator import itemgetter
from typing import Optional, Sequence

import pytesseract
from PIL import Image, ImageGrab
from tqdm import tqdm

FREQUENCY_FILES = {
    "sender": "sender_frequency.tsv",
    "receiver": "receiver_frequency.tsv",
    "word": "word_frequency.tsv",
}
FREQUENCY_PROPERTIES = {
    "sender": "sender_frequency",
    "receiver": "receiver_frequency",
    "word": "word_frequency",
}

REPLACEMENT_WORD_CACHE = {}
DO_STRETCH = False
GROUP_COUNT = 4  # the amount of nobs in highfleet decryption codes.
ALLOWED_DIGITS = 36  # the amount of digits in the highfleet decryption codes. making this different require a lot more work then just changing this number.


class AppendOnlyFileBackedSet(set):
    def __init__(
        self, filename: str, desc: str, unit: str, is_json: Optional[bool] = None, upper_case: Optional[bool] = None
    ):
        super().__init__()
        self.filename = filename
        self.desc = desc
        self.unit = unit
        self.dirty_items = set()
        self.is_json = is_json
        self.upper_case = upper_case

    def add(self, item):
        super().add(item)
        self.dirty_items.add(item)

    def remove(self, _item):
        raise NotImplementedError("This set is append only")

    def load(self):
        try:
            with open(self.filename, "r") as f:
                for line in tqdm(
                    f.readlines(),
                    desc=f"Loading {self.desc}",
                    unit=self.unit,
                    colour="green",
                    ascii=True,
                ):
                    line = line.strip()
                    if self.is_json:
                        line = json.loads(line)
                    if self.upper_case:
                        line = line.upper()
                    super().add(line)
        except FileNotFoundError:
            # make it for next time.
            with open(self.filename, "w"):
                pass

    def save(self):
        with open(self.filename, "a") as f:
            for item in tqdm(
                self.dirty_items,
                desc=f"Saving {self.desc}",
                unit=self.unit,
                colour="green",
                ascii=True,
            ):
                f.write(f"{json.dumps(item)}\n" if self.is_json else f"{item}\n")
        self.dirty_items = set()


class JSONBackedDict(dict):
    def __init__(self, filename: str, desc: str, unit: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename
        self.desc = desc or "frequency"
        self.unit = unit or " words"

    def load(self):
        try:
            with open(self.filename, "r") as f:
                json_dict = json.loads(f.read())
                self.clear()
                # I just want a cool progress bar
                for key, value in tqdm(
                    json_dict.items(),
                    desc=f"Loading {self.desc}",
                    unit=self.unit,
                    colour="green",
                    ascii=True,
                ):
                    super().__setitem__(key, value)
        except FileNotFoundError:
            # make it for next time.
            with open(self.filename, "w") as f:
                f.write("{}")

    def save(self):
        with open(self.filename, "w") as f:
            json_str = json.dumps(self, indent=4)
            # I just want a cool progress bar
            for line in tqdm(
                json_str.split("\n"),
                desc=f"Saving {self.desc}",
                unit=self.unit,
                colour="green",
                ascii=True,
            ):
                f.write(f"{line}\n")


class Message:
    def __init__(self, text: Optional[str] = None):
        self.ocred = not text
        self._text = text
        self._corrected_text: Optional[str] = None
        self._image: Optional[Image.Image] = None
        self._data: Optional[dict] = None
        self._raw_words: Optional[list[str]] = None
        self._raw_scores: Optional[list[float]] = None
        self._corrected_words: Optional[list[str]] = None
        self._words: Optional[tuple[str]] = None
        self._receiver: Optional[str] = None
        self._sender: Optional[str] = None
        self._body: Optional[list[str]] = None

    @property
    def image(self) -> Image:
        if not self.ocred:
            raise ValueError("Cannot get image of unocred message")
        if not self._image:
            # a bounding box (bbox) is a 4-tuple defining the left, upper, right, and lower pixel coordinate.
            # At 1920x1200, the box would be (8, 981, 571, 1136) if not stretched
            # At 1920x1200 stretched, the box would at approximately (9, 1080, 634, 1195)
            # if the ratio is not 16:9, we need to stretch our crop box.
            full_screen = ImageGrab.grab(include_layered_windows=True)
            bbox = (78, 981, 571, 1136)
            if DO_STRETCH:
                bbox = (79, 1080, 634, 1195)
            # scale for width and height of the full_screen
            bbox = (
                int(bbox[0] * full_screen.width / 1920),
                int(bbox[1] * full_screen.height / 1200),
                int(bbox[2] * full_screen.width / 1920),
                int(bbox[3] * full_screen.height / 1200),
            )
            self._image = ImageGrab.grab(bbox=bbox, include_layered_windows=True)
            # convert to greyscale
            self._image = self._image.convert("L")
        return self._image

    @property
    def text(self) -> str:
        if not self._text:
            assert self.ocred
            self._text = pytesseract.image_to_string(self.image)
        return self._text

    @property
    def data(self) -> dict:
        if not self.ocred:
            raise ValueError("Cannot get data of unocred message")
        if not self._data:
            tsv_data = pytesseract.image_to_data(self.image)
            tsv_reader = csv.reader(tsv_data.splitlines(), delimiter="\t")
            headers = [x.lower() for x in next(tsv_reader)]
            assert headers == [
                "level",
                "page_num",
                "block_num",
                "par_num",
                "line_num",
                "word_num",
                "left",
                "top",
                "width",
                "height",
                "conf",
                "text",
            ]
            self._data = [dict(zip(headers, row)) for row in tsv_reader]
        return self._data

    @property
    def raw_words(self) -> list[str]:
        if not self._raw_words:
            if self.ocred:
                # todo: deal with low confidence words
                raw = list(filter(itemgetter(0), [(x["text"].strip(), x["conf"]) for x in self.data if x["text"]]))
                self._raw_words = [x[0] for x in raw]
                self._raw_scores = [x[1] for x in raw]
                # remove low confidence words
                # for index, (score, word) in reversed(list(enumerate(zip(self._raw_scores, self._raw_words)))):
                #     if float(score) < 50:
                #         del self._raw_words[index]
                #         del self._raw_scores[index]

            else:
                self._raw_words = list(filter(None, [x.strip() for x in self.text.split()]))
            assert all(self._raw_words)
        return self._raw_words

    @lru_cache
    def valid_word(self, word: str, allow_mixed=False) -> bool:
        indicators = word and (
            all(c in string.ascii_uppercase + "-" for c in word)
            or all(c in string.digits for c in word)
            or word.startswith("=")
            or word.endswith("=")
            or (allow_mixed and all(c in (string.ascii_uppercase + "-" + string.digits) for c in word))
        )
        contra_indicators = not word or word.startswith("-") or word.endswith("-")
        return not contra_indicators and indicators

    @property
    def corrected_words(self) -> list[str]:
        if not self._corrected_words:
            # pytesseract seems to figure out 0 and Os using context clues.
            # The "1"s and "I"s in highfleet's font confuse it. we need to replace 1 with I in words that are mostly characters and I with 1 in words that are mostly numbers
            self._corrected_words = []
            new_replacement_words = {}
            for word in self.raw_words:
                if word in REPLACEMENT_WORD_CACHE:
                    if REPLACEMENT_WORD_CACHE[word] is None:
                        self._corrected_words.append("")
                        continue
                    self._corrected_words.append(REPLACEMENT_WORD_CACHE[word])
                    continue
                elif word in new_replacement_words:
                    if new_replacement_words[word] is None:
                        self._corrected_words.append("")
                        continue
                    self._corrected_words.append(new_replacement_words[word])
                    continue
                elif self.valid_word(word):
                    self._corrected_words.append(word)
                    new_replacement_words[word] = word
                    continue
                elif "I" in word:
                    # if the non I characters are mostly numbers, replace I with 1
                    number_count = sum(c.isdigit() for c in word.replace("I", ""))
                    if number_count > len(word) / 2:
                        replaced = word.replace("I", "1")
                        self._corrected_words.append(replaced)
                        new_replacement_words[word] = replaced
                        continue
                if "1" in word:
                    # if the non 1 characters are mostly letters, replace 1 with I
                    letter_count = sum(c.isalpha() for c in word.replace("1", ""))
                    if letter_count > len(word) / 2:
                        replaced = word.replace("1", "I")
                        self._corrected_words.append(replaced)
                        new_replacement_words[word] = replaced
                        continue
                # pound sings are sometimes 1s
                if "£" in word:
                    replaced = word.replace("£", "1")
                    if self.valid_word(replaced):
                        self._corrected_words.append(replaced)
                        new_replacement_words[word] = replaced
                        continue
                # fallthrough, the user can deal with this later
                self._corrected_words.append(word)
            for index, (new_word, old_word) in enumerate(zip(self._corrected_words, self._raw_words)):
                if new_word != old_word:
                    self.update_text_by_index(self._text, self.raw_words, index, new_word)
            REPLACEMENT_WORD_CACHE.update(new_replacement_words)
        return self._corrected_words

    @staticmethod
    def update_text_by_index(text: str, words: list[str], new_word_index: int, new_word: str) -> str:
        # if new_word is duplicated in the list, we need to figure out which one we're replacing
        duplicate_indices = [index for index, word in enumerate(words) if word == new_word]
        # we are assuming the words list is in order of appearance in the text, at least for duplicates
        if len(duplicate_indices) > 1:
            # replace the duplicates with unique markers that are unlikely to be in the text
            for index in duplicate_indices:
                text = text.replace(words[index], f"**{index}**", 1)
            # replace the one we want
            text = text.replace(f"**{new_word_index}**", new_word, 1)
            # replace the rest of the duplicates
            for index in duplicate_indices:
                if index != new_word_index:
                    text = text.replace(f"**{index}**", words[index], 1)
        else:
            text = text.replace(words[new_word_index], new_word, 1)
        return text

    @property
    def corrected_text(self) -> str:
        if not self._corrected_text:
            # _corrected_text is updated via update_corrected_word
            self._corrected_text = self._text
        return self._corrected_text

    def clear_words_after_corrected_words(self):
        self._words = None
        self._body = None
        self._receiver = None
        self._sender = None

    def update_corrected_word(self, index: int, new_word: str):
        self._corrected_text = self.update_text_by_index(self.corrected_text, self.corrected_words, index, new_word)
        self._corrected_words[index] = new_word
        self.clear_words_after_corrected_words()

    @property
    def words(self) -> tuple[str]:
        if not self._words:
            self._words = tuple(filter(None, [x for x in self.corrected_words if x]))
            assert all(self._words)
        return self._words

    @property
    def sender(self) -> Optional[str]:
        # the sender is the last word, prepended with a equals sign
        # the sender can be missing
        # return sans equals sign
        if not self._sender:
            self._sender = (
                self.words[-1].lstrip("=") if self.words and self.words[-1].startswith("=") else None
            ) or None
        return self._sender

    @property
    def receiver(self) -> Optional[str]:
        # the receiver is the first word appended with a equals sign
        # the receiver can be missing
        # return sans equals sign
        if not self._receiver:
            self._receiver = (self.words[0].rstrip("=") if self.words and self.words[0].endswith("=") else None) or None
        return self._receiver

    @property
    def body(self) -> list[str]:
        # the body is everything in between the sender and receiver
        if not self._body:
            self._body = self.words[1 if self.receiver else 0 : -1 if self.sender else None]
        return self._body

    def handle_replacement_word(self, word: str) -> str:
        replacement = None
        while True:  # no do while in python
            print(f"Please enter replacement for {word} or blank to skip")
            replacement = input()
            replacement = replacement.strip().upper()
            if replacement == "":
                # leave loop with no replacement
                break
            if self.valid_word(replacement, allow_mixed=True):
                # leave loop with replacement
                break
        return replacement

    def get_word_translations(self, translation_table: dict[int, str]) -> str:
        # get all the words in order, translate them and update the text to return
        cipher_words = [self.receiver] + list(self.body) + [self.sender]
        clear_words = [str.translate(word, translation_table) for word in cipher_words]
        return dict(zip(cipher_words, clear_words))

    def get_clear_text(self, translation_table: dict[int, str]) -> str:
        cipher_words_to_clear_words = self.get_word_translations(translation_table)
        clear_text = self.corrected_text
        for key, value in cipher_words_to_clear_words.items():
            clear_text = clear_text.replace(key, value, 1)
        return clear_text


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

    def handle_sender_decoding(self, message: Message):
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

    def handle_body_decoding(self, message: Message):
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
