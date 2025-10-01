import sys
import tkinter as tk
from collections.abc import Sequence
from operator import itemgetter
from typing import Any

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
from src.globals import BBOX, GROUP_COUNT
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
    return clear_words > len(words) / 4


def ask_if_clear(words: list[str], dictionary_words: AppendOnlyFileBackedSet) -> bool:
    """
    Ask the user if the message is clear text or cipher text
    """
    think_clear_text = is_clear_text(words, dictionary_words)
    if think_clear_text:
        print("This message is clear text.")
    else:
        print("This message seems like cipher text.")
    return think_clear_text if ask("Confirm?", choices=["y", "n"], default="y") == "y" else not think_clear_text


def ordinal(n: int) -> str:
    """Convert number to ordinal string (1st, 2nd, 3rd, 4th)."""
    if n % 100 in (11, 12, 13):  # Special case for 11th, 12th, 13th
        return f"{n}th"
    elif n % 10 == 1:
        return f"{n}st"
    elif n % 10 == 2:
        return f"{n}nd"
    elif n % 10 == 3:
        return f"{n}rd"
    else:
        return f"{n}th"


def ask_knobs() -> list[int]:
    """
    Ask the user for the current knob positions
    """
    knobs = [0, 0, 0, 0]
    while True:
        for index, knob in enumerate(knobs):
            while True:
                knob_label = ordinal(index + 1)
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
    source_type: str,
    source_word: str,
    target_word: str,
    code_diff: Sequence[int],
    original_knobs: Sequence[int],
) -> None:
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


def generate_suggestions(
    receiver_frequency: dict[str, int],
    sender_frequency: dict[str, int],
    word_frequency: dict[str, int],
    words: list[str],
    corrected_text: str,
    sender: str | None,
    receiver: str | None,
    seen_messages: AppendOnlyFileBackedSet | None = None,
) -> None:
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

                    # Check if this was a partial code
                    if len(inter_diff) < GROUP_COUNT:
                        print(f"Note: This is a partial code with only {len(inter_diff)} of {GROUP_COUNT} groups.")

                    keep_going = ask(
                        "Continue generating suggestions?",
                        choices=["y", "n"],
                        default="y",
                    )
                if keep_going == "n":
                    break
            if keep_going == "n":
                break
        if keep_going == "n":
            break
    else:
        print("We couldn't find a match for the captured cipher text.")
        print(f"The captured cipher text was:\n{corrected_text}")

    # Optionally mark cipher message as seen if user successfully decoded it
    if seen_messages is not None:
        mark_seen = ask("Did you successfully decode this message?", choices=["y", "n"], default="n")
        if mark_seen == "y":
            seen_messages.add(corrected_text)
            seen_messages.save()


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


