"""Micro Mario: original pixel-art adventures for the 2026 badge."""

import os
import sys

APP_DIR = "/system/apps/micro_mario"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from badgeware import State
from game import Game, BIOMES, TILE, COLS, ROWS

badge.mode(HIRES | VSYNC)
display = screen
display.antialias = image.OFF
screen = image(214, 160)
screen.font = font.nope
screen.antialias = image.OFF
screen.fill_rule = image.EVEN_ODD
sheet = image.load("assets/sprites.png").spritesheet(8, 3)
sprites = [sheet.sprite(i % 8, i // 8) for i in range(24)]
hero_sheet = image.load("assets/heroes.png").spritesheet(8, 3)
heroes = [hero_sheet.sprite(i % 8, i // 8) for i in range(24)]
WHITE = color.rgb(255, 247, 215)
INK = color.rgb(15, 23, 45)
GOLD = color.rgb(255, 210, 78)
BUSH_SHADOW = color.rgb(28, 99, 75)
BUSH_MID = color.rgb(42, 139, 88)
BUSH_LIGHT = color.rgb(79, 177, 108)
BUSH_GLEAM = color.rgb(134, 203, 121)
SKIES = (color.rgb(100, 177, 229), color.rgb(24, 27, 55),
         color.rgb(21, 86, 151))
EARTH = (color.rgb(163, 91, 61), color.rgb(73, 72, 115),
         color.rgb(190, 161, 98))
saved = {"best": 0}
State.load("pocket_plumber", saved)
game = Game((badge.ticks % 999999) + 1)
paused = False
world_y = 0


def box(x, y, w, h, pen):
    screen.pen = pen
    screen.shape(shape.rectangle(int(x), int(y - world_y), int(w), int(h)))


def text(label, x, y, pen=WHITE):
    screen.pen = INK
    screen.text(label, x + 1, y + 1)
    screen.pen = pen
    screen.text(label, x, y)


def center(label, y, pen=WHITE):
    width, _ = screen.measure_text(label)
    text(label, (screen.width - width) // 2, y + (screen.height - 120) // 2, pen)


def sprite(index, x, y, flip=False, height=16):
    screen.blit(sprites[index], rect(int(x), int(y - world_y), -16 if flip else 16, height))


def save_best():
    if game.score > saved["best"]:
        saved["best"] = game.score
        State.save("pocket_plumber", saved)


def backdrop(camera, camera_y):
    box(0, 0, screen.width, screen.height, SKIES[game.biome])
    if game.biome == 0:
        for i in range(7):
            x = (i * 73 - camera * .22) % (screen.width + 90) - 45
            box(x, 48 + (i % 3) * 19, 34, 9, WHITE)
            box(x + 8, 42 + (i % 3) * 19, 19, 8, WHITE)
        for i in range(6):
            x = (i * 97 - camera * .4) % (screen.width + 100) - 50
            y = 208 - camera_y
            height = 28 + (i % 3) * 5
            box(x + 3, y - 22, 62, 22, BUSH_SHADOW)
            box(x + 13, y - height, 42, height, BUSH_SHADOW)
            box(x + 21, y - height - 5, 23, 6, BUSH_SHADOW)
            box(x + 1, y - 18, 19, 14, BUSH_MID)
            box(x + 10, y - 26, 22, 23, BUSH_MID)
            box(x + 25, y - height + 1, 21, height - 4, BUSH_MID)
            box(x + 43, y - 24, 19, 20, BUSH_MID)
            box(x + 14, y - 25, 13, 5, BUSH_LIGHT)
            box(x + 26, y - height + 2, 15, 5, BUSH_LIGHT)
            box(x + 46, y - 23, 10, 4, BUSH_LIGHT)
            for leaf in range(7):
                lx = x + 7 + (leaf * 13 + i * 7) % 49
                ly = y - 8 - (leaf * 7 + i * 3) % 15
                box(lx, ly, 4, 2, BUSH_LIGHT if leaf % 2 else BUSH_SHADOW)
                if leaf % 3 == 0:
                    box(lx + 1, ly - 1, 2, 1, BUSH_GLEAM)
    elif game.biome == 1:
        for i in range(20):
            x = (i * 37 - camera * .35) % (screen.width + 20)
            box(x, 20, 7, 9 + (i % 4) * 8, EARTH[1])
            box(x + 2, 29 + (i % 4) * 8, 3, 5, EARTH[1])
        for i in range(10):
            x = (i * 59 - camera * .6) % (screen.width + 30)
            box(x, 180 - camera_y, 5, 28, color.rgb(36, 102, 127))
    else:
        for i in range(18):
            x = (i * 31 - camera * .3) % screen.width
            y = 30 + (i * 47 - int(game.clock * 16)) % 166
            box(x, y, 3, 3, color.rgb(89, 170, 211))
        for i in range(12):
            x = (i * 43 - camera * .7) % (screen.width + 20)
            box(x, 184 - camera_y, 3, 24, color.rgb(54, 158, 133))
            box(x - 4, 191 - camera_y, 6, 3, color.rgb(54, 158, 133))


def draw_world():
    global world_y
    p = game.player
    camera = max(0, min(COLS * TILE - screen.width, p.x - screen.width * .35))
    camera_y = max(0, min(ROWS * TILE - screen.height,
                          p.y + p.h / 2 - screen.height * .55))
    world_y = 0
    backdrop(camera, camera_y)
    world_y = camera_y
    first = max(0, int(camera // TILE))
    last = min(COLS, first + screen.width // TILE + 2)
    for row in range(3, 15):
        for col in range(first, last):
            tile = game.level.tiles[row][col]
            if not tile:
                continue
            x, y = col * TILE - camera, row * TILE
            if tile == 1:
                box(x, y, 16, 16, EARTH[game.biome])
                box(x, y, 16, 2, GOLD if game.biome == 2 else color.rgb(58, 181, 111))
                box(x + 3, y + 7, 3, 2, INK)
                box(x + 11, y + 12, 3, 2, INK)
            else:
                sprite({2: 8, 3: 9, 4: 10, 5: 11, 6: 12}[tile], x, y)
    for coin in game.level.coins:
        if coin[2] and camera - 16 < coin[0] < camera + screen.width:
            sprite(13, coin[0] - camera - 4, coin[1] - 3)
    for pickup in game.pickups:
        if pickup.alive:
            index = {"shield": 14, "mushroom": 16, "flower": 17}[pickup.kind]
            sprite(index, pickup.x - camera - 2, pickup.y - 4)
    for shot in game.fireballs:
        sprite(18, shot.x - camera - 5, shot.y - 5)
    for enemy in game.level.enemies:
        if not enemy.alive or not enemy.h or not camera - 20 < enemy.x < camera + screen.width:
            continue
        x, y = enemy.x - camera - 2, enemy.y + enemy.h - 16
        if enemy.kind == "plant":
            # Stem extends from the pipe; the head emerges last.
            if enemy.h > 5:
                box(x + 7, enemy.y + 5, 3, enemy.h - 5, color.rgb(54, 174, 109))
            if enemy.h >= 8:
                sprite(7, x, enemy.y - 2)
        else:
            index = {"walker": 3 + int(game.clock * 6) % 2, "turtle": 5,
                     "flying": 6, "shell": 15}[enemy.kind]
            sprite(index, x, y, enemy.direction > 0)
    checkpoint_x = game.level.checkpoint - camera
    box(checkpoint_x, 170, 2, 38, WHITE)
    box(checkpoint_x + 2, 170, 15, 9, GOLD if game.checkpoint else EARTH[1])
    goal_x = game.level.goal - camera
    box(goal_x, 97, 3, 111, WHITE)
    box(goal_x + 3, 98, 25, 16, GOLD)
    box(goal_x + 10, 102, 6, 6, INK)
    if game.invincible <= 0 or int(game.clock * 14) % 2 == 0:
        if game.biome == 2 and not p.grounded:
            frame = 4 + int(game.clock * 6) % 2
        elif not p.grounded:
            frame = 4
        else:
            frame = 1 + int(game.clock * 12) % 3 if abs(p.vx) > 8 else 0
        if p.h > 14:
            frame += 6
        if game.power == "fire":
            frame += 6 if p.h > 14 else 18
        screen.blit(heroes[frame], rect(
            int(p.x - camera - 3), int(p.y + p.h - 32 - world_y),
            -16 if p.direction < 0 else 16, 32))
        if game.shield:
            box(p.x - camera + 1, p.y - 5, 8, 2, GOLD)
    world_y = 0
    box(0, 0, screen.width, 22, INK)
    text("%06d  x%d" % (game.score, game.lives), 3, 1)
    text("%d %s $%02d T%03d" % (
        game.stage, BIOMES[game.biome][:3], game.coins, max(0, int(game.time))),
        3, 11, GOLD)
    if game.power != "small":
        text("FIRE" if game.power == "fire" else "BIG", screen.width - 30, 1, GOLD)


def panel():
    box(2, 24, screen.width - 4, screen.height - 26, INK)
    box(4, 25, screen.width - 8, 1, GOLD)


def draw_overlay():
    if game.status == "title":
        panel()
        center("MICRO MARIO", 30, GOLD)
        center("< %s >" % BIOMES[game.start_biome], 44, GOLD)
        center("D-pad move  A jump", 58)
        center("B run/fire  MENU pause", 69)
        center("A start  B new seed", 82)
        center("SEED %06d" % game.seed, 96)
        center("BEST %d" % saved["best"], 107)
    elif paused:
        panel()
        center("PAUSED", 30, GOLD)
        center("A jump / swim", 44)
        center("B hold: run  tap: fire", 55)
        center("Mushroom: grow", 66)
        center("Flower: fireballs", 77)
        center("Down: dive", 88)
        center("MENU resume HOME exit", 104)
    elif game.status == "clear":
        panel()
        center("STAGE CLEAR!", 32, GOLD)
        center("Next: %s" % BIOMES[(game.biome + 1) % 3], 53)
        center("Score %d" % game.score, 74)
        center("A / SELECT continue", 99)
    elif game.status == "gameover":
        panel()
        center("ADVENTURE OVER", 32, GOLD)
        center("Score %d" % game.score, 50)
        center("Best %d" % saved["best"], 64)
        center("A retry same seed", 87)
        center("B return to title", 102)


def update():
    global game, paused
    select = badge.pressed(BUTTON_SELECT)
    back = badge.pressed(BUTTON_BACK)
    if game.status == "title":
        change = int(bool(badge.pressed(BUTTON_RIGHT))) - int(bool(badge.pressed(BUTTON_LEFT)))
        if change or back:
            seed = (game.seed * 17 + 7919) % 999999 + 1 if back else game.seed
            game = Game(seed, (game.start_biome + change) % 3)
        if select:
            game.start()
    elif game.status == "gameover":
        if select or back:
            game = Game(game.seed, game.start_biome)
            if select:
                game.start()
    elif game.status == "clear":
        if select:
            game.next_stage()
    else:
        if badge.pressed(BUTTON_MENU) and game.status == "play":
            paused = not paused
        if not paused:
            direction = int(bool(badge.held(BUTTON_RIGHT))) - int(bool(badge.held(BUTTON_LEFT)))
            vertical = int(bool(badge.held(BUTTON_DOWN))) - int(bool(badge.held(BUTTON_UP)))
            old_status = game.status
            game.update(badge.ticks_delta / 1000, direction, select,
                        bool(badge.held(BUTTON_SELECT)),
                        bool(badge.held(BUTTON_BACK)), vertical, shoot=back)
            if game.status != old_status and game.status in ("clear", "gameover"):
                save_best()
    draw_world()
    draw_overlay()
    display.blit(screen, rect(0, 0, screen.width * 1.5, screen.height * 1.5), image.NEAREST)


run(update)
