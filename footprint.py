#!/usr/bin/env python3

import math

import cairo
import pykicad

m = pykicad.module.Module.from_file("test.kicad_mod")

WIDTH, HEIGHT = 2048, 2048

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
        rect = Rectangle(pad.at[0], pad.at[1], pad.size[0], pad.size[1])
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
    else:
        raise NotImplementedError("Pad shape " + shape + " not yet supported")

layers = {}
layers['F.Fab'] = Layer((0.8, 0.2, 0.2))
layers['F.CrtYd'] = Layer((0.2, 0.8, 0.2), 0.2)
layers['F.Cu'] = Layer((0.2, 0.2, 0.8), 1.0)
layers['F.Mask'] = Layer((0.8, 0.2, 0.8), 0.0)
layers['F.Paste'] = Layer((0.8, 0.8, 0.2), 0.0)
layers['F.SilkS'] = Layer((0.2, 0.8, 0.8), 0.0)

ctx.set_line_cap(cairo.LINE_CAP_ROUND)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
for line in m.lines:
    layers[line.layer].add_object(Line.from_kicad(line))
for pad in m.pads:
    for layer in pad.layers:
        layers[layer].add_object(pad_to_object(pad, layer))

for layer in layers.values():
    layer.draw(ctx)

surface.write_to_png("example.png")

