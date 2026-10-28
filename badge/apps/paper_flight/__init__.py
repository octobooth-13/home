"""Paper Flight: a small perspective skyway for the Universe 2026 badge."""

import math
import os
import sys

APP_DIR = "/system/apps/paper_flight"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from badgeware import State
from flight import Flight, clamp, tilt_angles, tilt_axes

badge.mode(LORES | VSYNC)
screen.antialias = image.OFF
screen.fill_rule = image.EVEN_ODD
screen.font = font.nope

INK = color.rgb(16, 29, 46)
SKY = color.rgb(23, 42, 59)
HAZE = color.rgb(32, 57, 70)
WALL = color.rgb(38, 79, 87)
EDGE = color.rgb(66, 116, 117)
MINT = color.rgb(132, 207, 183)
PAPER = color.rgb(247, 239, 215)
FOLD = color.rgb(184, 205, 194)

saved = {"best": 0}
State.load("paper_flight", saved)
flight = Flight()
mode = "title"
camera_x = camera_y = 0.0
imu_available = True
tilt_reference = None
launch_inverted = False
crashed_at = 0
preview_time = 0.0


def start():
    global mode, camera_x, camera_y, tilt_reference, launch_inverted
    launch_inverted = badge.rotate_180()
    tilt_reference = tilt_angles(*badge.imu()[:3], inverted=launch_inverted)
    flight.reset()
    camera_x = camera_y = 0.0
    mode = "flying"


def controls():
    global imu_available
    axes = tilt_axes(*badge.imu()[:3], reference=tilt_reference,
                     inverted=launch_inverted)
    imu_available = axes is not None
    bank, pitch = axes if axes is not None else (0.0, 0.0)
    horizontal = int(badge.held(BUTTON_RIGHT)) - int(badge.held(BUTTON_LEFT))
    vertical = int(badge.held(BUTTON_UP)) - int(badge.held(BUTTON_DOWN))
    return horizontal if horizontal else bank, vertical if vertical else pitch


def project(x, y, z):
    # Camera is behind, above, and just to the right of the paper airplane.
    dx, dy, dz = x - camera_x - 0.9, y - camera_y - 2.5, z + 7.0
    depth = -0.055 * dx - 0.155 * dy + 0.986 * dz
    if depth < 0.8:
        return None
    focal = screen.width * 0.78
    return (screen.width * 0.5 + focal * (0.998 * dx + 0.056 * dz) / depth,
            screen.height * 0.43 - focal * (-0.0087 * dx + 0.988 * dy + 0.1547 * dz) / depth)


def polygon(points, pen):
    if all(point is not None for point in points):
        screen.pen = pen
        screen.shape(shape.custom([vec2(point[0], point[1]) for point in points]))


def line(a, b, pen):
    if a is not None and b is not None:
        screen.pen = pen
        screen.line(a[0], a[1], b[0], b[1])


def panel(left, bottom, right, top, z, pen):
    polygon([project(left, bottom, z), project(right, bottom, z),
             project(right, top, z), project(left, top, z)], pen)


def draw_gate(gate, nearest):
    x, y, z, half_w, half_h = gate
    if z < -3.8:
        return
    left, right = x - half_w, x + half_w
    bottom, top = y - half_h, y + half_h
    shade = WALL if z < 65 else HAZE
    panel(-12, -8, left, 8, z, shade)
    panel(right, -8, 12, 8, z, shade)
    panel(left, top, right, 8, z, shade)
    panel(left, -8, right, bottom, z, shade)
    corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
    front = [project(cx, cy, z) for cx, cy in corners]
    rear = [project(cx, cy, z + Flight.THICKNESS) for cx, cy in corners]
    for index in range(4):
        following = (index + 1) % 4
        polygon([front[index], rear[index], rear[following], front[following]], EDGE)
        line(front[index], front[following], MINT if nearest else EDGE)
    # Corner ticks keep the next opening readable against distant gates.
    if nearest:
        for cx, cy in corners:
            sx = 0.32 if cx == left else -0.32
            sy = -0.32 if cy == top else 0.32
            line(project(cx, cy, z), project(cx + sx, cy, z), PAPER)
            line(project(cx, cy, z), project(cx, cy + sy, z), PAPER)


def draw_plane():
    nose, left, right, fold, tail = [
        project(flight.x + x, flight.y + y, z) for x, y, z in flight.vertices()
    ]
    polygon([nose, left, tail], PAPER)
    polygon([nose, tail, right], FOLD)
    polygon([nose, fold, tail], MINT)
    for a, b in ((nose, left), (left, tail), (tail, right), (right, nose)):
        line(a, b, INK)
    line(nose, tail, EDGE)


