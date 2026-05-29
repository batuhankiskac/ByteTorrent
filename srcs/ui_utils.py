import time

FRAME_WIDTH = 50


def timestamp():
    return time.strftime("%X")


def print_box_up(title):
    line = "=" * FRAME_WIDTH
    print(f"\n{line}")
    print(title)
    print(line)


def print_box_bottom():
    print("=" * FRAME_WIDTH)
