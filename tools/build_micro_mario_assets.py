"""Build original Micro Mario pixel art using only the Python standard library."""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "badge" / "apps" / "micro_mario"
PALETTE = {
    ".": (0, 0, 0, 0),
    "k": (20, 29, 48, 255),
    "w": (255, 247, 215, 255),
    "t": (36, 166, 165, 255),
    "T": (109, 230, 199, 255),
    "o": (230, 129, 63, 255),
    "s": (255, 201, 140, 255),
    "b": (107, 67, 65, 255),
    "g": (57, 162, 91, 255),
    "G": (137, 218, 112, 255),
    "y": (255, 210, 78, 255),
    "r": (204, 74, 102, 255),
    "p": (130, 92, 176, 255),
    "B": (66, 104, 151, 255),
}


def tile(rows):
    width = max(map(len, rows))
    if width > 16 or len(rows) > 16:
        raise ValueError("Sprite exceeds 16x16")
    left = (16 - width) // 2
    result = ["." * 16] * (16 - len(rows))
    return result + ["." * left + row.ljust(width, ".") + "." * (16 - width - left)
                     for row in rows]


HERO = [
    "....kkkkk.......", "...ktTTTtk......", "..ktTTTTTtkk....",
    "..ktttttttttk...", "...kbsskwssk....", "...kbsskksssk...",
    "....kssbbbkk....", "...kttBBttk.....", "..kwtByyBtwk....",
    "..kwwBBBBwwk....", "...kBBBBBBk.....", "...kBBkkBBk.....",
    "..kbbbkkbbbk....", "..kkkk..kkkk....",
]
BIG_HERO = [
    "....kkkkkk......", "...ktTTTTtk.....", "..ktTTTTTTtkk...",
    "..kttttttttttk..", "...kbbsskwssk...", "...kbssskwssk...",
    "...kbsssksSSsk..", "....ksssbbbkk...", ".....kssbbbk....",
    "....ktttttk.....", "...ktTTttTtk....", "..kttTBBTTttk...",
    ".kwwtByyBtwwk...", ".kwwwBBBBwwwk...", "..kwwBBBBwwk....",
    "...kBBBBBBk.....", "...kBBbbBBk.....", "...kBBbbBBk.....",
    "...kBBkkBBk.....", "...kBBkkBBk.....", "...kBBkkBBk.....",
    "...kbbkkbbk.....", "..kbbbkkbbbk....", "..kbbbkkbbbk....",
    "..kbbbkkbbbk....", "..kkkk..kkkk....", "................",
    "................",
]
PALETTE["S"] = (239, 157, 105, 255)


def hero_frames(large=False, fire=False):
    base = BIG_HERO if large else HERO
    frames = []
    for pose in range(6):
        rows = list(base)
        if pose == 1:
            rows[-6:] = [
                "...kBBkkBBk.....", "..kBBk..kBBk....", ".kbbbk..kBBk....",
                ".kkkk....kbbbk..", ".........kkkk...", "................",
            ]
        elif pose == 3:
            rows[-6:] = [
                "...kBBkkBBk.....", "...kBBk..kBBk...", "...kBBk..kbbbk..",
                "..kbbbk...kkkk..", "..kkkk..........", "................",
            ]
        elif pose == 2:
            rows[-6:] = [
                "....kBBBBk......", "....kBBBk.......", "....kBBk........",
                "...kbbbk........", "...kbbbk........", "...kkkk.........",
            ]
        elif pose == 4:
            rows[-6:] = [
                "..kBBkkBBk......", ".kBBk..kBBk.....", "kbbbk...kBBk....",
                "kkkk....kbbbk...", "........kkkk....", "................",
            ]
        elif pose == 5:
            rows[-6:] = [
                "..kBBBBBBk......", ".kBBkkkkBBk.....", "kbbbk...kBBk....",
                "kkkk....kbbbk...", "........kkkk....", "................",
            ]
        if fire:
            rows = [row.replace("t", "r").replace("T", "w").replace("B", "o")
                    for row in rows]
        frames.append(["." * 16] * (32 - len(rows)) + rows)
    return frames


HEROES = (hero_frames() + hero_frames(True)
          + hero_frames(True, True) + hero_frames(False, True))