def centered(text, y, pen=PAPER):
    screen.pen = pen
    width, _ = screen.measure_text(text)
    screen.text(text, (screen.width - width) / 2, y)


def draw_world():
    screen.pen = SKY
    screen.rectangle(screen.clip)
    screen.pen = HAZE
    screen.rectangle(0, int(screen.height * 0.43), screen.width, int(screen.height * 0.57) + 1)
    horizon = screen.height * 0.43 - camera_y * 0.35
    screen.pen = EDGE
    screen.line(0, horizon, screen.width, horizon)
    # Ground lines and dashes provide depth and speed without texture assets.
    for x in (-12, -6, 0, 6, 12):
        line(project(x, -7, -3), project(x, -7, 150), HAZE)
    for index in range(9):
        z = (index * 18 - flight.distance % 18)
        for x in (-9, 9):
            line(project(x, -2.5, z), project(x, -2.5, z + 2.5), EDGE)
    next_gate = next((g for g in flight.gates if g[2] > Flight.NOSE), None)
    for gate in reversed(flight.gates):
        if gate[2] > Flight.NOSE:
            draw_gate(gate, gate is next_gate)
    draw_plane()
    # Walls in front of the airplane correctly occlude its wings on impact.
    for gate in reversed(flight.gates):
        if gate[2] <= Flight.NOSE:
            draw_gate(gate, False)


def hud():
    screen.pen = INK
    screen.rectangle(0, 0, screen.width, 12)
    screen.pen = PAPER
    screen.text("%dm" % flight.distance, 4, 2)
    label = "%d GATES" % flight.passed
    width, _ = screen.measure_text(label)
    screen.pen = MINT
    screen.text(label, screen.width - width - 4, 2)
    if not imu_available and mode in ("flying", "paused"):
        centered("NO TILT - USE ARROWS", screen.height - 11, MINT)


def overlay(title, lines):
    top = int(screen.height * 0.15)
    screen.pen = INK
    screen.rectangle(5, top, screen.width - 10, 70)
    screen.pen = MINT
    screen.rectangle(5, top, 2, 70)
    centered(title, top + 5, MINT)
    for index, text in enumerate(lines):
        centered(text, top + 20 + index * 11)


def update():
    global mode, camera_x, camera_y, crashed_at, preview_time
    dt = clamp(badge.ticks_delta / 1000, 0, 0.1)
    bank, pitch = controls()
    if mode == "title":
        preview_time += dt
        flight.bank = math.sin(preview_time) * 0.25
        if badge.pressed(BUTTON_SELECT):
            start()
    elif mode == "flying":
        if badge.pressed(BUTTON_SELECT) or badge.pressed(BUTTON_BACK):
            mode = "paused"
        else:
            flight.advance(dt, bank, pitch)
            if not flight.alive:
                mode = "crashed"
                crashed_at = badge.ticks
                if int(flight.distance) > saved["best"]:
                    saved["best"] = int(flight.distance)
                    State.save("paper_flight", saved)
    elif mode == "paused":
        if badge.pressed(BUTTON_SELECT):
            mode = "flying"
        elif badge.pressed(BUTTON_BACK):
            mode = "title"
            flight.reset()
    elif mode == "crashed" and badge.ticks - crashed_at > 500:
        if badge.pressed(BUTTON_SELECT):
            start()
        elif badge.pressed(BUTTON_BACK):
            mode = "title"
            flight.reset()

    follow = 1 - math.exp(-dt / 0.22)
    camera_x += (flight.x - camera_x) * follow
    camera_y += (flight.y - camera_y) * follow
    draw_world()
    hud()
    if mode == "title":
        overlay("PAPER FLIGHT", ("Hold comfy & still",
                "Tilt: bank / pitch", "Aim for the gaps", "SELECT  -  launch"))
        centered("BEST %dm" % saved["best"], screen.height - 13, MINT)
    elif mode == "paused":
        overlay("FLIGHT PAUSED", ("SELECT  -  resume", "BACK  -  title",
                "Tilt or use arrows", "HOME  -  badge menu"))
    elif mode == "crashed":
        overlay("FOLDED!", ("%dm   /   %d gates" % (flight.distance, flight.passed),
                "BEST %dm" % saved["best"], "SELECT  -  fly again", "BACK  -  title"))

run(update)
