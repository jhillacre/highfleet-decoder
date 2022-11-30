import csv
from functools import lru_cache
from operator import itemgetter
import string
from typing import Optional

import pytesseract
from PIL import Image, ImageGrab

from src.globals import DO_STRETCH


REPLACEMENT_WORD_CACHE = {}


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
