"""Host-only rules and compact, atomic state snapshots; no firmware imports."""

import random
import struct

WIDTH, HEIGHT = 320, 240
TOP, BOTTOM = 34, 214
COLS, ROWS = 6, 10
WALL_X, BRICK_W, BRICK_H = 124, 12, 18
BASIC, RAPID, DRILL, SCATTER, ROCKET = range(5)
SHIELD, DASH, REPAIR, STRONG_SHIELD = range(5, 9)
NAMES = ("BLASTER", "RAPID", "DRILL", "SCATTER", "ROCKET",
         "SHIELD", "DASH", "REPAIR", "SHIELD+")
GLYPHS = ("B", "R", "D", "S", "!", "O", "^", "+", "O+")
UP, DOWN, FIRE = 1, 2, 4
COUNTDOWN, PLAY, ROUND_OVER, MATCH_OVER = range(4)
PLAYER_FORMAT = "<HBBBBHHH"
SHOT_FORMAT = "<HHhhBBBB"


def clamp(value, low, high):
    return max(low, min(high, value))


class Player:
    def __init__(self):
        self.y = 124.0
        self.hp = 5
        self.weapon = BASIC
        self.weapon_time = 0.0
        self.defense = 0
        self.shield = 0
        self.cooldown = 0.0
        self.dash_time = 0.0
        self.dash_cooldown = 0.0
        self.direction = -1


