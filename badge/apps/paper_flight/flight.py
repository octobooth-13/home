"""Hardware-independent flight, tilt mapping, and endless gate generation."""

import math
import random


def clamp(value, low, high):
    return max(low, min(high, value))


def tilt_angles(ax, ay, az, inverted=False):
    """Return display-relative bank and physical pitch, independent of units."""
    if ax * ax + ay * ay + az * az < 1:
        return None
    sign = -1 if inverted else 1
    bank = math.atan2(sign * ax, math.sqrt(ay * ay + az * az))
    return bank, math.atan2(-az, abs(ay))


def tilt_axes(ax, ay, az, reference, inverted=False):
    """Measure steering relative to the pose captured for this flight."""
    angles = tilt_angles(ax, ay, az, inverted)
    if angles is None or reference is None:
        return None
    sign = -1 if inverted else 1
    bank = angles[0] - reference[0]
    pitch = sign * (angles[1] - reference[1])

    def response(angle):
        magnitude = max(0, abs(angle) - 0.06) / 0.48
        return clamp(magnitude, 0, 1) * (-1 if angle < 0 else 1)

    return response(bank), response(pitch)


class Flight:
    WING = 1.15
    NOSE = 1.3
    TAIL = -1.0
    THICKNESS = 0.7
    SPACING = 27.0
    POINTS = ((0, 0, NOSE), (-WING, 0.03, -0.85), (WING, 0.03, -0.85),
              (0, -0.22, -0.4), (0, 0, TAIL))

    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random
        self.reset()

    def reset(self):
        self.x = self.y = self.bank = self.pitch = 0.0
        self.distance = 0.0
        self.passed = 0
        self.alive = True
        self.gates = []
        self.route_x = self.route_y = 0.0
        for index in range(5):
            self.gates.append(self.make_gate(42.0 + index * self.SPACING))

    @property
    def speed(self):
        return min(32.0, 16.0 + self.distance / 220.0)

    def make_gate(self, z):
        self.route_x = clamp(self.route_x + self.rng.uniform(-3.2, 3.2), -6, 6)
        self.route_y = clamp(self.route_y + self.rng.uniform(-2.0, 2.0), -3, 3)
        difficulty = min(1.0, self.distance / 2500.0)
        return [self.route_x, self.route_y, z,
                3.3 - difficulty * 0.7, 2.6 - difficulty * 0.5]

    def advance(self, dt, bank, pitch):
        remaining = clamp(dt, 0, 0.1)
        while remaining > 0.000001 and self.alive:
            step = min(remaining, 1 / 120)
            self.step(step, clamp(bank, -1, 1), clamp(pitch, -1, 1))
            remaining -= step

    def vertices(self):
        pitch, bank = self.pitch * 0.3, self.bank * 0.65
        cp, sp = math.cos(pitch), math.sin(pitch)
        cb, sb = math.cos(bank), math.sin(bank)
        points = []
        for x, y, z in self.POINTS:
            py, pz = y * cp + z * sp, z * cp - y * sp
            points.append((x * cb + py * sb, -x * sb + py * cb, pz))
        return points

    def step(self, dt, bank, pitch):
        previous_vertices = self.vertices()
        smooth = 1 - math.exp(-dt / 0.14)
        self.bank += (bank - self.bank) * smooth
        self.pitch += (pitch - self.pitch) * smooth
        old_x, old_y = self.x, self.y
        self.x = clamp(self.x + self.bank * 8.0 * dt, -8.5, 8.5)
        self.y = clamp(self.y + self.pitch * 6.5 * dt, -4.8, 4.8)
        travel = self.speed * dt
        self.distance += travel
        vertices = previous_vertices + self.vertices()
        left = min(point[0] for point in vertices)
        right = max(point[0] for point in vertices)
        bottom = min(point[1] for point in vertices)
        top = max(point[1] for point in vertices)
        for gate in self.gates:
            old_z = gate[2]
            gate[2] -= travel
            # Sweep nose to tail through the whole wall, including its thickness.
            if old_z >= self.TAIL - self.THICKNESS and gate[2] <= self.NOSE:
                enter = clamp((old_z - self.NOSE) / travel, 0, 1)
                leave = clamp((old_z - self.TAIL + self.THICKNESS) / travel, 0, 1)
                for fraction in (enter, leave):
                    x = old_x + (self.x - old_x) * fraction
                    y = old_y + (self.y - old_y) * fraction
                    if (x + left < gate[0] - gate[3]
                            or x + right > gate[0] + gate[3]
                            or y + bottom < gate[1] - gate[4]
                            or y + top > gate[1] + gate[4]):
                        self.alive = False
                        return
                if gate[2] < self.TAIL - self.THICKNESS <= old_z:
                    self.passed += 1
        while self.gates[0][2] < -9:
            self.gates.pop(0)
            self.gates.append(self.make_gate(self.gates[-1][2] + self.SPACING))
