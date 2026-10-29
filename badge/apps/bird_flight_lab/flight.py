"""Small SI-unit flight model, independent of the badge graphics runtime."""

import math


GRAVITY = 9.81
DENSITY = 1.225
MASS_FACTORS = (0.5, 0.75, 1.0, 1.5, 2.0)
SPAN_FACTORS = (0.7, 0.85, 1.0, 1.15, 1.3)
POWER_LEVELS = (35, 60, 90, 130, 180)
WINDS = (-4, 0, 4, 8)
THERMALS = (0, 1, 3, 5)
# Name, aspect ratio, maximum lift coefficient, profile drag coefficient.
WINGS = (
    ("Broad", 5.0, 1.65, 0.055),
    ("Tapered", 7.0, 1.4, 0.035),
    ("Slender", 11.0, 1.15, 0.025),
)
# Name, rounded mass (kg), full span (m), model wing index, model power index.
PRESETS = (
    ("Peregrine Falcon", 0.9, 1.05, 1, 4),
    ("Common Loon", 4.5, 1.3, 1, 4),
    ("Barn Swallow", 0.019, 0.31, 2, 3),
    ("Ring-necked Pheasant", 1.2, 0.75, 0, 4),
    ("Green Heron", 0.24, 0.66, 0, 2),
    ("Bald Eagle", 4.5, 2.1, 0, 2),
    ("Red-tailed Hawk", 1.1, 1.25, 0, 2),
    ("Mallard", 1.1, 0.9, 1, 3),
    ("Canada Goose", 4.0, 1.6, 1, 2),
    ("Ruby-throated Hummingbird", 0.0032, 0.10, 1, 4),
    ("Belted Kingfisher", 0.15, 0.55, 1, 3),
    ("Pileated Woodpecker", 0.30, 0.72, 0, 3),
)
DEFAULT_PRESET = 7
PHASES = ("Takeoff", "Speed up", "Soar", "Dive", "Land", "Finished")
LIMITS = (len(PRESETS), len(MASS_FACTORS), len(SPAN_FACTORS), len(WINGS),
          len(POWER_LEVELS), len(WINDS), len(THERMALS))


def selections(preset=DEFAULT_PRESET):
    bird = PRESETS[preset]
    return [preset, 2, 2, bird[3], bird[4], 1, 0]


def parameters(choices):
    bird = PRESETS[choices[0]]
    wing = WINGS[choices[3]]
    mass = bird[1] * MASS_FACTORS[choices[1]]
    span = bird[2] * SPAN_FACTORS[choices[2]]
    area = span * span / wing[1]
    return {
        "name": bird[0],
        "mass": mass,
        "span": span,
        "area": area,
        "aspect": wing[1],
        "cl_max": wing[2],
        "cd0": wing[3],
        "power": POWER_LEVELS[choices[4]] * mass,
        "wind": WINDS[choices[5]],
        "thermal": THERMALS[choices[6]],
        "stall": math.sqrt(2 * mass * GRAVITY / (DENSITY * area * wing[2])),
    }


