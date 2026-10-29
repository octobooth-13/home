"""Hardware-independent, fixed-step platformer simulation."""

import math

TILE = 16
ROWS = 15
COLS = 192
FLOOR = 13
BIOMES = ("SURFACE", "CAVERN", "UNDERWATER")
STEP = 1 / 120


class Random:
    def __init__(self, seed):
        self.seed = seed & 0x7fffffff

    def pick(self, count):
        self.seed = (1103515245 * self.seed + 12345) & 0x7fffffff
        return (self.seed >> 8) % count


class Body:
    def __init__(self, x, y, w=10, h=14, kind="player"):
        self.x, self.y = float(x), float(y)
        self.w, self.h = w, h
        self.vx, self.vy = 0.0, 0.0
        self.grounded = False
        self.kind = kind
        self.alive = True
        self.direction = -1
        self.phase = 0.0
        self.home_y = float(y)


def overlaps(a, b):
    return (a.x < b.x + b.w and a.x + a.w > b.x
            and a.y < b.y + b.h and a.y + a.h > b.y)


class Level:
    def __init__(self, seed, biome):
        self.biome = biome
        self.tiles = [bytearray(COLS) for _ in range(ROWS)]
        self.coins = []
        self.enemies = []
        self.goal = (COLS - 6) * TILE
        self.checkpoint = 96 * TILE
        rng = Random(seed + biome * 65537)
        self.sections = []
        for row in range(FLOOR, ROWS):
            self.tiles[row] = bytearray([1] * COLS)
        patterns = list(range(10))
        for i in range(len(patterns) - 1, 0, -1):
            j = rng.pick(i + 1)
            patterns[i], patterns[j] = patterns[j], patterns[i]
        for region, (start, end) in enumerate(((12, 92), (104, 180))):
            x = start
            for index in range(5):
                remaining = end - x
                width = (remaining if index == 4 else
                         12 + rng.pick(min(18, remaining - (4 - index) * 12) - 11))
                pattern = patterns[region * 5 + index]
                self.sections.append((x, width, pattern))
                self.build_section(x, width, pattern, rng)
                x += width

    def platform(self, col, row, width, tile=2):
        for x in range(col, col + width):
            self.tiles[row][x] = tile

    def mound(self, col, width, height):
        for row in range(FLOOR - height, FLOOR):
            self.platform(col, row, width, 1)

    def coin_line(self, col, row, width, arc=False):
        for offset in range(width):
            y = row * TILE - (min(offset, width - offset - 1) * 6 if arc else 0)
            self.coins.append([(col + offset) * TILE + 4, y, True])

    def pipe(self, col, height):
        top = FLOOR - height
        self.platform(col, top, 2, 6)
        for row in range(top + 1, FLOOR):
            self.platform(col, row, 2, 5)
        self.enemies.append(Body(col * TILE + 10, top * TILE + 2, 12, 0, "plant"))

    def build_section(self, start, width, pattern, rng):
        x = start + 2 + rng.pick(2)
        span = width - (x - start) - 2
        if pattern == 0:  # Staircase ridge with a high coin trail.
            for offset, height in enumerate((1, 2, 3, 2, 1)):
                self.mound(x + offset, 1, height)
            self.coin_line(x, 8, 5, True)
            self.enemy(x + 2, "turtle")
        elif pattern == 1:  # Gap plus an optional high bridge.
            gap = 2 + rng.pick(2)
            if self.biome != 2:
                for row in range(FLOOR, ROWS):
                    for col in range(x + 2, x + 2 + gap):
                        self.tiles[row][col] = 0
            else:
                self.mound(x + 2, gap, 3)
            self.platform(x + 1, 6, gap + 2)
            self.platform(x - 1, 10, 2)
            self.platform(x + gap + 3, 8, 2)
            self.coin_line(x + 1, 4, gap + 2, True)
            self.enemy(x + gap + 4, "walker")
        elif pattern == 2:  # Two different pipe heights and a guarded reward.
            self.pipe(x, 1 + rng.pick(2))
            self.pipe(x + 5, 2 + rng.pick(2))
            self.tiles[8][x + 3] = 3
            self.coin_line(x + 2, 6, 3, True)
        elif pattern == 3:  # Low and high routes through a platform garden.
            self.platform(x, 10, 3)
            self.platform(x + 4, 8, 3)
            self.platform(x + 1, 5, 3)
            self.tiles[10][x + 1] = 3
            self.coin_line(x + 4, 6, 3)
            self.enemy(x + 5, "flying")
        elif pattern == 4:  # Broad terrace, then a lower reward shelf.
            self.mound(x, min(span - 3, 5), 2)
            self.platform(x + span - 2, 10, 2)
            self.tiles[8][x + 1] = 3
            self.coin_line(x, 7, 4)
            self.enemy(x + 2, "walker")
        elif pattern == 5:  # Uneven stepping stones, no fatal floor gap.
            for offset in (0, 3, 6):
                self.mound(x + offset, 2, 1 + (offset // 3) % 2)
            self.coin_line(x, 8, 7, True)
            self.enemy(x + 4, "flying")
        elif pattern == 6:  # Reward arcade, with ample large-player headroom.
            self.mound(x - 2, 2, 2)
            self.platform(x, 9, min(span, 7))
            self.tiles[9][x + 1] = 3
            self.tiles[9][x + 5] = 3
            self.platform(x + 2, 6, 3)
            self.coin_line(x + 2, 4, 3)
            self.enemy(x + 3, "turtle")
        elif pattern == 7:  # Short leap with a raised landing.
            if self.biome != 2:
                for row in range(FLOOR, ROWS):
                    for col in range(x + 2, x + 4):
                        self.tiles[row][col] = 0
            self.mound(x + 4, 3, 1)
            self.coin_line(x + 1, 9, 6, True)
            self.enemy(x + 5, "turtle")
        elif pattern == 8:  # Sheltered lower path or rooftop coins.
            self.platform(x, 8, min(span, 7))
            self.mound(x, 2, 1)
            self.mound(x + 4, 2, 2)
            self.mound(x + 7, 2, 2)
            self.coin_line(x, 6, min(span, 7))
            self.enemy(x + 3, "walker")
        else:  # Pipe, ledge and flying guard in one compact encounter.
            self.pipe(x, 2)
            self.platform(x + 4, 8, 3)
            self.tiles[8][x + 5] = 3
            self.coin_line(x + 4, 6, 3, True)
            self.enemy(x + 5, "flying")
        if self.biome == 1:
            depth = 1 + rng.pick(3)
            for row in range(3, 3 + depth):
                self.platform(start + 1, row, 2, 1)
        elif self.biome == 2:
            # A continuous mid-water lane remains open between reefs and overhangs.
            for row in range(6, 10):
                for col in range(start, start + width):
                    self.tiles[row][col] = 0
            for row in range(3, 5 + rng.pick(2)):
                self.platform(start + width - 4, row, 2, 1)
            self.coin_line(start + 2, 7 + rng.pick(2), min(width - 4, 6), True)
            self.tiles[9][start] = 3
            self.tiles[10][start] = 0
            self.tiles[11][start] = 0

    def enemy(self, col, kind):
        height = 12 if kind == "walker" else 16
        row = next(row for row in range(ROWS) if self.tiles[row][col])
        y = row * TILE - height
        if kind == "flying":
            y -= 42
        self.enemies.append(Body(col * TILE, y, 12, height, kind))

    def solid(self, col, row):
        if col < 0 or col >= COLS or row < 0:
            return True
        return row < ROWS and self.tiles[row][col] != 0

    def cells(self, body):
        for row in range(int(body.y // TILE), int((body.y + body.h - .01) // TILE) + 1):
            for col in range(int(body.x // TILE), int((body.x + body.w - .01) // TILE) + 1):
                if self.solid(col, row):
                    yield col, row

    def move(self, body, dt, on_head=None):
        hit_wall = False
        body.x += body.vx * dt
        for col, row in self.cells(body):
            if body.vx > 0:
                body.x = col * TILE - body.w
            elif body.vx < 0:
                body.x = (col + 1) * TILE
            hit_wall = True
        body.y += body.vy * dt
        body.grounded = False
        falling = body.vy >= 0
        for col, row in self.cells(body):
            if falling:
                body.y = row * TILE - body.h
                body.grounded = True
            else:
                body.y = (row + 1) * TILE
                if on_head and 0 <= row < ROWS and 0 <= col < COLS:
                    on_head(col, row)
            body.vy = 0
        return hit_wall


class Game:
    def __init__(self, seed=1, biome=0):
        self.seed = seed
        self.start_biome = biome
        self.stage = 1
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.shield = False
        self.power = "small"
        self.status = "title"
        self.load_level()

    def load_level(self):
        self.biome = (self.start_biome + self.stage - 1) % 3
        self.level = Level(self.seed + (self.stage - 1) * 997, self.biome)
        self.player = Body(3 * TILE, FLOOR * TILE - 14)
        self.resize_player()
        self.checkpoint = False
        self.camera = 0.0
        self.time = 240.0
        self.clock = 0.0
        self.invincible = 0.0
        self.death_timer = 0.0
        self.accumulator = 0.0
        self.jump_buffer = 0.0
        self.coyote = 0.0
        self.pickups = []
        self.fireballs = []
        self.fire_cooldown = 0.0
        self.shot_buffer = 0.0

    def start(self):
        self.status = "play"

    def next_stage(self):
        if self.status == "clear":
            self.stage += 1
            self.load_level()
            self.status = "play"

    def coin(self):
        self.coins += 1
        self.score += 100
        if self.coins % 100 == 0:
            self.lives += 1

    def resize_player(self):
        p = self.player
        height = 14 if self.power == "small" else 26
        if p.h == height:
            return
        candidate = Body(p.x, p.y + p.h - height, p.w, height)
        # Defer growth under a low ceiling rather than embed the player in tiles.
        if height < p.h or not any(self.level.cells(candidate)):
            p.y, p.h = candidate.y, height

    def collect(self, pickup):
        pickup.alive = False
        if pickup.kind == "mushroom":
            if self.power == "small":
                self.power = "big"
        elif pickup.kind == "flower":
            self.power = "fire"
        elif pickup.kind == "shield":
            self.shield = True
        self.resize_player()
        self.invincible = max(self.invincible, 1.0)
        self.score += 250

    def bump(self, col, row):
        tile = self.level.tiles[row][col]
        if tile == 3:
            self.level.tiles[row][col] = 4
            self.coin()
            kind = {"small": "mushroom", "big": "flower", "fire": "shield"}[self.power]
            pickup = Body(col * TILE + 2, row * TILE - 12, 12, 12, kind)
            if kind == "mushroom":
                pickup.vx = 32
            self.pickups.append(pickup)
        elif tile == 2 and (self.shield or self.power != "small"):
            self.level.tiles[row][col] = 0
            self.score += 50

    def hurt(self, fatal=False):
        if self.status != "play" or (self.invincible > 0 and not fatal):
            return
        if not fatal and (self.shield or self.power != "small"):
            if self.shield:
                self.shield = False
            else:
                self.power = "big" if self.power == "fire" else "small"
                self.resize_player()
            self.invincible = 2.0
            self.player.vy = -100
        else:
            self.lives -= 1
            self.status = "dead"
            self.death_timer = 1.0
            self.player.vy = -180
            self.fireballs = []
            self.shot_buffer = 0.0

    def update(self, dt, direction=0, jump=False, jump_held=False,
               running=False, vertical=0, shoot=False):
        if self.status not in ("play", "dead"):
            return
        if jump:
            self.jump_buffer = .12
        if shoot and self.status == "play":
            self.shot_buffer = .12
        self.accumulator += min(max(dt, 0), .1)
        while self.accumulator >= STEP:
            self.accumulator -= STEP
            self.step(STEP, direction, jump_held, running, vertical)
            if self.status not in ("play", "dead"):
                self.accumulator = 0
                break

    def step(self, dt, direction, jump_held, running, vertical):
        p = self.player
        self.clock += dt
        if self.status == "dead":
            p.vy += 500 * dt
            p.y += p.vy * dt
            self.death_timer -= dt
            if self.death_timer <= 0:
                if self.lives <= 0:
                    self.status = "gameover"
                else:
                    x = self.level.checkpoint if self.checkpoint else 3 * TILE
                    self.player = Body(x, FLOOR * TILE - 14)
                    self.shield = False
                    self.power = "small"
                    self.invincible = 2.0
                    self.time = max(120, self.time)
                    self.jump_buffer = self.coyote = 0.0
                    self.status = "play"
            return
        self.time -= dt
        self.invincible = max(0, self.invincible - dt)
        self.fire_cooldown = max(0, self.fire_cooldown - dt)
        self.shot_buffer = max(0, self.shot_buffer - dt)
        self.jump_buffer = max(0, self.jump_buffer - dt)
        self.coyote = .09 if p.grounded else max(0, self.coyote - dt)
        water = self.biome == 2
        speed = (92 if running else 65) if water else (126 if running else 86)
        target = direction * speed
        accel = 600 if direction else 800
        p.vx += max(-accel * dt, min(accel * dt, target - p.vx))
        if direction:
            p.direction = direction
        if self.shot_buffer > 0:
            self.shoot()
            self.shot_buffer = 0.0
        if water:
            if self.jump_buffer > 0:
                p.vy = -100
                self.jump_buffer = 0
            p.vy += (95 + vertical * 150) * dt
            p.vy = max(-110, min(65, p.vy))
        else:
            if self.jump_buffer > 0 and self.coyote > 0:
                p.vy = -245
                self.jump_buffer = self.coyote = 0
                p.grounded = False
            gravity = 580 if jump_held or p.vy > 0 else 1150
            p.vy = min(320, p.vy + gravity * dt)
        previous_bottom = p.y + p.h
        if self.level.move(p, dt, self.bump):
            p.vx = 0
        self.resize_player()
        if p.x >= self.level.checkpoint:
            self.checkpoint = True
        if p.y > ROWS * TILE + 20 or self.time <= 0:
            self.hurt(True)
        if self.status != "play":
            return
        for coin in self.level.coins:
            if coin[2] and p.x < coin[0] + 8 and p.x + p.w > coin[0] and p.y < coin[1] + 10 and p.y + p.h > coin[1]:
                coin[2] = False
                self.coin()
        for pickup in self.pickups:
            if not pickup.alive:
                continue
            pickup.vy = min(200, pickup.vy + 400 * dt)
            if self.level.move(pickup, dt):
                pickup.vx *= -1
            if pickup.y > ROWS * TILE + 20:
                pickup.alive = False
                continue
            if overlaps(p, pickup):
                self.collect(pickup)
        self.pickups = [pickup for pickup in self.pickups if pickup.alive]
        for enemy in self.level.enemies:
            if not enemy.alive or abs(enemy.x - p.x) > 360:
                continue
            self.move_enemy(enemy, dt)
            if not enemy.alive or enemy.h == 0 or not overlaps(p, enemy):
                continue
            stomp = (not water and enemy.kind != "plant"
                     and p.vy > 0 and previous_bottom <= enemy.y + 5)
            if stomp:
                p.vy = -180 if jump_held else -140
                if enemy.kind == "flying":
                    enemy.kind = "turtle"
                    enemy.vy = 0
                elif enemy.kind == "turtle":
                    enemy.kind = "shell"
                    enemy.h = 9
                    enemy.y += 7
                    enemy.vx = 0
                elif enemy.kind == "shell":
                    if enemy.vx:
                        enemy.vx = 0
                    else:
                        self.kick(enemy)
                else:
                    enemy.alive = False
                self.score += 200
            elif enemy.kind == "shell" and enemy.vx == 0:
                self.kick(enemy)
            else:
                self.hurt()
        if self.status != "play":
            return
        self.move_fireballs(dt)
        self.camera = max(0, min((COLS - 20) * TILE, p.x - 112))
        if p.x >= self.level.goal and self.status == "play":
            self.score += int(self.time) * 5 + 500
            self.status = "clear"

    def shoot(self):
        if self.power != "fire" or self.fire_cooldown > 0 or len(self.fireballs) >= 2:
            return
        p = self.player
        x = p.x + p.w + 1 if p.direction > 0 else p.x - 7
        shot = Body(x, p.y + p.h * .5, 6, 6, "fireball")
        shot.vx = p.direction * 190
        shot.vy = 30
        shot.phase = 1.8
        self.fireballs.append(shot)
        self.fire_cooldown = .25

    def move_fireballs(self, dt):
        for shot in self.fireballs:
            shot.phase -= dt
            if shot.phase <= 0 or shot.y > ROWS * TILE + 20:
                shot.alive = False
                continue
            shot.vy = min(240, shot.vy + 400 * dt)
            falling = shot.vy >= 0
            if self.level.move(shot, dt):
                shot.alive = False
                continue
            if shot.grounded:
                shot.vy = -115
            elif not falling and shot.vy == 0:
                shot.alive = False
                continue
            for enemy in self.level.enemies:
                if enemy.alive and enemy.h and overlaps(shot, enemy):
                    enemy.alive = False
                    shot.alive = False
                    self.score += 200
                    break
        self.fireballs = [shot for shot in self.fireballs if shot.alive]

    def kick(self, enemy):
        enemy.vx = 190 if self.player.x < enemy.x else -190
        enemy.x = (self.player.x + self.player.w + 2 if enemy.vx > 0
                   else self.player.x - enemy.w - 2)

    def move_enemy(self, enemy, dt):
        kind = enemy.kind
        if kind == "plant":
            phase = (self.clock + enemy.x / 100) % 4.5
            height = int(max(0, min(24, (phase - 1) * 32, (4 - phase) * 32)))
            if abs(self.player.x - enemy.x) < 30 and enemy.h == 0:
                height = 0
            enemy.h = height
            enemy.y = enemy.home_y - height
            return
        if kind == "flying":
            enemy.phase += dt
            enemy.vx = enemy.direction * 25
            if self.level.move(enemy, dt):
                enemy.direction *= -1
            enemy.y = enemy.home_y + math.sin(enemy.phase * 3) * 22
        else:
            if kind != "shell":
                enemy.vx = enemy.direction * (24 if kind == "walker" else 32)
                ahead = int((enemy.x + (enemy.w + 2 if enemy.direction > 0 else -2)) // TILE)
                feet = int((enemy.y + enemy.h + 2) // TILE)
                if enemy.grounded and not self.level.solid(ahead, feet):
                    enemy.direction *= -1
                    enemy.vx *= -1
            enemy.vy = min(300, enemy.vy + 580 * dt)
            if self.level.move(enemy, dt):
                enemy.direction *= -1
                enemy.vx *= -1
            if enemy.y > ROWS * TILE + 20:
                enemy.alive = False
            if kind == "shell" and enemy.vx:
                for other in self.level.enemies:
                    if other is not enemy and other.alive and other.h and overlaps(enemy, other):
                        other.alive = False
                        self.score += 200