WALKER = [
    "....oooo....", "..ooyyyyoo..", ".ooyoyoyyoo.", "ooyyyyyyyyoo",
    "ooooooooyooo", ".kswkkwsk...", ".ksskkssk...", "..ssssss....",
    "..bb..bb....", ".kkk..kkk...", "............",
]
TURTLE = [
    "....GGG.....", "...GgggG....", "..GgGgGgG...", ".GgggggggG..",
    ".GgGgGgGgG..", ".GgggggggG..", "..GGGGGGG...", "..gggg..sss.",
    "..gggg..swk.", "..gggg..sss.", "...bb..bb...", "..kkk..kkk..",
]
SPRITES = [
    tile(HERO),
    tile(HERO[:10] + ["...bb..bb...", "...kk...bb..", ".......kkk..", "............"]),
    tile(HERO[:7] + ["sstTtttTtss.", "ss.ttttt.ss.", "...bbbbbb...", "..bb....bb..", ".kkk....kkk.", "............"]),
    tile(WALKER),
    tile(WALKER[:8] + ["..bb..bb....", "..kk..kkkk..", "............"]),
    tile(TURTLE),
    tile(["ww......ww..", "www....www..", ".wwGGGGww...", ".wGgGgGgGw..",
          ".GgggggggG..", ".GgGgGgGgG..", "..GGGGGGG...", "..gggg..sss.",
          "..gggg..swk.", "..gggg..sss.", "...bb..bb...", "..kkk..kkk.."]),
    tile(["....rrrr....", "..rrwwwwrr..", ".rwwrwwrwwr.", ".rrrwwwwrrr.",
          "rrwkwrrwkwrr", "rrrrrrrrrrrr", ".rrwwwwwwrr.", "..rrwwwwrr..",
          "....gggg....", ".GG.gggg.GG.", "..GGggggGG..", "....gggg...."]),
    tile(["kkkkkkkkkkkkkkkk", "boooooobooooooob", "boooooobooooooob", "boooooobooooooob",
          "boooooobooooooob", "bbbbbbbbbbbbbbbb", "oooboooooooboooo", "oooboooooooboooo",
          "oooboooooooboooo", "bbbbbbbbbbbbbbbb", "boooooobooooooob", "boooooobooooooob",
          "boooooobooooooob", "boooooobooooooob", "bbbbbbbbbbbbbbbb", "kkkkkkkkkkkkkkkk"]),
    tile(["kkkkkkkkkkkkkkkk", "kyyyyyyyyyyyyyyk", "kykyyyyyyyyyykyk", "kyyyykkkkkkyyyyk",
          "kyyykkwwwwkkyyyk", "kyyyyyyywwkkyyyk", "kyyyyyywwkkyyyyk", "kyyyyywwkkyyyyyk",
          "kyyyyywwkyyyyyyk", "kyyyyyyyyyyyyyyk", "kyyyyywwkyyyyyyk", "kyyyyywwkyyyyyyk",
          "kyyyyyyyyyyyyyyk", "kykyyyyyyyyyykyk", "kyyyyyyyyyyyyyyk", "kkkkkkkkkkkkkkkk"]),
    tile(["kkkkkkkkkkkkkkkk"] + ["kbbbbbbbbbbbbbbk"] * 14 + ["kkkkkkkkkkkkkkkk"]),
    tile(["kgGGgggggggggggk"] * 16),
    tile(["kkkkkkkkkkkkkkkk", "kGGGGGGGGGGGGGGk", "kGGGGGGGGGGGGGGk",
          "kggggggggggggggk", "kkkkkkkkkkkkkkkk"] + ["kgGGgggggggggggk"] * 11),
    tile([".....yyy....", "....ywwwy...", "...ywykwyy..", "...ywykwyy..",
          "...ywykwyy..", "...ywykwyy..", "...ywykwyy..", "...ywykwyy..",
          "....ywwwy...", ".....yyy....", "............", "............"]),
    tile(["....yyyy....", "..yyTTTTyy..", ".yTTTwwTTTy.", ".yTTwwwwTTy.",
          ".yTTwwwwTTy.", "..yTTwwTTy..", "..yTTTTTTy..", "...yTTTTy...",
          "....yTTy....", ".....yy.....", "............", "............"]),
    tile(["....GGGG....", "..GGggggGG..", ".GgGgGgGgG..", ".GgggggggG..",
          ".GgGgGgGgG..", "..GGGGGGGG..", ".kkkkkkkkkk.", "............"]),
    tile(["....pppp....", "..ppwwwwpp..", ".pwwppppwwp.", ".ppppwwpppp.",
          "ppwwpwwpwwpp", "pwwppppppwwp", "pppppppppppp", ".kkkkkkkkkk.",
          "...swwwws...", "...swkkws...", "...swwwws...", "....kkkk...."]),
    tile(["....oooo....", "...owwwwo...", "..owoyyowo..", "..owyyyywo..",
          "...owwwwo...", "....oooo....", ".....gg.....", "..GG.gg.GG..",
          "...GGggGG...", ".....gg.....", "....gggg....", "....kkkk...."]),
    tile(["............", "............", ".....oo.....", "....oyyo....",
          "...oywwyo...", "...oywwyo...", "....oyyo....", ".....oo.....",
          "............", "............", "............", "............"]),
]
for frame in SPRITES[:3]:
    SPRITES.append([row.replace("t", "o").replace("T", "w").replace("b", "r")
                    for row in frame])
while len(SPRITES) < 24:
    SPRITES.append(["." * 16] * 16)


def chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))


def write_png(path, pixels):
    height, width = len(pixels), len(pixels[0])
    raw = b"".join(b"\0" + bytes(v for pixel in row for v in PALETTE[pixel])
                   for row in pixels)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9))
    data += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    atlas = [["."] * 128 for _ in range(48)]
    for index, art in enumerate(SPRITES):
        x, y = index % 8 * 16, index // 8 * 16
        for row, line in enumerate(art):
            atlas[y + row][x:x + 16] = line
    write_png(APP / "assets" / "sprites.png", atlas)
    heroes = [["."] * 128 for _ in range(96)]
    for index, art in enumerate(HEROES):
        x, y = index % 8 * 16, index // 8 * 32
        for row, line in enumerate(art):
            if len(line) != 16:
                raise ValueError("Hero rows must be exactly 16 pixels wide")
            heroes[y + row][x:x + 16] = line
    write_png(APP / "assets" / "heroes.png", heroes)
    icon = [["B"] * 24 for _ in range(24)]
    for y in range(20, 24):
        icon[y] = list(("G" if y == 20 else "b") * 24)
    for y, row in enumerate(SPRITES[0]):
        for x, pixel in enumerate(row):
            if pixel != ".":
                icon[4 + y][4 + x] = pixel
    for y, row in enumerate(SPRITES[13]):
        for x, pixel in enumerate(row):
            if pixel != ".":
                icon[y][12 + x] = pixel
    write_png(APP / "icon.png", icon)
    print("Built sprites (128x48), animated heroes (128x96) and icon (24x24).")


if __name__ == "__main__":
    main()