class Flight:
    def __init__(self, config):
        self.config = config
        self.phase = 0
        self.phase_time = 0.0
        self.time = 0.0
        self.speed = max(0.0, config["wind"])
        self.ground_speed = 0.0
        self.height = 0.0
        self.distance = 0.0
        self.vertical = 0.0
        self.energy = 1.0
        self.lift_ratio = 0.0
        self.peak_speed = 0.0
        self.peak_height = 0.0
        self.takeoff_distance = 0.0
        self.soar_change = 0.0
        self.soar_start = 0.0
        self.outcome = ""
        self.reason = ""
        self.visited = [0]
        self.stalled = False
        self._pending = 0.0

    def drag(self, speed, landing=False):
        p = self.config
        pressure = 0.5 * DENSITY * max(speed, 0.5) ** 2
        lift_coefficient = min(p["cl_max"], p["mass"] * GRAVITY / (pressure * p["area"]))
        induced = lift_coefficient ** 2 / (math.pi * 0.8 * p["aspect"])
        return pressure * p["area"] * (p["cd0"] + induced + (0.16 if landing else 0))

    def advance_phase(self):
        if self.phase == 2:
            self.soar_change = self.height - self.soar_start
        self.phase += 1
        self.phase_time = 0.0
        self.visited.append(self.phase)
        if self.phase == 2:
            self.soar_start = self.height

    def finish(self, outcome, reason):
        if self.phase == 2:
            self.soar_change = self.height - self.soar_start
        self.phase = 5
        self.outcome = outcome
        self.reason = reason
        self.ground_speed = 0.0

    def step(self, seconds):
        # Fixed-size substeps keep fast playback and slow displays consistent.
        if self.phase == 5:
            return
        self._pending += seconds
        while self._pending + 0.000000001 >= 0.01 and self.phase < 5:
            self._pending -= 0.01
            self._step(0.01)

    def _step(self, dt):
        p = self.config
        mass = p["mass"]
        weight = mass * GRAVITY
        available = p["power"] * 0.72 if self.energy > 0 else 0.0
        self.time += dt
        self.phase_time += dt
        used = available
        stall = p["stall"]
        if self.phase == 0:
            thrust = available / max(self.speed, 4.0)
            drag = 0.5 * DENSITY * self.speed ** 2 * p["area"] * p["cd0"]
            acceleration = (thrust - drag - weight * 0.04) / mass
            self.ground_speed = max(0.0, self.ground_speed + acceleration * dt)
            self.speed = max(0.0, self.ground_speed + p["wind"])
            self.distance += self.ground_speed * dt
            self.lift_ratio = (self.speed / stall) ** 2
            if self.speed >= stall * 1.12 and available - self.drag(self.speed) * self.speed > weight * 0.35:
                self.takeoff_distance = self.distance
                self.height = 0.2
                self.advance_phase()
            elif self.phase_time >= 12 or self.distance >= 120:
                self.finish("Cannot take off", "120 m / 12 s runway limit")
        else:
            drag = self.drag(self.speed, self.phase == 4)
            sink = drag * self.speed / weight
            if self.phase == 1:
                target = stall * 1.55
                climb = min(2.5, max(0.0, (available - drag * self.speed) / weight) * 0.5)
                self.vertical = climb + p["thermal"]
            elif self.phase == 2:
                used = 0.0
                self.vertical = p["thermal"] - sink
            elif self.phase == 3:
                used = 0.0
                self.vertical = -max(2.0, self.speed * 0.28)
            else:
                target = stall * 1.12
                self.vertical = -min(2.0, self.height * 0.22 + 0.25)
            if self.phase in (1, 4):
                requested = drag * self.speed + weight * (self.vertical - p["thermal"])
                requested += mass * self.speed * (target - self.speed) * 0.9
                used = min(available, max(0.0, requested))
            acceleration = (used - drag * self.speed - weight * (self.vertical - p["thermal"])) / (mass * max(self.speed, 3.0))
            self.speed = max(0.5, self.speed + acceleration * dt)
            self.lift_ratio = (self.speed / stall) ** 2
            self.stalled = self.lift_ratio < 1.0
            if self.stalled:
                self.vertical -= (1.0 - self.lift_ratio) * 5.0
            self.height = max(0.0, self.height + self.vertical * dt)
            self.ground_speed = self.speed - p["wind"]
            self.distance += self.ground_speed * dt
            if self.height <= 0:
                gentle = self.phase == 4 and self.vertical > -1.5 and not self.stalled and self.speed < stall * 1.45
                self.finish("Soft landing" if gentle else "Hard landing",
                            "Flight sequence complete" if gentle else "Low lift or fast touchdown")
            elif self.energy <= 0 and self.phase != 4:
                self.phase = 4
                self.phase_time = 0.0
                self.visited.append(4)
            elif self.phase == 1 and self.phase_time >= 10:
                self.advance_phase()
            elif self.phase == 2 and self.phase_time >= 10:
                self.advance_phase()
            elif self.phase == 3 and (self.phase_time >= 4 or self.height < 6):
                self.advance_phase()
            elif self.phase == 4 and self.phase_time >= 90:
                self.finish("Landing incomplete", "Descent exceeded time limit")
        self.energy = max(0.0, self.energy - used * dt / (mass * 20000))
        self.peak_speed = max(self.peak_speed, self.speed)
        self.peak_height = max(self.peak_height, self.height)