class Arena:
    def __init__(self):
        self.match = 0
        self.scores = [0, 0]
        self.round_number = 0
        self.new_round()

    def new_round(self):
        self.round_number += 1
        self.players = [Player(), Player()]
        self.bricks = [8] * (COLS * ROWS)
        self.supply = [0] * len(self.bricks)
        for row in range(ROWS):
            column = random.randrange(COLS)
            index = row * COLS + column
            self.bricks[index] = 12
            # Strong shields are deliberately rarer than other drops.
            self.supply[index] = random.choice(
                (RAPID, DRILL, SCATTER, ROCKET, SHIELD, DASH, REPAIR,
                 RAPID, SHIELD, STRONG_SHIELD))
        self.shots = []
        self.drops = []
        self.effects = []
        self.phase = COUNTDOWN
        self.phase_time = 3.0
        self.remaining = 90.0
        self.sudden = False
        self.link_paused = False
        self.winner = -1

    def new_match(self):
        self.match = (self.match + 1) & 65535
        self.scores = [0, 0]
        self.round_number = 0
        self.new_round()

    def activate(self, side):
        if self.phase != PLAY:
            return
        player = self.players[side]
        item = player.defense
        if item == DASH and player.dash_cooldown > 0:
            return
        if item in (SHIELD, STRONG_SHIELD):
            player.shield = 2 if item == STRONG_SHIELD else 1
        elif item == DASH:
            player.dash_time = 0.14
            player.dash_cooldown = 0.8
        elif item == REPAIR:
            player.hp = min(5, player.hp + 1)
        else:
            return
        player.defense = 0

    def shoot(self, side):
        player = self.players[side]
        kind = player.weapon
        player.cooldown = (0.28, 0.10, 1.05, 0.65, 1.3)[kind]
        direction = 1 if side == 0 else -1
        speed = (155, 180, 85, 145, 70)[kind]
        for slope in ((-0.42, 0, 0.42) if kind == SCATTER else (0,)):
            if len(self.shots) >= 32:
                break
            # x, y, vx, vy, owner, kind, remaining range, pierces.
            self.shots.append([24 if side == 0 else 296, player.y,
                               speed * direction, speed * slope, side, kind,
                               170.0 if kind == SCATTER and slope else 340.0,
                               4 if kind == DRILL else 1])

    def damage_brick(self, index, damage, side):
        if not self.bricks[index]:
            return
        self.bricks[index] = max(0, self.bricks[index] - damage)
        if not self.bricks[index] and self.supply[index]:
            if len(self.drops) < 12:
                self.drops.append([WALL_X + (index % COLS + 0.5) * BRICK_W,
                                   TOP + (index // COLS + 0.5) * BRICK_H,
                                   self.supply[index], side])
            self.supply[index] = 0

    def explode(self, x, y, side):
        self.effects.append([x, y, 0.25])
        self.effects = self.effects[-8:]
        for index, hp in enumerate(self.bricks):
            bx = WALL_X + (index % COLS + 0.5) * BRICK_W
            by = TOP + (index // COLS + 0.5) * BRICK_H
            if hp and (bx - x) ** 2 + (by - y) ** 2 <= 25 ** 2:
                self.damage_brick(index, 6, side)

    def finish_round(self, winner):
        self.winner = winner
        self.scores[winner] += 1
        self.phase = MATCH_OVER if self.scores[winner] == 2 else ROUND_OVER
        self.phase_time = 2.5
        self.shots = []

    def step(self, dt, controls):
        # Small substeps prevent fast shots and dashes tunnelling through targets.
        dt = clamp(dt, 0, 0.1)
        while dt > 0:
            part = min(dt, 1 / 120)
            self.advance(part, controls)
            dt -= part

    def advance(self, dt, controls):
        if self.phase in (COUNTDOWN, ROUND_OVER):
            self.phase_time -= dt
            if self.phase_time <= 0:
                if self.phase == ROUND_OVER:
                    self.new_round()
                else:
                    self.phase = PLAY
            return
        if self.phase != PLAY:
            return
        for side, player in enumerate(self.players):
            flags = controls[side]
            move = bool(flags & DOWN) - bool(flags & UP)
            if move:
                player.direction = move
            speed = 440 if player.dash_time > 0 else 105
            movement = player.direction if player.dash_time > 0 else move
            player.y = clamp(player.y + movement * speed * dt, TOP + 10, BOTTOM - 10)
            player.dash_time = max(0, player.dash_time - dt)
            player.dash_cooldown = max(0, player.dash_cooldown - dt)
            player.weapon_time = max(0, player.weapon_time - dt)
            if not player.weapon_time:
                player.weapon = BASIC
            player.cooldown = max(0, player.cooldown - dt)
            if flags & FIRE and not player.cooldown:
                self.shoot(side)

        live = []
        for shot in self.shots:
            x, y, vx, vy, side, kind, distance, pierces = shot[:8]
            nx, ny = x + vx * dt, y + vy * dt
            shot[0], shot[1] = nx, ny
            shot[6] -= abs(vx * dt)
            if not TOP <= ny <= BOTTOM or shot[6] <= 0 or not 0 <= nx <= WIDTH:
                continue
            index = -1
            if WALL_X <= nx < WALL_X + COLS * BRICK_W:
                index = int((ny - TOP) // BRICK_H) * COLS + int((nx - WALL_X) // BRICK_W)
                if 0 <= index < len(self.bricks) and self.bricks[index]:
                    # Remember the last brick so a drill hits each brick only once.
                    previous = shot[8] if len(shot) > 8 else -1
                    if previous != index:
                        damage = (2, 1, 5, 1, 6)[kind]
                        self.damage_brick(index, damage, side)
                        if kind == ROCKET:
                            self.explode(nx, ny, side)
                        pierces -= 1
                        shot[7] = pierces
                        if len(shot) == 8:
                            shot.append(index)
                        else:
                            shot[8] = index
                        if not pierces:
                            continue
            target = self.players[1 - side]
            face = 296 if side == 0 else 24
            crossed = x <= face <= nx if side == 0 else nx <= face <= x
            if crossed and abs(ny - target.y) <= 11:
                if target.shield:
                    target.shield -= 1
                else:
                    target.hp = max(0, target.hp - (5 if self.sudden else 1))
                if kind == ROCKET:
                    self.explode(nx, ny, side)
                continue
            live.append(shot)
        self.shots = live

        live = []
        for drop in self.drops:
            side = drop[3]
            drop[0] += (-58 if side == 0 else 58) * dt
            player = self.players[side]
            if (drop[0] <= 24 if side == 0 else drop[0] >= 296):
                if abs(drop[1] - player.y) <= 14:
                    if drop[2] <= ROCKET:
                        player.weapon, player.weapon_time = drop[2], 10.0
                    else:
                        player.defense = drop[2]
                continue
            live.append(drop)
        self.drops = live
        self.effects = [[x, y, life - dt] for x, y, life in self.effects if life > dt]

        dead = [i for i, p in enumerate(self.players) if p.hp <= 0]
        if len(dead) == 1:
            self.finish_round(1 - dead[0])
            return
        if len(dead) == 2:
            # Simultaneous hits are a draw: replay sudden death, no free point.
            self.players[0].hp = self.players[1].hp = 1
            self.enter_sudden()
            return
        self.remaining = max(0, self.remaining - dt)
        if not self.remaining and not self.sudden:
            if self.players[0].hp != self.players[1].hp:
                self.finish_round(int(self.players[1].hp > self.players[0].hp))
            else:
                self.enter_sudden()

    def enter_sudden(self):
        self.sudden = True
        self.bricks = [0] * len(self.bricks)
        self.supply = [0] * len(self.supply)
        self.shots = []
        self.drops = []
        for player in self.players:
            player.shield = 0
            player.defense = 0

    def snapshot(self):
        data = bytearray(struct.pack(
            "<HBBBBBHBB", self.match, self.phase, self.scores[0], self.scores[1],
            self.round_number, int(self.sudden) | (2 if self.link_paused else 0), round(self.remaining * 10),
            round(max(0, self.phase_time) * 10), self.winner + 1))
        for p in self.players:
            data.extend(struct.pack(PLAYER_FORMAT, round(p.y * 16), p.hp, p.weapon,
                                    p.defense, p.shield, round(p.weapon_time * 100),
                                    round(p.dash_time * 1000), round(p.dash_cooldown * 1000)))
        data.extend(bytes(self.bricks))
        data.extend(bytes(self.supply))
        data.append(len(self.shots))
        for s in self.shots:
            data.extend(struct.pack(SHOT_FORMAT, round(s[0] * 16), round(s[1] * 16),
                                    round(s[2]), round(s[3]), s[4], s[5],
                                    clamp(round(s[6]), 0, 255), s[7]))
        data.append(len(self.drops))
        for x, y, kind, side in self.drops:
            data.extend(struct.pack("<HHBB", round(x * 16), round(y * 16), kind, side))
        return bytes(data)

    def restore(self, data):
        # Decode to a temporary model so truncated packets never mutate the view.
        other = Arena.__new__(Arena)
        other.players = [Player(), Player()]
        other.effects = []
        header = struct.unpack("<HBBBBBHBB", data[:11])
        (other.match, other.phase, a, b, other.round_number, sudden,
         remaining, phase_time, winner) = header
        other.scores = [a, b]
        other.sudden = bool(sudden & 1)
        other.link_paused = bool(sudden & 2)
        other.remaining, other.phase_time = remaining / 10, phase_time / 10
        other.winner = winner - 1
        offset = 11
        for p in other.players:
            fields = struct.unpack(PLAYER_FORMAT, data[offset:offset + 12])
            y, p.hp, p.weapon, p.defense, p.shield, weapon, dash, cooldown = fields
            if (p.hp > 5 or p.weapon > ROCKET or
                    (p.defense != 0 and not SHIELD <= p.defense <= STRONG_SHIELD) or
                    p.shield > 2 or weapon > 1000 or dash > 140 or cooldown > 800):
                raise ValueError("Invalid player snapshot")
            p.y, p.weapon_time = y / 16, weapon / 100
            if not TOP + 10 <= p.y <= BOTTOM - 10:
                raise ValueError("Invalid ship position")
            p.dash_time, p.dash_cooldown = dash / 1000, cooldown / 1000
            offset += 12
        other.bricks = list(data[offset:offset + 60])
        other.supply = list(data[offset + 60:offset + 120])
        if (len(other.bricks) != 60 or len(other.supply) != 60 or
                any(hp > 12 for hp in other.bricks) or
                any(kind > STRONG_SHIELD for kind in other.supply)):
            raise ValueError("Invalid wall snapshot")
        offset += 120
        other.shots = []
        count = data[offset]
        offset += 1
        if count > 32:
            raise ValueError("Too many projectiles")
        for _ in range(count):
            fields = list(struct.unpack(SHOT_FORMAT, data[offset:offset + 12]))
            fields[0] /= 16
            fields[1] /= 16
            if (fields[4] > 1 or fields[5] > ROCKET or
                    not 0 <= fields[0] <= WIDTH or not TOP <= fields[1] <= BOTTOM):
                raise ValueError("Invalid projectile snapshot")
            other.shots.append(fields)
            offset += 12
        other.drops = []
        count = data[offset]
        offset += 1
        if count > 12:
            raise ValueError("Too many drops")
        for _ in range(count):
            x, y, kind, side = struct.unpack("<HHBB", data[offset:offset + 6])
            if (not RAPID <= kind <= STRONG_SHIELD or side > 1 or
                    not 0 <= x / 16 <= WIDTH or not TOP <= y / 16 <= BOTTOM):
                raise ValueError("Invalid capsule snapshot")
            other.drops.append([x / 16, y / 16, kind, side])
            offset += 6
        if (offset != len(data) or other.phase > MATCH_OVER or sudden > 3 or
                a > 2 or b > 2 or winner > 2 or not 1 <= other.round_number <= 3 or
                remaining > 900 or phase_time > 30):
            raise ValueError("Invalid snapshot length or phase")
        self.__dict__.update(other.__dict__)


def newer(sequence, previous):
    return previous is None or 0 < ((sequence - previous) & 65535) < 32768


def packets(sequence, data, capacity=85):
    size = min(85, capacity) - 5
    if size < 7:
        raise ValueError("Breach requires a link capacity of at least 12 bytes")
    count = (len(data) + size - 1) // size
    if count > 128:
        raise ValueError("Breach snapshot exceeds transport limit")
    return [b"S" + struct.pack("<HBB", sequence, part, count) + data[part * size:(part + 1) * size]
            for part in range(count)]


class Assembler:
    def __init__(self):
        self.latest = None
        self.sequence = None
        self.parts = {}
        self.count = 0

    def feed(self, message):
        if len(message) < 6 or message[:1] != b"S":
            raise ValueError("Invalid state packet")
        sequence, part, count = struct.unpack("<HBB", message[1:5])
        if not 1 <= count <= 128 or part >= count or len(message) > 85:
            raise ValueError("Invalid state fragment")
        if not newer(sequence, self.latest):
            return None
        if sequence != self.sequence:
            if not newer(sequence, self.sequence):
                return None
            self.sequence, self.count, self.parts = sequence, count, {}
        if self.count != count:
            raise ValueError("Inconsistent state fragment count")
        self.parts[part] = message[5:]
        if len(self.parts) == count:
            self.latest = sequence
            return b"".join(self.parts[i] for i in range(count))
        return None
