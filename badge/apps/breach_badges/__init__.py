"""Breach Badges: the central badge referees the whole arena."""

import os
import sys
import struct

PACK_ERROR = getattr(struct, "error", ValueError)

APP_DIR = "/system/apps/breach_badges"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from badgeware import link as badgelink
from arena import (
    Arena, Assembler, packets, newer, clamp, NAMES, GLYPHS,
    BASIC, RAPID, DRILL, SCATTER, ROCKET, SHIELD, DASH, REPAIR, STRONG_SHIELD,
    UP, DOWN, FIRE, COUNTDOWN, PLAY, ROUND_OVER, MATCH_OVER,
    TOP, BOTTOM, WALL_X, COLS, BRICK_W, BRICK_H,
)

badge.mode(HIRES | VSYNC)
screen.font = font.nope
screen.fill_rule = image.EVEN_ODD
screen.antialias = image.OFF

PALETTE = (
    color.rgb(242, 245, 255), color.rgb(255, 219, 80),
    color.rgb(199, 122, 255), color.rgb(115, 238, 120),
    color.rgb(255, 91, 67), color.rgb(58, 210, 255),
    color.rgb(58, 210, 255), color.rgb(58, 210, 255),
    color.rgb(255, 219, 80),
)
BG = color.rgb(10, 15, 29)
DIM = color.rgb(99, 117, 151)
WALL = color.rgb(75, 92, 123)
LOCAL = color.rgb(63, 227, 216)
RIVAL = color.rgb(255, 116, 129)


def box(x, y, w, h, pen):
    screen.pen = pen
    screen.rectangle(x * screen.width / 320, y * screen.height / 240,
                     w * screen.width / 320, h * screen.height / 240)


def text(label, x, y, pen=PALETTE[0]):
    screen.pen = pen
    screen.text(label, x * screen.width / 320, y * screen.height / 240)


def centre(label, y, pen=PALETTE[0]):
    screen.pen = pen
    width, _ = screen.measure_text(label)
    screen.text(label, (screen.width - width) / 2, y * screen.height / 240)


