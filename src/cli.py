
from functools import partial
from time import sleep
try:
    import msvcrt
except (ImportError, ModuleNotFoundError):
    msvcrt = None
import shutil
import sys
try:
    import termios
    import tty
except (ImportError, ModuleNotFoundError):
    termios = None
    tty = None

from argparse_color_formatter import ColorTextWrapper
from colors import color

BLUE_COLOR = partial(color, fg='#0077f7', style='bold') # Blue
ORANGE_COLOR = partial(color, fg='#F77700', style='bold') # Orange
OPEN_PROMPT = "\x1b[38;2;127;255;0m\x1b[1m" # Green
CLOSE_PROMPT = "\x1b[0m" # reset
ERROR_COLOR = partial(color, fg='#FF0000', style='bold') # Red

def get_terminal_width() -> int:
    terminal_size = shutil.get_terminal_size()
    return terminal_size[0]

text_wrapper = ColorTextWrapper(width=get_terminal_width())

def wrap_text(text: str) -> str:
    return "\n".join(text_wrapper.wrap(text))

def get_char(default: str = None) -> str:
    """
    Get a single character from stdin.
    """
    answer = None
    try:
        sys.stdout.write(OPEN_PROMPT)
        while answer is None:
            key = msvcrt.getch()
            printable = False
            str_key = None
            try:
                str_key = key.decode()
                printable = str_key.isprintable()
            except UnicodeDecodeError:
                pass
            if (b"\n" in key or b"\r" in key) and default is not None:
                answer = default
                print(answer, end="", file=sys.stdout)
            elif printable:
                answer = str_key.lower()
                print(answer, end="", file=sys.stdout)
    finally:
        print(CLOSE_PROMPT, file=sys.stdout)
    return answer

def get_string(default: str = None) -> str:
    """
    Get a string from stdin.
    """
    try:
        answer = input(OPEN_PROMPT)
        if answer == "" and default is not None:
            answer = default
            sys.stdout.write(answer)
    finally:
        print(CLOSE_PROMPT, file=sys.stdout)
    return answer

def ask(question: str, choices: list = None, default: str = None, char_input: bool = False) -> str:
    """
    Ask a question and return the answer.
    """
    get_answer = get_char if char_input else get_string
    if choices:
        if "" in choices:
            raise ValueError("Empty string not allowed in choices")
        if not all((x in choices for x in default)):
            raise ValueError("Default value must be in choices")
        if not all((x.isprintable() for x in choices)):
            raise ValueError("Choices must be printable characters")
        choices_text = ORANGE_COLOR(f"[{','.join(choices)}]")
        default_text = BLUE_COLOR(f"({default})") if default else ""
        answer = None
        while answer not in choices:
            sys.stdout.write(wrap_text(f"{BLUE_COLOR(question)}{choices_text}{default_text}>"))
            sys.stdout.flush()
            answer = get_answer(default)
            if answer not in choices:
                print(wrap_text(f"{ERROR_COLOR('Invalid choice'): {answer!r}}"), file=sys.stderr)
    else:
        sys.stdout.write(wrap_text(f"{BLUE_COLOR(question)}>"))
        sys.stdout.flush()
        answer = get_answer(default)
        if char_input:
            try:
                answer = answer.decode()
            except (UnicodeDecodeError, AttributeError):
                pass
    return answer

def visible_length(string):
    """
    Calculate the visible length of a string (excluding ANSI codes).
    """
    escape_code = False
    length = 0
    for char in string:
        if char == "\x1b":
            escape_code = True
        elif escape_code:
            if char == "m":
                escape_code = False
        else:
            length += 1
    return length

EDITOR_INSTRUCTIONS = f"{ORANGE_COLOR('⏎')} {BLUE_COLOR('to insert lines,')} {ORANGE_COLOR('←→↑↓⇤⇥')} {BLUE_COLOR('to move cursor,')} {ORANGE_COLOR('␈,␡')} {BLUE_COLOR('to delete, and')} {ORANGE_COLOR('␛')} {BLUE_COLOR('to finish.')}"

