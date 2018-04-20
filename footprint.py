#!/usr/bin/env python3

import math

import cairo
import pykicad

m = pykicad.module.Module.from_file("test.kicad_mod")

WIDTH, HEIGHT = 256, 256

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
ctx = cairo.Context(surface)
ctx.scale(WIDTH/2, HEIGHT/2)
ctx.translate(1, 1)

pat = cairo.LinearGradient(0.0, -1.0, 0.0, 1.0)
pat.add_color_stop_rgba(1, 0.7, 0, 0, 0.5)  # First stop, 50% opacity
pat.add_color_stop_rgba(0, 0.9, 0.7, 0.2, 1)  # Last stop, 100% opacity
ctx.rectangle(-1, -1, 2, 2)  # Rectangle(x0, y0, x1, y1)
ctx.set_source(pat)
ctx.fill()

class Line:
    def __init__(self, x1, y1, x2, y2, width):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.width = width

class Layer:
    def __init__(self, color, alpha=1.0):
        self.color = color
        self.alpha = alpha
        self.objects = []
    
    def add_object(self, obj):
        self.objects.append(obj)
    

layers = {}
layers['F.Fab'] = Layer((0.8, 0.2, 0.2))
layers['F.CrtYd'] = Layer((0.2, 0.8, 0.2), 0.2)

print(m)

def draw_line(line):
    x1 = line.start[0]
    x2 = line.end[0]
    y1 = line.start[1] 
    y2 = line.end[1]
    ctx.set_line_width(line.width)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)

ctx.set_line_cap(cairo.LINE_CAP_ROUND)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
for line in m.lines:
    layers[line.layer].add_object(line)

for layer in layers.values():
    ctx.set_source_rgba(*layer.color, layer.alpha)
    for line in layer.objects:
        draw_line(line)
    ctx.stroke()

surface.write_to_png("example.png")

