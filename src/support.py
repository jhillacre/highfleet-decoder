import json

from tqdm import tqdm
from typing import Optional


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
