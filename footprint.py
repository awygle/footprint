#!/usr/bin/env python3

import math

import cairo
import pykicad

m = pykicad.module.Module.from_file("test.kicad_mod")

WIDTH, HEIGHT = 2048, 2048

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
ctx = cairo.Context(surface)
maxsize = 8
ctx.scale(WIDTH/maxsize, HEIGHT/maxsize)
ctx.translate(maxsize / 2, maxsize / 2)

pat = cairo.LinearGradient(0.0, -1.0, 0.0, 1.0)
pat.add_color_stop_rgba(1, 0.7, 0, 0, 0.5)  # First stop, 50% opacity
pat.add_color_stop_rgba(0, 0.9, 0.7, 0.2, 1)  # Last stop, 100% opacity
ctx.rectangle(-(maxsize/2), -(maxsize/2), maxsize, maxsize)  # Rectangle(x0, y0, x1, y1)
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

    def from_pad(pad, layer):
        longer = pad.size[0] > pad.size[1]
        if longer:
            width = pad.size[1]
            length = pad.size[0] - width
            x1 = pad.at[0] - (length / 2.0)
            y1 = pad.at[1]

            x2 = pad.at[0] + (length / 2.0)
            y2 = pad.at[1]
        else:
            width = pad.size[0]
            length = pad.size[1] - width
            x1 = pad.at[0]
            y1 = pad.at[1] - (length / 2.0)

            x2 = pad.at[0]
            y2 = pad.at[1] + (length / 2.0)

        return Line(x1, y1, x2, y2, width)

    def draw(self, ctx):
        ctx.set_line_width(self.width)
        ctx.move_to(self.x1, self.y1)
        ctx.line_to(self.x2, self.y2)
        ctx.stroke()

class Rectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def from_pad(pad, layer):
        size = [pad.size[0], pad.size[1]]
        if layer == 'F.Mask' and pad.attributes['solder_mask_margin']:
            size[0] += pad.attributes['solder_mask_margin']
            size[1] += pad.attributes['solder_mask_margin']
        if layer == 'F.Paste' and pad.attributes['solder_paste_margin']:
            size[0] += pad.attributes['solder_paste_margin']
            size[1] += pad.attributes['solder_paste_margin']
        rect = Rectangle(pad.at[0], pad.at[1], size[0], size[1])
        rect.origin = (pad.at[0], pad.at[1])
        if len(pad.at) > 2:
            rect.angle = pad.at[2]
        else:
            rect.angle = 0
        return rect

    def draw(self, ctx):
        ctx.save()
        ctx.translate(self.origin[0], self.origin[1])
        ctx.rotate(math.radians(self.angle))
        ctx.translate(-self.origin[0], -self.origin[1])
        x = self.x - (self.width / 2.0)
        y = self.y - (self.height / 2.0)
        ctx.rectangle(x, y, self.width, self.height)
        ctx.fill()
        ctx.restore()

class Arc:
    def __init__(self, x, y, radius, start_angle, end_angle):
        self.x = x
        self.y = y
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle

    def from_kicad(arc):
        delta_x = arc.end[0] - arc.start[0]
        delta_y = arc.start[1] - arc.end[1] # because negative Y is higher up
        radius = math.hypot(delta_x, delta_y)
        start_angle = math.atan2(delta_y, delta_x)
        end_angle = start_angle + math.radians(arc.angle)
        return Arc(arc.start[0], arc.start[1], radius, start_angle, end_angle)

    def draw(self, ctx):
        ctx.arc_negative(self.x, self.y, self.radius, self.start_angle, self.end_angle)
        ctx.stroke()

class Circle:
    def __init__(self, x, y, diameter, filled=True):
        self.x = x
        self.y = y
        self.radius = diameter / 2.0
        self.filled = filled

    def from_kicad(circle):
        return Circle(circle.center[0],
                circle.center[1],
                math.hypot(circle.end[0] - circle.center[0],
                    circle.center[1] - circle.end[1])*2,
                False)

    def from_pad(pad, layer):
        size = pad.size[0]
        if layer == 'F.Mask' and pad.attributes['solder_mask_margin']:
            size += pad.attributes['solder_mask_margin']
        if layer == 'F.Paste' and pad.attributes['solder_paste_margin']:
            size += pad.attributes['solder_paste_margin']
        circ = Circle(pad.at[0], pad.at[1], size)
        return circ

    def draw(self, ctx):
        ctx.arc(self.x, self.y, self.radius, 0.0, math.radians(360))
        if self.filled:
            ctx.fill()
        else:
            ctx.stroke()