class RegionSelector:
    """Interactive region selector overlay."""

    def __init__(self) -> None:
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.dragging = False
        self.selected_region = None

    def select_region(self) -> tuple[int, int, int, int] | None:
        """Show fullscreen overlay for region selection. Returns (x1, y1, x2, y2) or None if cancelled."""

        # Create instruction window (fully opaque)
        instruction_window = tk.Tk()
        instruction_window.title("Region Selector")
        instruction_window.attributes("-topmost", True)
        instruction_window.geometry("600x120")
        instruction_window.configure(bg="darkblue")

        # Center instruction window
        instruction_window.update_idletasks()
        x = (instruction_window.winfo_screenwidth() // 2) - (instruction_window.winfo_width() // 2)
        y = 50  # Near top of screen
        instruction_window.geometry(f"+{x}+{y}")

        # Instructions with full opacity
        instructions = tk.Label(
            instruction_window,
            text="Drag to select capture region.\nPress ESC to cancel, ENTER to confirm.",
            fg="white",
            bg="darkblue",
            font=("Arial", 16, "bold"),
            justify=tk.CENTER,
        )
        instructions.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Create transparent overlay window
        overlay = tk.Toplevel(instruction_window)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.1)  # Very transparent
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black")
        overlay.overrideredirect(True)  # Remove window decorations

        # Create canvas for drawing selection rectangle
        canvas = tk.Canvas(overlay, highlightthickness=0, bg="black")
        canvas.pack(fill=tk.BOTH, expand=True)

        selection_rect = None

        def on_mouse_down(event: Any) -> None:
            nonlocal selection_rect
            # Convert to absolute screen coordinates
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.dragging = True
            # Clear previous rectangle
            if selection_rect:
                canvas.delete(selection_rect)

        def on_mouse_drag(event: Any) -> None:
            nonlocal selection_rect
            if self.dragging:
                # Convert to absolute screen coordinates
                self.end_x = event.x_root
                self.end_y = event.y_root

                # Clear previous rectangle
                if selection_rect:
                    canvas.delete(selection_rect)

                # Draw new rectangle with better visibility (convert screen to canvas coordinates for drawing)
                canvas_start_x = self.start_x - overlay.winfo_rootx() if overlay.winfo_rootx() else self.start_x
                canvas_start_y = self.start_y - overlay.winfo_rooty() if overlay.winfo_rooty() else self.start_y
                canvas_end_x = self.end_x - overlay.winfo_rootx() if overlay.winfo_rootx() else self.end_x
                canvas_end_y = self.end_y - overlay.winfo_rooty() if overlay.winfo_rooty() else self.end_y

                selection_rect = canvas.create_rectangle(
                    canvas_start_x,
                    canvas_start_y,
                    canvas_end_x,
                    canvas_end_y,
                    outline="cyan",
                    width=3,
                    fill="white",
                    stipple="gray25",
                )

        def on_mouse_up(event: Any) -> None:
            self.dragging = False
            # Convert to absolute screen coordinates
            self.end_x = event.x_root
            self.end_y = event.y_root

        def on_key_press(event: Any) -> None:
            if event.keysym == "Escape":
                # Cancel selection
                self.selected_region = None
                instruction_window.quit()
            elif event.keysym == "Return":
                # Confirm selection
                if abs(self.end_x - self.start_x) > 10 and abs(self.end_y - self.start_y) > 10:
                    # Ensure coordinates are in correct order (x1 < x2, y1 < y2)
                    x1, x2 = sorted([self.start_x, self.end_x])
                    y1, y2 = sorted([self.start_y, self.end_y])
                    self.selected_region = (x1, y1, x2, y2)
                    print(f"Debug: Selected region {self.selected_region} (size: {x2 - x1}x{y2 - y1})")
                    instruction_window.quit()
                else:
                    # Selection too small
                    pass

        # Bind events - both windows need to handle keys
        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        overlay.bind("<KeyPress>", on_key_press)
        instruction_window.bind("<KeyPress>", on_key_press)

        # Make sure windows can receive key events
        overlay.focus_set()

        print("Region selector overlay active...")
        print("Drag to select region, ENTER to confirm, ESC to cancel")

        instruction_window.mainloop()
        instruction_window.destroy()

        return self.selected_region

    def show_image_preview(self, image: Any, title: str = "Captured Image") -> None:
        """Show captured image in a preview window."""
        # Save image temporarily and open with system default viewer
        temp_filename = "temp_preview.png"
        image.save(temp_filename)

        preview_window = tk.Tk()
        preview_window.title(title)
        preview_window.attributes("-topmost", True)
        preview_window.geometry("400x200")

        # Instructions about the saved image
        info_text = f"Captured image saved as: {temp_filename}\n"
        info_text += f"Image size: {image.size[0]}x{image.size[1]} pixels\n"
        info_text += f"Mode: {image.mode}\n\n"
        info_text += "Check the saved image file to verify the capture region.\n"
        info_text += "Press any key to close this window."

        info_label = tk.Label(
            preview_window,
            text=info_text,
            font=("Arial", 12),
            justify=tk.LEFT,
            wraplength=380,
        )
        info_label.pack(padx=20, pady=20)

        def close_preview(event: Any = None) -> None:
            preview_window.quit()

        preview_window.bind("<KeyPress>", close_preview)
        preview_window.focus_set()

        # Center window
        preview_window.update_idletasks()
        screen_width = preview_window.winfo_screenwidth()
        screen_height = preview_window.winfo_screenheight()
        x = (screen_width // 2) - (preview_window.winfo_width() // 2)
        y = (screen_height // 2) - (preview_window.winfo_height() // 2)
        preview_window.geometry(f"+{x}+{y}")

        print(f"Image preview saved as: {temp_filename}")
        print("Check the file to verify your capture region is correct.")

        try:
            preview_window.mainloop()
        finally:
            try:
                preview_window.destroy()
            except tk.TclError:
                pass  # Window already destroyed


def main() -> None:
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
    seen_messages = AppendOnlyFileBackedSet("seen_messages.txt", "seen messages", " messages", is_json=True)
    receiver_frequency = JSONBackedDict("receiver_frequency.json", "receiver frequency", " receivers")
    sender_frequency = JSONBackedDict("sender_frequency.json", "sender frequency", " senders")
    word_frequency = JSONBackedDict("word_frequency.json", "word frequency", " words")
    region_config = JSONBackedDict("capture_region.json", "capture region", " region")

    dictionary_words.load()
    seen_messages.load()
    receiver_frequency.load()
    sender_frequency.load()
    word_frequency.load()
    region_config.load()

    while True:
        pressed = ask(
            "Press 'r' to select region, 'q' to quit, or any other key to capture message.",
            char_input=True,
        )
        if pressed == "q":
            break
        elif pressed == "r":
            # Region selection mode
            print("Opening region selector...")
            selector = RegionSelector()
            selected_region = selector.select_region()

            if selected_region:
                region_config["bbox"] = list(selected_region)  # JSONBackedDict needs list, not tuple
                region_config.save()
                print(f"Region saved: {selected_region}")
                print(f"Size: {selected_region[2] - selected_region[0]}x{selected_region[3] - selected_region[1]}")
            else:
                print("Region selection cancelled.")
            continue
        # Detect DPI scaling for coordinate correction
        try:
            import ctypes

            user32 = ctypes.windll.user32
            screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

            # Compare with PIL screen size
            full_screen_test = ImageGrab.grab()

            # Calculate scaling factor
            scale_x = full_screen_test.width / screensize[0] if screensize[0] > 0 else 1.0
            scale_y = full_screen_test.height / screensize[1] if screensize[1] > 0 else 1.0

            if scale_x != 1.0 or scale_y != 1.0:
                print(f"DPI scaling detected: {scale_x:.1f}× (logical {screensize} → physical {full_screen_test.size})")
        except Exception as e:
            print(f"Could not detect scaling: {e}")
            scale_x = scale_y = 1.0

        # Get capture region - use saved region if available, otherwise fallback to default
        if "bbox" in region_config and region_config["bbox"]:
            bbox = tuple(region_config["bbox"])
            print(f"Using saved region: {bbox}")
            print(f"Region size: {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]}")

            # Apply scaling correction if needed
            if scale_x != 1.0 or scale_y != 1.0:
                bbox = (
                    int(bbox[0] * scale_x),
                    int(bbox[1] * scale_y),
                    int(bbox[2] * scale_x),
                    int(bbox[3] * scale_y),
                )
                print(f"Applying {scale_x:.1f}× scaling: {bbox}")
        else:
            # Fallback to default region with scaling
            full_screen = ImageGrab.grab()
            print(f"Screen resolution: {full_screen.size}")
            bbox = BBOX
            bbox = (
                int(bbox[0] * full_screen.width / 1920),
                int(bbox[1] * full_screen.height / 1200),
                int(bbox[2] * full_screen.width / 1920),
                int(bbox[3] * full_screen.height / 1200),
            )
            print(f"Using default scaled region: {bbox}")
            print(f"Scaled region size: {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]}")

        while True:  # Capture loop - allow recapture if needed
            # Try both capture methods to debug layering issues
            image = ImageGrab.grab(bbox=bbox).convert("L")

            # Save captured image for debugging
            image.save("debug_captured.png")

            text = pytesseract.image_to_string(image)
            print(f"Captured {image.size[0]}×{image.size[1]} region, OCR found {len(text)} characters")

            if len(text.strip()) == 0:
                print("Warning: No text detected by OCR!")

            # Show options for user
            action = ask(
                "'p' to preview, 'r' to recapture, 'f' for fullscreen capture, or any key to edit text",
                char_input=True,
            )

            if action == "p":
                # Show preview of captured image
                selector = RegionSelector()  # We reuse for the preview method
                selector.show_image_preview(image, f"Captured Image - Size: {image.size}")
                continue
            elif action == "r":
                # Recapture - just continue the loop
                print("Recapturing...")
                continue
            elif action == "f":
                # Capture full screen for debugging
                print("Capturing full screen for comparison...")
                full_image = ImageGrab.grab().convert("L")
                full_image.save("debug_fullscreen.png")
                print(f"Full screen saved as debug_fullscreen.png (size: {full_image.size})")
                selector = RegionSelector()
                selector.show_image_preview(full_image, "Full Screen Capture")
                continue
            else:
                # Proceed with text editing
                break

        print("Please correct the text, pressing ESC to continue.")
        corrected_text = edit_lines(text)

        # Check if we've already seen this message
        if corrected_text in seen_messages:
            print("This message has already been seen. Skipping processing.")
            continue

        receiver, sender, words = process_text(corrected_text)
        message_is_clear = ask_if_clear(words, dictionary_words)
        if message_is_clear:
            # Record clear text message frequencies
            if receiver:
                receiver_frequency[receiver] = receiver_frequency.get(receiver, 0) + 1
            if sender:
                sender_frequency[sender] = sender_frequency.get(sender, 0) + 1
            for word in words:
                word_frequency[word] = word_frequency.get(word, 0) + 1

            # Mark message as seen and save all data
            seen_messages.add(corrected_text)
            receiver_frequency.save()
            sender_frequency.save()
            word_frequency.save()
            seen_messages.save()
        else:
            generate_suggestions(
                receiver_frequency,
                sender_frequency,
                word_frequency,
                words,
                corrected_text,
                sender,
                receiver,
                seen_messages,
            )


if __name__ == "__main__":
    main()
