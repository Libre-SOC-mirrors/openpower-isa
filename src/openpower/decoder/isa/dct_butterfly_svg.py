#!/usr/bin/env python
# SPDX: LGPLv3+
# Program for generating DCT butterfly diagrams from yield REMAP schedules
# avoids the need to mess about drawing diagrams by hand, getting them wrong,
# introducing mistakes (common in academic published papers, sigh)

from copy import deepcopy
from collections import OrderedDict
from math import pi
import os
import base64
import math

from openpower.decoder.isa.remap_dct_yield import (reverse_bits, halfrev2,
                                        iterate_dct_inner_butterfly_indices,
                                        iterate_dct_outer_butterfly_indices,
                                        )

cwd = os.path.split(os.path.abspath(__file__))[0]

def linescale(l1, l2, scale):
    diffx = l2[0] - l1[0]
    diffy = l2[1] - l1[1]
    return l1[0] - diffx*scale, l1[1] + diffy*scale

def lineoffs(l2, scale):
    return l2[0] - abs(scale), l2[1] + scale


def create_idct(fname, n, redir=True):
    """unsophisticated drawer of an SVG
    """

    try:
        import svgwrite
    except ImportError:
        print ("WARNING, no SVG image, not producing image %s" % fname)
        return

    # Initialization
    vec = range(n)
    print ()
    print ("transform2", n)
    levels = n.bit_length() - 1

    # set up dims
    xdim = n

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # pretend we LDed data in half-swapped *and* bit-reversed order as well
    # TODO: merge these two
    vec = [vec[ri[i]] for i in range(n)]
    vec = halfrev2(vec, True)

    width = 800
    height = 600
    scale = 15

    dwg = svgwrite.Drawing(fname, profile='full',
                           size=(width, height))

    # outer QFP rect
    dwg.add(dwg.rect((0, 0), (width, height),
            fill='white',
            stroke=svgwrite.rgb(0, 128, 0, '%'),
            stroke_width=scale/5.0))

    # x start layer
    xstep = width / 10.0
    x = xstep / 2
    ystep = height/(n+1.0)
    y = ystep

    # start data
    for i in range(n):
        # flat lines
        startline = (x-scale, y+i*ystep+scale/2)
        dwg.add(dwg.text("%d" % vec[i],
                         startline,
                         fill='black'))

    # set up an SVSHAPE
    class SVSHAPE:
        pass

    # ####
    # outer
    # ####

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b0000010, 0]
    SVSHAPE0.submode2 = 0b11
    SVSHAPE0.mode = 0b11
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [1,0,1] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b0000010, 0]
    SVSHAPE1.mode = 0b11
    SVSHAPE1.submode2 = 0b11
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [1,0,1] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_outer_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_outer_butterfly_indices(SVSHAPE1)
    for k, ((jl, jle), (jh, jhe)) in enumerate(zip(i0, i1)):
        print ("itersum    jr", jl, jh,
                "end", bin(jle), bin(jhe))
        if redir:
            jl = vec[jl]
            jh = vec[jh]
        # jh to jl
        startline = (x, y+jh*ystep)
        endline = (x+xstep, y+jl*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        # plus sign
        dwg.add(dwg.text("+",
                         lineoffs(endline, scale*0.9),
                         fill='black'))
        if (jle & 0b010):
            for i in range(n):
                # flat lines
                startline = (x, y+i*ystep)
                endline = (x+xstep, y+i*ystep)
                dwg.add(dwg.line(startline,
                                 endline,
                                 stroke=svgwrite.rgb(16, 255, 16, '%'),
                                 stroke_width=scale/15.0))
            x += xstep * 1.2
        if jle == 0b111: # all loops end
            break

    # break point
    for i in range(n):
        # flat lines
        startline = (x, y+i*ystep)
        endline = (x+xstep, y+i*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/15.0))
    x += xstep * 0.2

    ################
    # INNER butterfly
    ################

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b000001, 0]
    SVSHAPE0.mode = 0b11
    SVSHAPE0.submode2 = 0b11
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b000001, 0]
    SVSHAPE1.mode = 0b11
    SVSHAPE1.submode2 = 0b11
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [0,0,0] # inversion if desired
    # ci schedule
    SVSHAPE2 = SVSHAPE()
    SVSHAPE2.lims = [xdim, 0b000001, 0]
    SVSHAPE2.mode = 0b11
    SVSHAPE2.submode2 = 0b11
    SVSHAPE2.skip = 0b10
    SVSHAPE2.offset = 0       # experiment with different offset, here
    SVSHAPE2.invxyz = [0,0,0] # inversion if desired
    # size schedule
    SVSHAPE3 = SVSHAPE()
    SVSHAPE3.lims = [xdim, 0b000001, 0]
    SVSHAPE3.mode = 0b11
    SVSHAPE3.submode2 = 0b11
    SVSHAPE3.skip = 0b11
    SVSHAPE3.offset = 0       # experiment with different offset, here
    SVSHAPE3.invxyz = [0,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_inner_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_inner_butterfly_indices(SVSHAPE1)
    i2 = iterate_dct_inner_butterfly_indices(SVSHAPE2)
    i3 = iterate_dct_inner_butterfly_indices(SVSHAPE3)
    for k, ((jl, jle), (jh, jhe), (ci, cie), (size, sze)) in \
                enumerate(zip(i0, i1, i2, i3)):
        if redir:
            jl = vec[jl]
            jh = vec[jh]
        print ("xform2", jl, jh, ci, size)
        # jl to jh
        startline = (x, y+jl*ystep)
        endline = (x+xstep, y+jh*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        # plus sign
        dwg.add(dwg.text("+",
                         lineoffs(endline, scale*0.9),
                         fill='black'))
        # jh to jl
        startline = (x, y+jh*ystep)
        endline = (x+xstep, y+jl*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        # times sign
        dwg.add(dwg.text("x",
                         lineoffs(endline, scale*0.9),
                         fill='black'))

        if (jle & 0b010):
            for i in range(n):
                # flat lines
                startline = (x, y+i*ystep)
                endline = (x+xstep, y+i*ystep)
                dwg.add(dwg.line(startline,
                                 endline,
                                 stroke=svgwrite.rgb(16, 255, 16, '%'),
                                 stroke_width=scale/15.0))
            x += xstep * 1.2
        if jle == 0b111: # all loops end
            break

    print("transform2 result", vec)

    dwg.save()


def create_dct(fname, n, redir=True):
    """unsophisticated drawer of an SVG
    """

    try:
        import svgwrite
    except ImportError:
        print ("WARNING, no SVG image, not producing image %s" % fname)
        return

    # Initialization
    vec = range(n)
    print ()
    print ("transform2", n)
    levels = n.bit_length() - 1

    # set up dims
    xdim = n

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # and pretend we LDed data in half-swapped *and* bit-reversed order as well
    # TODO: merge these two
    vec = halfrev2(vec, False)
    vec = [vec[ri[i]] for i in range(n)]

    width = 800
    height = 600
    scale = 15

    dwg = svgwrite.Drawing(fname, profile='full',
                           size=(width, height))

    # outer QFP rect
    dwg.add(dwg.rect((0, 0), (width, height),
            fill='white',
            stroke=svgwrite.rgb(0, 128, 0, '%'),
            stroke_width=scale/5.0))

    # set up an SVSHAPE
    class SVSHAPE:
        pass

    ################
    # INNER butterfly
    ################

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b000001, 0]
    SVSHAPE0.mode = 0b01
    SVSHAPE0.submode2 = 0b01
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [1,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b000001, 0]
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b01
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [1,0,0] # inversion if desired
    # ci schedule
    SVSHAPE2 = SVSHAPE()
    SVSHAPE2.lims = [xdim, 0b000001, 0]
    SVSHAPE2.mode = 0b01
    SVSHAPE2.submode2 = 0b01
    SVSHAPE2.skip = 0b10
    SVSHAPE2.offset = 0       # experiment with different offset, here
    SVSHAPE2.invxyz = [1,0,0] # inversion if desired
    # size schedule
    SVSHAPE3 = SVSHAPE()
    SVSHAPE3.lims = [xdim, 0b000001, 0]
    SVSHAPE3.mode = 0b01
    SVSHAPE3.submode2 = 0b01
    SVSHAPE3.skip = 0b11
    SVSHAPE3.offset = 0       # experiment with different offset, here
    SVSHAPE3.invxyz = [1,0,0] # inversion if desired

    # x start layer
    xstep = width / 10.0
    x = xstep / 2
    ystep = height/(n+1.0)
    y = ystep

    # start data
    for i in range(n):
        # flat lines
        startline = (x-scale, y+i*ystep+scale/2)
        dwg.add(dwg.text("%d" % vec[i],
                         startline,
                         fill='black'))

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_inner_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_inner_butterfly_indices(SVSHAPE1)
    i2 = iterate_dct_inner_butterfly_indices(SVSHAPE2)
    i3 = iterate_dct_inner_butterfly_indices(SVSHAPE3)
    for k, ((jl, jle), (jh, jhe), (ci, cie), (size, sze)) in \
                enumerate(zip(i0, i1, i2, i3)):
        if redir:
            jl = vec[jl]
            jh = vec[jh]
        print ("xform2", jl, jh, ci, size)
        coeff = (math.cos((ci + 0.5) * math.pi / size) * 2.0)
        # jl to jh
        startline = (x, y+jl*ystep)
        endline = (x+xstep, y+jh*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        # plus sign
        dwg.add(dwg.text("+",
                         lineoffs(endline, scale*0.9),
                         fill='black'))
        # jh to jl
        startline = (x, y+jh*ystep)
        endline = (x+xstep, y+jl*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        # times sign
        dwg.add(dwg.text("x",
                         lineoffs(endline, scale*0.9),
                         fill='black'))

        if (jle & 0b010):
            for i in range(n):
                # flat lines
                startline = (x, y+i*ystep)
                endline = (x+xstep, y+i*ystep)
                dwg.add(dwg.line(startline,
                                 endline,
                                 stroke=svgwrite.rgb(16, 255, 16, '%'),
                                 stroke_width=scale/15.0))
            x += xstep * 1.2
        if jle == 0b111: # all loops end
            break

    # break point
    for i in range(n):
        # flat lines
        startline = (x, y+i*ystep)
        endline = (x+xstep, y+i*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/15.0))
    x += xstep * 0.2

    # ####
    # outer
    # ####

    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, 0b0000010, 0]
    SVSHAPE0.submode2 = 0b100
    SVSHAPE0.mode = 0b01
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [0,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, 0b0000010, 0]
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b100
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [0,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_outer_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_outer_butterfly_indices(SVSHAPE1)
    for k, ((jl, jle), (jh, jhe)) in enumerate(zip(i0, i1)):
        if redir:
            jl = vec[jl]
            jh = vec[jh]
        print ("itersum    jr", jl, jh,
                "end", bin(jle), bin(jhe))
        # jh to jl
        startline = (x, y+jh*ystep)
        endline = (x+xstep, y+jl*ystep)
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        # plus sign
        dwg.add(dwg.text("+",
                         lineoffs(endline, scale*0.9),
                         fill='black'))
        if (jle & 0b010):
            for i in range(n):
                # flat lines
                startline = (x, y+i*ystep)
                endline = (x+xstep, y+i*ystep)
                dwg.add(dwg.line(startline,
                                 endline,
                                 stroke=svgwrite.rgb(16, 255, 16, '%'),
                                 stroke_width=scale/15.0))
            x += xstep * 1.2
        if jle == 0b111: # all loops end
            break

    print("transform2 result", vec)

    dwg.save()


if __name__ == '__main__':
    create_dct("dct_butterfly.svg", 16)
    create_idct("idct_butterfly.svg", 16)
