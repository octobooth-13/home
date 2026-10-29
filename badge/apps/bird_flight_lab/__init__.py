"""Bird Flight Lab: adjustable birds and an animated educational flight model."""

import math
import os
import sys

APP_DIR = "/system/apps/bird_flight_lab"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from flight import Flight, LIMITS, PHASES, POWER_LEVELS, PRESETS, WINGS, parameters, selections

badge.mode(HIRES | VSYNC)
screen.font = font.nope
screen.fill_rule = image.EVEN_ODD
screen.antialias = image.X2

BG = color.rgb(13, 24, 39)
PANEL = color.rgb(27, 44, 61)
WHITE = color.rgb(235, 244, 246)
MUTED = color.rgb(151, 181, 195)
GREEN = color.rgb(181, 241, 121)
GOLD = color.rgb(255, 202, 111)
SKY = color.rgb(39, 82, 108)
choices = selections()
row = 0
view = "setup"
flight = None
paused = False
playback = 1
trail = []
trail_time = 0.0
LABELS = ("Bird preset", "Body mass", "Wingspan", "Wing shape", "Muscle power", "Wind", "Thermal")
NOTES = (
    "Preset resets body, wings and power.",
    "More mass needs more lift to fly.",
    "Longer wings lower stall speed.",
    "Broad: lift. Slender: efficient glide.",
    "Mechanical power per kg of body.",
    "Headwind helps runway takeoff.",
    "Rising air supports unpowered flight.",
)


def text(label, x, y, pen=WHITE):
    screen.pen = pen
    screen.text(label, x, y)


def box(x, y, width, height, pen):
    screen.pen = pen
    screen.shape(shape.rectangle(x, y, width, height))


def line(x1, y1, x2, y2, pen):
    screen.pen = pen
    screen.line(x1, y1, x2, y2)


def bird(x, y, size, flap=0.0, diving=False):
    screen.pen = GOLD
    screen.shape(shape.ellipse(x, y, size * 0.46, size * 0.17))
    screen.shape(shape.circle(x + size * 0.38, y - size * 0.1, size * 0.15))
    screen.pen = WHITE
    lift = size * (0.25 + flap * 0.65)
    reach = (0.55, 0.75, 1.0)[choices[3]]
    if diving:
        lift *= 0.3
    screen.shape(shape.custom([
        vec2(x - size * 0.2, y), vec2(x - size * reach, y - lift),
        vec2(x + size * 0.12, y - lift * 0.5), vec2(x + size * 0.2, y),
    ]))
    line(x - size * 0.3, y, x - size * 0.72, y - size * 0.12, GOLD)
    line(x - size * 0.3, y, x - size * 0.7, y + size * 0.18, GOLD)
    line(x + size * 0.5, y - size * 0.1, x + size * 0.68, y - size * 0.03, GOLD)
    screen.pen = BG
    screen.shape(shape.circle(x + size * 0.41, y - size * 0.14, max(1, size * 0.035)))


def start():
    global flight, view, paused, trail, trail_time
    flight = Flight(parameters(choices))
    view = "flight"
    paused = False
    trail = []
    trail_time = 0.0


def change(direction):
    global choices
    choices[row] = (choices[row] + direction) % LIMITS[row]
    if row == 0:
        choices = selections(choices[0])


def setup():
    p = parameters(choices)
    text("BIRD FLIGHT LAB", 12, 10, GREEN)
    text("Otter Tail birds  %d/%d" % (choices[0] + 1, len(PRESETS)), 12, 28, MUTED)
    if p["mass"] < 0.01:
        mass_label = "%.1f g" % (p["mass"] * 1000)
    elif p["mass"] < 1:
        mass_label = "%d g" % round(p["mass"] * 1000)
    else:
        mass_label = "%.2f kg" % p["mass"]
    values = (
        p["name"],
        mass_label,
        "%.2f m" % p["span"],
        WINGS[choices[3]][0],
        "%d W/kg" % POWER_LEVELS[choices[4]],
        ("Tail 4 m/s", "Calm", "Head 4 m/s", "Head 8 m/s")[choices[5]],
        "+%d m/s" % p["thermal"],
    )
    for index, label in enumerate(LABELS):
        y = 52 + index * 19
        if index == row:
            box(8, y - 3, screen.width - 16, 18, PANEL)
            text(">", 12, y, GREEN)
        if index == 0:
            text(values[index], 27, y)
        else:
            text(label, 27, y, GREEN if index == row else MUTED)
            text(values[index], 181, y)
    text(NOTES[row], 12, 188, GOLD)
    text("Stall %.1f m/s | Loading %.0f N/m2" % (p["stall"], p["mass"] * 9.81 / p["area"]), 12, 203, MUTED)
    text("UP/DN choose  L/R change  SEL fly", 12, screen.height - 18, GREEN)


