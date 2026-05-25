import time

FRAME_WIDTH = 50


def ts():
    return time.strftime("%X")


def print_box_title(title):
    line = "=" * FRAME_WIDTH
    print(f"\n{line}")
    print(title)
    print(line)


def print_box_footer():
    print("=" * FRAME_WIDTH)
