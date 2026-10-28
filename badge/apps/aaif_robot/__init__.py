"""Promote AAIF's Sandbox with a friendly waving robot."""

import math
import os
import sys


APP_DIR = "/system/apps/aaif_robot"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

screen.antialias = image.X2
screen.font = font.nope

robot = image.load("assets/robot.png")
hand = image.load("assets/hand.png")
logo = image.load("assets/aaif_logo.png")
hand_brush = brush.image(hand)
hand_shape = shape.rectangle(0, 0, hand.width, hand.height)

robot_height = screen.height * 0.69
robot_scale = robot_height / robot.height
robot_width = robot.width * robot_scale
robot_left = screen.width * 0.05
robot_top = screen.height * 0.22

hand_pivot_x = 19.9
hand_pivot_y = 66.3


def draw_centered(text, center_x, y):
    width, _ = screen.measure_text(text)
    screen.text(text, center_x - width / 2, y)


def update():
    phase = badge.ticks / 180
    wave_angle = math.sin(phase) * 32

    screen.pen = color.rgb(74, 85, 104)
    screen.rectangle(screen.clip)

    screen.pen = color.white
    screen.shape(shape.rounded_rectangle(29, 1, 102, 23, 4))
    screen.blit(logo, rect(33, 1.5, 94, 22))

    screen.blit(robot, rect(robot_left, robot_top, robot_width, robot_height))

    hand_shape.transform = (
        mat3()
        .translate(
            robot_left + hand_pivot_x * robot_scale,
            robot_top + hand_pivot_y * robot_scale,
        )
        .scale(robot_scale, robot_scale)
        .rotate(wave_angle)
        .translate(-hand_pivot_x, -hand_pivot_y)
    )
    screen.pen = hand_brush
    screen.shape(hand_shape)

    text_x = robot_left + robot_width + (screen.width - robot_left - robot_width) / 2
    screen.pen = color.white
    draw_centered("Our Sandbox", text_x, 48)
    screen.pen = color.rgb(255, 151, 110)
    draw_centered("is open for", text_x, 59)
    screen.pen = color.white
    draw_centered("new projects!", text_x, 70)


run(update)
