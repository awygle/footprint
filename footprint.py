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
    
    def from_kicad(line):
        return Line(line.start[0], line.start[1], line.end[0], line.end[1], line.width)
    
    def draw(self, ctx):
        ctx.set_line_width(self.width)
        ctx.move_to(self.x1, self.y1)
        ctx.line_to(self.x2, self.y2)
        
class Rectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def from_pad(pad):
        return Rectangle(pad.at[0], pad.at[1], pad.size[0], pad.size[1])
    
    def draw(self, ctx):
        x = self.x - (self.width / 2.0)
        y = self.y - (self.height / 2.0)
        ctx.rectangle(x, y, self.width, self.height)

class Layer:
    def __init__(self, color, alpha=1.0):
        self.color = color
        self.alpha = alpha
        self.objects = []
    
    def add_object(self, obj):
        self.objects.append(obj)
    
    def draw(self, ctx):
        for obj in self.objects:
            try:
                obj.draw(ctx)
            except:
                print(obj)
                raise

layers = {}
layers['F.Fab'] = Layer((0.8, 0.2, 0.2))
layers['F.CrtYd'] = Layer((0.2, 0.8, 0.2), 0.2)
layers['F.Cu'] = Layer((0.2, 0.2, 0.8), 1.0)
layers['F.Mask'] = Layer((0.8, 0.2, 0.8), 0.0)
layers['F.Paste'] = Layer((0.8, 0.8, 0.2), 0.0)

ctx.set_line_cap(cairo.LINE_CAP_ROUND)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
for line in m.lines:
    layers[line.layer].add_object(Line.from_kicad(line))
for pad in m.pads:
    for layer in pad.layers:
        layers[layer].add_object(Rectangle.from_pad(pad))

for layer in layers.values():
    ctx.set_source_rgba(*layer.color, layer.alpha)
    layer.draw(ctx)
    ctx.stroke()

surface.write_to_png("example.png")