class Polygon:
    def __init__(self, points):
        self.points = points
        Polygon.run = 0

    def from_pad(pad, layer):
        size = [pad.size[0], pad.size[1]]
        if layer == 'F.Mask' and pad.attributes['solder_mask_margin']:
            size[0] += pad.attributes['solder_mask_margin']
            size[1] += pad.attributes['solder_mask_margin']
        if layer == 'F.Paste' and pad.attributes['solder_paste_margin']:
            size[0] += pad.attributes['solder_paste_margin']
            size[1] += pad.attributes['solder_paste_margin']
        points = []
        xoff = (size[0] / 2.0)
        xdelt = (pad.rect_delta[1] / 2.0) # these indices are inverted compared to what makes sense to me
        yoff = (size[1] / 2.0)
        ydelt = (pad.rect_delta[0] / 2.0)
        # top left
        points.append( (pad.at[0] - xoff + xdelt, pad.at[1] - yoff - ydelt) )
        # top right
        points.append( (pad.at[0] + xoff - xdelt, pad.at[1] - yoff + ydelt) )
        # bottom right
        points.append( (pad.at[0] + xoff + xdelt, pad.at[1] + yoff - ydelt) )
        # bottom left
        points.append( (pad.at[0] - xoff - xdelt, pad.at[1] + yoff + ydelt) )
        poly = Polygon(points)
        poly.pad = pad
        poly.origin = (pad.at[0], pad.at[1])
        if len(pad.at) > 2:
            poly.angle = pad.at[2]
        else:
            poly.angle = 0
        return poly

    def draw(self, ctx):
        ctx.save()
        ctx.translate(self.origin[0], self.origin[1])
        ctx.rotate(math.radians(self.angle))
        ctx.translate(-self.origin[0], -self.origin[1])
        for point in self.points:
            ctx.line_to(point[0], point[1])
        ctx.close_path()
        ctx.fill()
        ctx.restore()

class Layer:
    def __init__(self, color, alpha=1.0):
        self.color = color
        self.alpha = alpha
        self.objects = []

    def add_object(self, obj):
        self.objects.append(obj)

    def draw(self, ctx):
        ctx.push_group()
        ctx.set_source_rgb(*layer.color)
        for obj in self.objects:
            try:
                obj.draw(ctx)
            except:
                print(obj)
                raise
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(layer.alpha)

def pad_to_object(pad, layer):
    shape = pad.attributes['shape']
    if shape == "rect":
        return Rectangle.from_pad(pad, layer)
    if shape == "trapezoid":
        return Polygon.from_pad(pad, layer)
    if shape == "circle":
        return Circle.from_pad(pad, layer)
    if shape == "oval":
        return Line.from_pad(pad, layer)
    else:
        raise NotImplementedError("Pad shape " + shape + " not yet supported")

layers = {}
layers['F.Fab'] = Layer((0.8, 0.2, 0.2))
layers['F.CrtYd'] = Layer((0.2, 0.8, 0.2), 0.2)
layers['F.Cu'] = Layer((0.2, 0.2, 0.8), 1.0)
layers['F.Mask'] = Layer((0.8, 0.2, 0.8), 0.0)
layers['F.Paste'] = Layer((0.8, 0.8, 0.2), 0.0)
layers['F.SilkS'] = Layer((0.2, 0.8, 0.8), 1.0)

ctx.set_line_cap(cairo.LINE_CAP_ROUND)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
for line in m.lines:
    layers[line.layer].add_object(Line.from_kicad(line))
for arc in m.arcs:
    layers[arc.layer].add_object(Arc.from_kicad(arc))
for circle in m.circles:
    layers[circle.layer].add_object(Circle.from_kicad(circle))
for pad in m.pads:
    for layer in pad.layers:
        layers[layer].add_object(pad_to_object(pad, layer))

for layer in layers.values():
    layer.draw(ctx)

surface.write_to_png("example.png")