def scene():
    width = screen.width
    ground = 153
    box(0, 45, width, 119, SKY)
    for index in range(5):
        x = (index * 89 - flight.distance * 0.4) % (width + 60) - 30
        screen.pen = color.rgb(76, 118, 139)
        screen.shape(shape.ellipse(x, 65 + index % 2 * 15, 22, 4))
    for index in range(9):
        x = (index * 49 - flight.distance * 2) % (width + 40) - 20
        line(x, ground, x + 24, ground - 8 - index % 3 * 5, MUTED)
    box(0, ground, width, 12, PANEL)
    scale = max(0.5, 70.0 / max(30.0, flight.peak_height))
    y = ground - 7 - flight.height * scale
    for index, point in enumerate(trail):
        tx = 104 - (flight.distance - point[0]) * 1.5
        ty = ground - 7 - point[1] * scale
        if 0 < tx < width and 48 < ty < ground:
            box(tx, ty, 2, 2, MUTED)
    if flight.config["thermal"] > 0:
        for index in range(3):
            x = 225 + index * 22
            ay = 140 - ((flight.time * 17 + index * 14) % 70)
            line(x, ay + 15, x, ay, GREEN)
            line(x, ay, x - 3, ay + 4, GREEN)
            line(x, ay, x + 3, ay + 4, GREEN)
    flapping = flight.phase in (0, 1, 4)
    flap = math.sin(flight.time * 13) if flapping else 0.5
    size = 17 + choices[2] * 2
    bird(104, y, size, flap, flight.phase == 3)
    if flight.phase == 0:
        text("RUNWAY  %d / 120 m" % flight.distance, 12, 50)
    elif flight.stalled:
        text("STALL: insufficient lift", 12, 50, GOLD)
    elif flight.phase == 2:
        text("WINGS OPEN / NO FLAPPING", 12, 50, GREEN)
    elif flight.phase == 3:
        text("GRAVITY / NO FLAPPING", 12, 50, GOLD)


def flight_view():
    text(PHASES[flight.phase].upper(), 12, 9, GREEN)
    status = "PAUSED" if paused else "%dx" % playback
    status_width, _ = screen.measure_text(status)
    text(status, screen.width - status_width - 12, 9, GOLD)
    text(flight.config["name"], 12, 24, MUTED)
    for index in range(5):
        box(12 + index * 61, 39, 52, 4, GREEN if index <= flight.phase else PANEL)
    scene()
    text("AIR %.1f m/s" % flight.speed, 12, 172)
    text("ALT %.1f m" % flight.height, 175, 172)
    text("GROUND %.1f m/s" % flight.ground_speed, 12, 188, MUTED)
    text("V/S %+.1f m/s" % flight.vertical, 175, 188, MUTED)
    text("LIFT MAX %.1fx" % flight.lift_ratio, 12, 204, GOLD)
    text("ENERGY %d%%" % (flight.energy * 100), 175, 204, GREEN)
    text("SEL pause  R 1x/3x  BACK edit", 12, screen.height - 17, MUTED)


def results():
    text("FLIGHT REPORT", 12, 12, GREEN)
    bird(screen.width - 42, 33, 23, 0.6)
    text(flight.outcome, 12, 38, GOLD)
    text(flight.reason, 12, 58, MUTED)
    metrics = (
        ("Takeoff run", "%.1f m" % flight.takeoff_distance if 1 in flight.visited else "Not airborne"),
        ("Peak airspeed", "%.1f m/s" % flight.peak_speed),
        ("Peak altitude", "%.1f m" % flight.peak_height),
        ("Soar height change", "%+.1f m" % flight.soar_change if 2 in flight.visited else "Not reached"),
        ("Energy remaining", "%d%%" % (flight.energy * 100)),
        ("Flight time", "%.1f s" % flight.time),
    )
    for index, (label, value) in enumerate(metrics):
        y = 84 + index * 19
        text(label, 12, y, MUTED)
        text(value, 203, y)
    text("Educational model, not bird predictions.", 12, 204, GOLD)
    text("SEL replay  BACK change selections", 12, screen.height - 18, GREEN)


def update():
    global view, row, paused, playback, trail_time
    box(0, 0, screen.width, screen.height, BG)
    if view == "setup":
        if badge.pressed(BUTTON_UP):
            row = (row - 1) % len(LABELS)
        if badge.pressed(BUTTON_DOWN):
            row = (row + 1) % len(LABELS)
        if badge.pressed(BUTTON_LEFT):
            change(-1)
        if badge.pressed(BUTTON_RIGHT):
            change(1)
        if badge.pressed(BUTTON_SELECT):
            start()
    elif badge.pressed(BUTTON_BACK):
        view = "setup"
    elif badge.pressed(BUTTON_SELECT):
        if view == "results":
            start()
        else:
            paused = not paused
    if view == "flight":
        if badge.pressed(BUTTON_RIGHT):
            playback = 3 if playback == 1 else 1
        if not paused:
            dt = min(0.25, max(0, badge.ticks_delta / 1000)) * playback
            flight.step(dt)
            trail_time += dt
            if trail_time >= 0.2:
                trail.append((flight.distance, flight.height))
                if len(trail) > 40:
                    trail.pop(0)
                trail_time = 0.0
        if flight.phase == 5:
            view = "results"
    if view == "setup":
        setup()
    elif view == "flight":
        flight_view()
    else:
        results()


run(update)