def edit_lines(text, max_lines=5):
    """
    A simple multi-line text editor.
    """
    lines = text.splitlines()[:max_lines]
    cursor_x, cursor_y = 0, 0
    prev_cursor_y = 0, 0
    pressed = ""

    def clear_screen():
        if prev_cursor_y:
            sys.stdout.write(f"\x1b[{prev_cursor_y}A") # move up
        sys.stdout.write("\x1b[G") # move to the first column
        sys.stdout.write("\x1b[J") # clear down to bottom

    def draw_lines():
        for index, line in enumerate(lines):
            sys.stdout.write(line)
            if index < len(lines) - 1:
                sys.stdout.write("\n")

    def draw_cursor():
        lines_to_move_up = len(lines) - cursor_y - 1
        if lines_to_move_up:
            sys.stdout.write(f"\x1b[{lines_to_move_up}A") # move up
        sys.stdout.write(f"\x1b[{cursor_x + 1}G") # move to column (columns start at 1)
        sys.stdout.flush()

    print(wrap_text(EDITOR_INSTRUCTIONS) + OPEN_PROMPT)
    draw_lines()
    draw_cursor()

    while True:
        key = msvcrt.getch()
        pressed = key
        isprintable = False
        str_key = None
        redraw = False
        bell = False
        try:
            str_key = key.decode()
            isprintable = str_key.isprintable()
            pressed = str_key
        except UnicodeDecodeError:
            pass
        if key == b'\x03':
            # ctrl-c
            raise KeyboardInterrupt
        elif key == b"\r" or key == b"\n":
            # insert a new line, breaking the current line depending on the cursor position
            if len(lines) < max_lines:
                lines.insert(cursor_y + 1, lines[cursor_y][cursor_x:])
                lines[cursor_y] = lines[cursor_y][:cursor_x]
                cursor_y += 1
                cursor_x = 0
                redraw = True
            else:
                bell = True
        elif key == b"\x08":
            # backspace
            # if at the beginning of a line
            if cursor_x == 0:
                # if at the beginning of the first line, do nothing
                if cursor_y > 0:
                    # join with the previous line
                    cursor_y -= 1
                    cursor_x = len(lines[cursor_y])
                    lines[cursor_y] += lines.pop(cursor_y + 1)
                    redraw = True
                else:
                    bell = True
            else:
                # delete the character before the cursor
                cursor_x -= 1
                lines[cursor_y] = lines[cursor_y][:cursor_x] + lines[cursor_y][cursor_x + 1:]
                redraw = True
        elif key == b"\x7f":
            # delete
            # if at the end of a line, join with the next line
            # if at the end of the last line, do nothing
            if cursor_x == len(lines[cursor_y]):
                if cursor_y < len(lines) - 1:
                    lines[cursor_y] += lines.pop(cursor_y + 1)
                    redraw = True
                else:
                    bell = True
            else:
                lines[cursor_y] = lines[cursor_y][:cursor_x] + lines[cursor_y][cursor_x + 1:]
                redraw = True
        elif key == b"\x1b":
            # escape
            break
        elif key == b"\xe0":
            # special key
            key = msvcrt.getch()
            pressed = [pressed, key]
            if key == b"G":
                # home
                cursor_x = 0
                sys.stdout.write("\x1b[G")
                sys.stdout.flush()
            elif key == b"O":
                # end
                cursor_x = len(lines[cursor_y])
                sys.stdout.write(f"\x1b[{cursor_x + 1}G")
                sys.stdout.flush()
            elif key == b"S":
                # delete
                # delete the character after the cursor
                # if at the end of a line, join with the next line
                # if at the end of the last line, do nothing
                if cursor_x == len(lines[cursor_y]):
                    if cursor_y < len(lines) - 1:
                        lines[cursor_y] += lines.pop(cursor_y + 1)
                        redraw = True
                    else:
                        bell = True
                else:
                    lines[cursor_y] = lines[cursor_y][:cursor_x] + lines[cursor_y][cursor_x + 1:]
                    redraw = True
            elif key == b"H":
                # up arrow
                if cursor_y > 0:
                    cursor_y -= 1
                    cursor_x = min(cursor_x, len(lines[cursor_y]))
                    sys.stdout.write("\x1b[A")
                    sys.stdout.flush()
                else:
                    bell = True
            elif key == b"K":
                # left arrow
                if cursor_x > 0:
                    cursor_x -= 1
                    sys.stdout.write("\x1b[D")
                    sys.stdout.flush()
                else:
                    bell = True
            elif key == b"M":
                # right arrow
                if cursor_x < len(lines[cursor_y]):
                    cursor_x += 1
                    sys.stdout.write("\x1b[C")
                    sys.stdout.flush()
                else:
                    bell = True
            elif key == b"P":
                # down arrow
                if cursor_y < len(lines) - 1:
                    cursor_y += 1
                    cursor_x = min(cursor_x, len(lines[cursor_y]))
                    sys.stdout.write("\x1b[B")
                    sys.stdout.flush()
                else:
                    bell = True
            else:
                raise ValueError(f"Invalid key: {key!r}")
        elif isprintable:
            # printable character
            lines[cursor_y] = lines[cursor_y][:cursor_x] + str_key + lines[cursor_y][cursor_x:]
            cursor_x += 1
            redraw = True
        else:
            raise ValueError(f"Invalid key: {key!r}")
        if redraw:
            clear_screen()
            draw_lines()
            draw_cursor()
        if bell:
            sys.stdout.write("\a")
            sys.stdout.flush()
        prev_cursor_y = cursor_y

    result = "\n".join(lines)

    # done editing, show the final result without the cursor
    clear_screen()
    draw_lines()
    sys.stdout.write(CLOSE_PROMPT + "\n")
    sys.stdout.flush()
    return result

