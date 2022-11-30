# highfleet-decoder

![A HighFleet clear text message.](./example_message.png)

A command line interface for dealing with HighFleet radio intercepts.
* captures clear text or cipher text via OCR.
* track frequency of words in clear text.
* generate cipher code difference by matching frequent word difference vs cipher words.
* helps translate a code difference to a code.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

---

* [highfleet-decoder](#highfleet-decoder)
  * [License](#license)
  * [Install](#install)
  * [Usage](#usage)
  * [Tips](#tips)
  * [Todo](#todo)

---

## Install

1. download source or clone the repo
2. use `pipenv` to create environment and install dependencies

## Usage

`$ python highfleet-decoder.py`

![(What the program looks like.)](./example_startup.png)

* Follow onscreen prompts to
 * capture message
 * fix OCR
 * confirm if message is clear or cipher text (it knows)
 * review code suggestions.

## Tips

The project is a rough prototype.

* Valid word characters are `strings.ascii_uppercase + strings.digits + "=-"`. I haven't dealt with dashed locations yet, probably will be treated as multiple words.
* HighFleet messages are all caps. When correcting OCR text, your input will be transformed into uppercase.
* When correcting senders or receivers, the equals sign must be in the right place to be detected as such. Receivers and senders are kept separate from body words. 
* Senders and receivers must be last and first. If there is OCR text after, you should blank it, or swap positions with other text.
* `1` and `I` look the same in HighFleet's font. The project tries to deal with this by figuring out if the rest of the word is mostly numbers or letters.
* Are the suggestions actually solutions?
  * Depends on the frequency list being populated somewhat.
  * Assuming that unique words have unique difference patterns 

## Todo

* Finding edge cases by running campaigns.
* Ability to have different frequency sets, for starting clean with a new campaigns, if desired.
* Add unit tests.
* Add CI, preferably in CircleCI since I've used it.
* Refactor code into not one big file.
* Screenshots.
* Colour output.
* Arguments and argument parsing?
* `pypi` package?

## License

[BSD-3-Clause license](./LICENSE)

`words_alpha.txt` used under "Unlicense license", [dwyl/english-words](https://github.com/dwyl/english-words)