class Breach:
    def __init__(self):
        self.link = badgelink.Link("breach_badges")
        self.proximity = badgelink.Proximity(self.link)
        self.arena = Arena()
        self.assembler = Assembler()
        self.mode = "lobby"
        self.practice = False
        self.host = False
        self.side = 0
        self.partner_id = None
        self.ready = False
        self.peer_ready = False
        self.remote_flags = 0
        self.remote_defense = 0
        self.defense = 0
        self.input_sequence = 0
        self.remote_sequence = None
        self.state_sequence = 0
        self.last_rx = -10000
        self.last_state = -10000
        self.clock = 0.0
        self.sent_at = -10000
        self.was_linked = False
        self.paused = True
        self.notice = ""
        self.reported_error = ""
        self.bot_defense_at = 0
        self.outbox = {}
        self.state_packets = []

    def leave(self):
        partner = self.link.partner
        self.proximity.rest(partner.id if partner else None, int(self.clock))
        self.link.leave()
        self.mode = "lobby"
        self.practice = False
        self.partner_id = None
        self.ready = self.peer_ready = False
        self.remote_flags = 0
        self.remote_sequence = None
        self.assembler = Assembler()
        self.last_rx = self.last_state = -10000
        self.was_linked = False
        self.outbox = {}
        self.state_packets = []

    def start(self):
        self.arena.new_match()
        self.mode = "game"
        self.ready = self.peer_ready = False
        self.remote_flags = 0
        self.remote_defense = 0
        self.defense = 0
        self.remote_sequence = None
        self.outbox = {}
        self.state_packets = []

    def queue(self, message):
        self.outbox[message[:1]] = message

    def flush(self):
        capacity = self.link.capacity()
        if capacity < 12:
            self.notice = "Link capacity too small (need 12 bytes)"
            self.paused = True
            if self.reported_error != self.notice:
                print("Breach Badges:", self.notice)
                self.reported_error = self.notice
            return
        for kind in list(self.outbox):
            message = self.outbox[kind]
            if not self.link.send(message):
                return
            del self.outbox[kind]
        while self.state_packets:
            if len(self.state_packets[0]) > capacity:
                # Renegotiated MTU: restart with a newly sized complete snapshot.
                self.state_packets = []
                return
            if not self.link.send(self.state_packets[0]):
                return
            self.state_packets.pop(0)

    def decline(self):
        if not self.link.send(b"L"):
            print("Breach Badges: peer not notified of departure; peer will pause")
        self.leave()

    def input_flags(self):
        flags = 0
        for button, value in ((BUTTON_UP, UP), (BUTTON_DOWN, DOWN), (BUTTON_SELECT, FIRE)):
            if badge.held(button):
                flags |= value
        return flags

    def handle(self, message):
        if message[:1] == b"A" and len(message) == 3:
            match, = struct.unpack("<H", message[1:])
            if match == self.arena.match and (
                    self.mode == "offer" or self.arena.phase == MATCH_OVER):
                self.peer_ready = True
        elif message[:1] == b"L" and len(message) == 1:
            self.leave()
            self.notice = "Opponent left - match not scored"
        elif message[:1] == b"I" and len(message) == 8 and self.host:
            match, sequence, flags, defense = struct.unpack("<HHBH", message[1:])
            if match == self.arena.match and newer(sequence, self.remote_sequence):
                self.remote_sequence = sequence
                if flags & 8:
                    self.last_rx = self.clock
                self.remote_flags = flags & 7
                if defense != self.remote_defense:
                    if not self.paused:
                        self.arena.activate(1)
                    self.remote_defense = defense
        elif message[:1] == b"S" and not self.host:
            data = self.assembler.feed(message)
            if data is not None:
                self.arena.restore(data)
                self.last_rx = self.last_state = self.clock
                self.mode = "game"
                if self.arena.phase != MATCH_OVER:
                    self.ready = self.peer_ready = False
        elif message[:1] == b"H" and len(message) == 3:
            match, = struct.unpack("<H", message[1:])
            if match == self.arena.match and (not self.host or self.mode == "offer"):
                self.last_rx = self.clock
        else:
            raise ValueError("Unknown or malformed Breach packet")

    def update(self, dt):
        self.clock += dt * 1000
        now = int(self.clock)
        self.link.pump()
        linked = self.link.linked
        if linked and not self.was_linked:
            peer = self.link.partner
            if self.mode == "lobby" and not self.practice:
                self.partner_id = peer.id
                self.host = bool(self.link.central)
                self.side = 0 if self.host else 1
                self.ready = self.peer_ready = False
                self.arena = Arena()
                self.assembler = Assembler()
                self.mode = "offer"
            elif self.practice or peer.id != self.partner_id:
                self.link.leave()
                linked = False
        self.was_linked = linked
        if linked:
            for message in self.link.receive():
                try:
                    self.handle(message)
                except (ValueError, IndexError, PACK_ERROR) as error:
                    self.notice = "Link data error; waiting for fresh state"
                    if str(error) != self.reported_error:
                        print("Breach Badges link error:", error)
                        self.reported_error = str(error)

        if badge.pressed(BUTTON_MENU) and self.mode != "lobby":
            if linked and not self.practice:
                self.decline()
            else:
                self.leave()
        if self.mode == "lobby":
            self.proximity.update(now)
            if badge.pressed(BUTTON_SELECT):
                self.link.leave()
                self.practice = self.host = True
                self.side = 0
                self.start()
        elif self.mode == "offer":
            if not linked:
                self.leave()
            elif badge.pressed(BUTTON_BACK):
                self.decline()
            elif badge.pressed(BUTTON_SELECT):
                self.ready = True
        elif self.mode == "game":
            if not self.practice and not linked:
                self.proximity.update(now)
            self.paused = not self.practice and (
                not linked or self.clock - self.last_rx > 650 or
                (not self.host and (self.clock - self.last_state > 650 or self.arena.link_paused)) or
                (linked and self.link.capacity() < 12))
            if self.arena.phase == MATCH_OVER:
                if badge.pressed(BUTTON_SELECT):
                    self.ready = True
                if self.practice and self.ready:
                    self.start()
            elif not self.paused:
                flags = self.input_flags()
                if badge.pressed(BUTTON_BACK):
                    self.defense = (self.defense + 1) & 65535
                    if self.host:
                        self.arena.activate(0)
                if self.host:
                    rival = self.remote_flags
                    if self.practice:
                        bot = self.arena.players[1]
                        # Sweep across supply rows instead of perfectly tracking shots.
                        target = TOP + 14 + (self.clock / 24) % (BOTTOM - TOP - 28)
                        rival = FIRE | (DOWN if bot.y < target else UP)
                        if self.clock > self.bot_defense_at:
                            self.arena.activate(1)
                            self.bot_defense_at = self.clock + 1000
                    self.arena.step(dt, (flags, rival))

        if linked and not self.practice and self.clock - self.sent_at >= 80:
            self.sent_at = self.clock
            if self.ready:
                self.queue(b"A" + struct.pack("<H", self.arena.match))
            self.queue(b"H" + struct.pack("<H", self.arena.match))
            if self.mode == "game":
                if self.host:
                    self.arena.link_paused = self.paused
                    if not self.state_packets and self.link.capacity() >= 12:
                        self.state_packets = packets(
                            self.state_sequence, self.arena.snapshot(), self.link.capacity())
                        self.state_sequence = (self.state_sequence + 1) & 65535
                else:
                    self.queue(b"I" + struct.pack(
                        "<HHBH", self.arena.match, self.input_sequence,
                        (self.input_flags() if not self.paused else 0) |
                        (8 if self.clock - self.last_state <= 650 else 0), self.defense))
                    self.input_sequence = (self.input_sequence + 1) & 65535
        if self.host and self.ready and self.peer_ready:
            if self.mode == "offer" or self.arena.phase == MATCH_OVER:
                self.start()
        if linked and not self.practice:
            self.flush()
        self.link.update()

    def px(self, x, width=0):
        return x if self.side == 0 else 320 - x - width

    def draw(self):
        box(0, 0, 320, 240, BG)
        if self.mode == "lobby":
            centre("BREACH BADGES", 22, LOCAL)
            centre("Break walls. Catch gear. Win the duel.", 52)
            peer = self.proximity.syncing()
            centre("Connecting: " + peer.name if peer else "Hold badges back to back", 90)
            centre("Then both confirm the named opponent", 112, DIM)
            centre("SELECT: practice against a bot", 148, PALETTE[RAPID])
            centre("UP / DOWN move    SELECT fire", 176)
            centre("BACK defense    MENU leave", 196)
            if self.notice:
                centre(self.notice, 222, RIVAL)
            return
        if self.mode == "offer":
            centre("NEARBY OPPONENT", 30, LOCAL)
            partner = self.link.partner
            name = partner.name if partner else "Disconnected"
            while screen.measure_text(name)[0] > screen.width - 16:
                name = name[:-1]
            centre(name, 70)
            centre("They confirmed" if self.peer_ready else "Confirm on BOTH badges", 110)
            centre("Waiting..." if self.ready else "SELECT: accept match", 150, PALETTE[RAPID])
            centre("BACK: decline", 180, DIM)
            return

        arena = self.arena
        me, them = arena.players[self.side], arena.players[1 - self.side]
        text("YOU %d" % me.hp, 6, 4, LOCAL)
        centre("%d:%d  %s" % (
            arena.scores[self.side], arena.scores[1 - self.side],
            "SD" if arena.sudden else "%02d" % int(arena.remaining + 0.99)), 4)
        text("FOE %d" % them.hp, 261, 4, RIVAL)
        box(0, TOP - 3, 320, 1, DIM)
        box(0, BOTTOM + 2, 320, 1, DIM)
        for index, hp in enumerate(arena.bricks):
            if not hp:
                continue
            x = self.px(WALL_X + index % COLS * BRICK_W, BRICK_W - 1)
            y = TOP + index // COLS * BRICK_H
            pen = PALETTE[RAPID] if arena.supply[index] else WALL
            box(x, y, BRICK_W - 1, BRICK_H - 1, pen)
            if hp < (12 if arena.supply[index] else 8):
                box(x + 4, y, 2, 9, BG)
                box(x + 6, y + 7, 3, 2, BG)
            if arena.supply[index]:
                box(x + 3, y + 5, 5, 5, BG)
        for side, player in enumerate(arena.players):
            x = self.px(12 if side == 0 else 294, 14)
            pen = LOCAL if side == self.side else RIVAL
            box(x, player.y - 9, 14, 18, pen)
            box(x + 4, player.y - 4, 6, 8, BG)
            box(self.px(24 if side == 0 else 288, 8), player.y - 2, 8, 4, pen)
            if player.shield:
                box(x - 3, player.y - 13, 20, 2, PALETTE[SHIELD])
                if player.shield == 2:
                    box(x - 3, player.y + 11, 20, 2, PALETTE[STRONG_SHIELD])
            if player.dash_time:
                box(x + 4, player.y + (12 if player.direction < 0 else -17),
                    6, 5, PALETTE[DASH])
        for shot in arena.shots:
            x, y, _, _, side, kind = shot[:6]
            size = 6 if kind == ROCKET else 3
            box(self.px(x - size / 2, size), y - 1, size, 3, PALETTE[kind])
            if kind == ROCKET:
                text("!", self.px(x) - 2, y - 12, PALETTE[ROCKET])
        for x, y, kind, side in arena.drops:
            x = self.px(x) - 5
            box(x, y - 6, 12, 12, PALETTE[kind])
            text(GLYPHS[kind], x + 2, y - 4, BG)
        for x, y, life in arena.effects:
            size = 8 + (0.25 - life) * 100
            box(self.px(x) - size / 2, y, size, 2, PALETTE[ROCKET])
        weapon_label = GLYPHS[me.weapon] + ":" + NAMES[me.weapon]
        if me.weapon != BASIC:
            weapon_label += " %ds" % int(me.weapon_time + 0.99)
        text(weapon_label, 4, 220, PALETTE[me.weapon])
        text("BACK:" + (NAMES[me.defense] if me.defense else "EMPTY"),
             173, 220, PALETTE[SHIELD])
        if self.paused:
            box(8, 87, 304, 70, BG)
            centre("LINK PAUSED - no win awarded", 94, PALETTE[RAPID])
            centre("Return to the same badge to resume", 116)
            centre("MENU: abandon match", 138, DIM)
            if self.notice:
                centre(self.notice, 158, RIVAL)
        elif arena.phase == COUNTDOWN:
            centre("ROUND %d" % arena.round_number, 88)
            centre(str(max(1, int(arena.phase_time + 0.99))), 110, PALETTE[RAPID])
        elif arena.phase in (ROUND_OVER, MATCH_OVER):
            box(20, 85, 280, 84, BG)
            centre("YOU WIN" if arena.winner == self.side else "RIVAL WINS", 94, LOCAL)
            if arena.phase == MATCH_OVER:
                centre("Waiting for rematch" if self.ready else "SELECT: rematch", 124)
                centre("MENU: leave", 148, DIM)
            else:
                centre("Next round...", 124)
        elif arena.sudden:
            centre("SUDDEN DEATH - ONE HIT", 19, PALETTE[ROCKET])


game = Breach()


def update():
    game.update(clamp(badge.ticks_delta / 1000, 0, 0.1))
    game.draw()


def on_exit():
    game.link.close()


run(update)
