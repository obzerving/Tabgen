#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) [2022] [Joseph Zakar], [observing@gmail.com]
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
Given a closed path of straight lines, this program generates a paper model containing
tabs and score lines for each straight edge marked by line paths of a specific color.
"""

import inkex
import math
import copy
import inspect

from inkex import PathElement, Style
from inkex.paths import Move, Line, ZoneClose, Path
from inkex.elements._groups import Group
from inkex.transforms import Vector2d

class pathStruct(object):
    def __init__(self):
        self.id="path0000"
        self.path=Path()
        self.enclosed=False
        self.tabmarker=False
        self.style = None
    def __str__(self):
        return self.path
    
class pnPoint(object):
   # This class came from https://github.com/JoJocoder/PNPOLY
    def __init__(self,p):
        self.p=p
    def __str__(self):
        return self.p
    def InPolygon(self,polygon,BoundCheck=False):
        inside=False
        if BoundCheck:
            minX=polygon[0][0]
            maxX=polygon[0][0]
            minY=polygon[0][1]
            maxY=polygon[0][1]
            for p in polygon:
                minX=min(p[0],minX)
                maxX=max(p[0],maxX)
                minY=min(p[1],minY)
                maxY=max(p[1],maxY)
            if self.p[0]<minX or self.p[0]>maxX or self.p[1]<minY or self.p[1]>maxY:
                return False
        j=len(polygon)-1
        for i in range(len(polygon)):
            if ((polygon[i][1]>self.p[1])!=(polygon[j][1]>self.p[1]) and (self.p[0]<(polygon[j][0]-polygon[i][0])*(self.p[1]-polygon[i][1])/( polygon[j][1] - polygon[i][1] ) + polygon[i][0])):
                    inside =not inside
            j=i
        return inside

class Tabgen(inkex.EffectExtension):
    
    def add_arguments(self, pars):
        pars.add_argument("--usermenu")
        pars.add_argument("--tabangle", type=float, default=45.0,\
            help="Angle of tab edges in degrees")
        pars.add_argument("--tabheight", type=float, default=0.4,\
            help="Height of tab in dimensional units")
        pars.add_argument("--dashlength", type=float, default=0.1,\
            help="Length of dashline in dimentional units (zero for solid line)")
        pars.add_argument("--tabsets", default="both",\
            help="Tab placement on polygons with cutouts")
        pars.add_argument("--dashcolor", type=str, dest="dashcolor", default="#00ff00",\
            help="Color of scorelines when solid")
        pars.add_argument("--markercolor", type=str, dest="markercolor", default="#ff0000",\
            help="Color of lines for marking tabs")
        pars.add_argument("--tabmarker", type=inkex.Boolean, dest="tabmarker", default=False,\
            help="Check to put tabs where there are lines of above color; uncheck for opposite")
        pars.add_argument("--unit", default="in",\
            help="Dimensional units of selected paths")

    #draw SVG line segment(s) between the given (raw) points
    def drawline(self, dstr, name, parent, sstr=None):
        line_style   = {'stroke':'#000000','stroke-width':'0.25','fill':'#eeeeee'}
        if sstr == None:
            stylestr = str(Style(line_style))
        else:
            stylestr = sstr
        el = parent.add(PathElement())
        el.path = dstr
        el.style = stylestr
        el.label = name

    def pathInsidePath(self, path, testpath):
        enclosed = True
        for tp in testpath:
            # If any point in the testpath is outside the path, it's not enclosed
            if self.insidePath(path, tp) == False:
                enclosed = False
                return enclosed # True if testpath is fully enclosed in path
        return enclosed
        
    def insidePath(self, path, p):
        point = pnPoint((p.x, p.y))
        pverts = []
        for pnum in path:
            if pnum.letter == 'Z':
                pverts.append((path[0].x, path[0].y))
            else:
                pverts.append((pnum.x, pnum.y))
        isInside = point.InPolygon(pverts, True)
        return isInside # True if point p is inside path

    def makescore(self, pt1, pt2, dashlength):
        # Draws a dashed line of dashlength between two points
        # Dash = dashlength space followed by dashlength mark
        # if dashlength is zero, we want a solid line
        # Returns dashed line as a Path object
        apt1 = Line(0.0,0.0)
        apt2 = Line(0.0,0.0)
        ddash = Path()
        if math.isclose(dashlength, 0.0):
            #inkex.utils.debug("Draw solid dashline")
            ddash.append(Move(pt1.x,pt1.y))
            ddash.append(Line(pt2.x,pt2.y))
        else:
            if math.isclose(pt1.y, pt2.y):
                #inkex.utils.debug("Draw horizontal dashline")
                if pt1.x < pt2.x:
                    xcushion = pt2.x - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    xcushion = pt1.x - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if (xpt + dashlength*2) <= xcushion:
                        xpt = xpt + dashlength
                        ddash.append(Move(xpt,ypt))
                        xpt = xpt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            elif math.isclose(pt1.x, pt2.x):
                #inkex.utils.debug("Draw vertical dashline")
                if pt1.y < pt2.y:
                    ycushion = pt2.y - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    ycushion = pt1.y - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if(ypt + dashlength*2) <= ycushion:
                        ypt = ypt + dashlength         
                        ddash.append(Move(xpt,ypt))
                        ypt = ypt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            else:
                #inkex.utils.debug("Draw sloping dashline")
                if pt1.y > pt2.y:
                    apt1 = Line(pt1.x,pt1.y)
                    #apt1.x = pt1.x
                    #apt1.y = pt1.y
                    apt2 = Line(pt2.x,pt2.y)
                    #apt2.x = pt2.x
                    #apt2.y = pt2.y
                else:
                    apt1 = Line(pt2.x,pt2.y)
                    #apt1.x = pt2.x
                    #apt1.y = pt2.y
                    apt2 = Line(pt1.x,pt1.y)
                    #apt2.x = pt1.x
                    #apt2.y = pt1.y
                m = (apt1.y-apt2.y)/(apt1.x-apt2.x)
                theta = math.atan(m)
                msign = (m>0) - (m<0)
                ycushion = apt2.y + dashlength*math.sin(theta)
                xcushion = apt2.x + msign*dashlength*math.cos(theta)
                xpt = apt1.x
                ypt = apt1.y
                done = False
                while not(done):
                    nypt = ypt - dashlength*2*math.sin(theta)
                    nxpt = xpt - msign*dashlength*2*math.cos(theta)
                    if (nypt >= ycushion) and (((m<0) and (nxpt <= xcushion)) or ((m>0) and (nxpt >= xcushion))):
                        # move to end of space / beginning of mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Move(xpt,ypt))
                        # draw the mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
        return ddash

    def detectIntersect(self, x1, y1, x2, y2, x3, y3, x4, y4):
        td = (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
        if td == 0:
            # These line segments are parallel
            return False
        t = ((x1-x3)*(y3-y4)-(y1-y3)*(x3-x4))/td
        if (0.0 <= t) and (t <= 1.0):
            return True
        else:
            return False

    def orientTab(self,pt1,pt2,height,angle,theta,orient):
        tpt1 = Line(pt1.x + orient[0]*height + orient[1]*height/math.tan(math.radians(angle)),pt1.y + orient[4]*height + orient[5]*height/math.tan(math.radians(angle)))
        tpt2 = Line(pt2.x + orient[2]*height + orient[3]*height/math.tan(math.radians(angle)),pt2.y + orient[6]*height + orient[7]*height/math.tan(math.radians(angle)))
        if not math.isclose(theta, 0.0):
            t11 = Path([Move(pt1.x,pt1.y),Line(tpt1.x, tpt1.y)])
            t12 = Path([Move(pt1.x,pt1.y),Line(tpt2.x, tpt2.y)])
            thetal1 = t11.rotate(theta, [pt1.x,pt1.y])
            thetal2 = t12.rotate(theta, [pt2.x,pt2.y])
            tpt1 = Line(thetal1[1].x,thetal1[1].y)
            #tpt1.x = thetal1[1].x
            #tpt1.y = thetal1[1].y
            tpt2 = Line(thetal2[1].x,thetal2[1].y)
            #tpt2.x = thetal2[1].x
            #tpt2.y = thetal2[1].y
        return tpt1,tpt2

    def makeTab(self, tpath, pt1, pt2, tabht, taba):
        # tpath - the pathstructure containing pt1 and pt2
        # pt1, pt2 - the two points where the tab will be inserted
        # tabht - the height of the tab
        # taba - the angle of the tab sides
        # returns the two tab points (Line objects) in order of closest to pt1
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        currTabHt = tabht
        currTabAngle = taba
        testAngle = 1.0
        testHt = currTabHt * 0.001
        adjustTab = 0
        tabDone = False
        while not tabDone:
            # Let's find out the orientation of the tab
            if math.isclose(pt1.x, pt2.x):
                # It's vertical. Let's try the right side
                if pt1.y < pt2.y:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,1,0,-1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,1,0,-1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,1,0,-1]) # Guessed right
                else: # pt2.y < pt1.y
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,-1,0,1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,-1,0,1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,-1,0,1]) # Guessed right
            elif math.isclose(pt1.y, pt2.y):
                # It's horizontal. Let's try the top
                if pt1.x < pt2.x:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,1,0,-1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                else: # pt2.x < pt1.x
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,-1,0,1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,-1,0,-1,0]) # Guessed right

            else: # the orientation is neither horizontal nor vertical
                # Let's get the slope of the line between the points
                # Because Inkscape's origin is in the upper-left corner,
                # a positive slope (/) will yield a negative value
                slope = (pt2.y - pt1.y)/(pt2.x - pt1.x)
                # Let's get the angle to the horizontal
                theta = math.degrees(math.atan(slope))
                # Let's construct a horizontal tab
                seglength = math.sqrt((pt1.x-pt2.x)**2 +(pt1.y-pt2.y)**2)
                if slope < 0.0:
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
                else: # slope > 0.0
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,+1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
            # Check to see if any tabs intersect each other
            if self.detectIntersect(pt1.x, pt1.y, tpt1.x, tpt1.y, pt2.x, pt2.y, tpt2.x, tpt2.y):
                # Found an intersection.
                if adjustTab == 0:
                    # Try increasing the tab angle in one-degree increments
                    currTabAngle = currTabAngle + 1.0
                    if currTabAngle > 88.0: # We're not increasing the tab angle above 89 degrees
                        adjustTab = 1
                        currTabAngle = taba
                if adjustTab == 1:
                    # So, try reducing the tab height in 20% increments instead
                    currTabHt = currTabHt - tabht*0.2 # Could this lead to a zero tab_height?
                    if currTabHt <= 0.0:
                        # Give up
                        currTabHt = tabht
                        adjustTab = 2
                if adjustTab == 2:
                    tabDone = True # Just show the failure
            else:
                tabDone = True
            
        return tpt1,tpt2

    def checkForTab(self, pt1, pt2, tablist, marker):
        # if marker is true, we want to return true if we find the pts in the tablist
        for tabpts in tablist:
            if math.isclose(pt1.x,tabpts[0].x,abs_tol=0.001) and math.isclose(pt1.y,tabpts[0].y,abs_tol=0.001):
                if math.isclose(pt2.x,tabpts[1].x,abs_tol=0.001) and math.isclose(pt2.y,tabpts[1].y,abs_tol=0.001):
                    return marker
            if math.isclose(pt1.x,tabpts[1].x,abs_tol=0.001) and math.isclose(pt1.y,tabpts[1].y,abs_tol=0.001):
                if math.isclose(pt2.x,tabpts[0].x,abs_tol=0.001) and math.isclose(pt2.y,tabpts[0].y,abs_tol=0.001):
                    return marker
        return (not marker)
                    
                    
    def effect(self):
        scale = self.svg.unittouu('1'+self.options.unit)
        layer = self.svg.get_current_layer()
        tab_angle = float(self.options.tabangle)
        tab_height = float(self.options.tabheight) * scale
        dashlength = float(self.options.dashlength) * scale
        tabmarker = self.options.tabmarker
        markercolor = str(self.options.markercolor)
        dashcolor = str(self.options.dashcolor)
        tabsets = self.options.tabsets
        tablist = [] # contains pairs of points to put (or not put) tabs
        npaths = []
        savid = ''
        elems = []
        pc = 0
        sstr = None
        for selem in self.svg.selection.filter(PathElement):
            copyflag = False
            if 'style' in selem.attrib:
                lsstr = selem.attrib['style'].split(';')
                for stoken in range(len(lsstr)):
                    if lsstr[stoken].startswith('stroke:'):
                        swt = lsstr[stoken].split(':')[1]
                        if swt == markercolor:
                            # stroke is markercolor. move element to the front of the list
                            elems.insert(0,copy.deepcopy(selem))
                            selem.delete() # and get rid of the original
                        else:
                            elems.append(copy.deepcopy(selem))
                        copyflag = True
            else: # no style property; just copy it
                elems.append(copy.deepcopy(selem))
                copyflag = True
            if not copyflag:
                elems.append(copy.deepcopy(selem))  
        if len(elems) == 0:
            raise inkex.AbortExtension("Nothing selected")
        for elem in elems:
            escale = 1.0
            npaths.clear()
            if 'transform' in elem.attrib:
                transforms = elem.attrib['transform'].split()
                for tf in transforms:
                    if tf.startswith('scale'):
                        escale = float(tf.split('(')[1].split(')')[0])
                if 'style' in elem.attrib:
                    lsstr = elem.attrib['style'].split(';')
                    strokeflag = False
                    for stoken in range(len(lsstr)):
                        if lsstr[stoken].startswith('stroke-width'):
                            swt = lsstr[stoken].split(':')[1]
                            if not swt[2:].isalpha(): # is value expressed in units (e.g. px)?
                                swf = str(float(swt)*escale) # no. scale it
                                lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                        if lsstr[stoken].startswith('stroke-miterlimit'):
                            swt = lsstr[stoken].split(':')[1]
                            if not swt[2:].isalpha(): # is value expressed in units (e.g. px)?
                                swf = str(float(swt)*escale) # no. scale it
                                lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                        if lsstr[stoken].startswith('stroke'):
                            strokeflag = True
                    if not strokeflag:
                        lsstr.append('stroke:none')
                    sstr = ";".join(lsstr)
                else:
                    sstr = None
                elem.apply_transform()
            last_letter = 'Z'
            savid = elem.get_id()
            idmod = 0
            for ptoken in elem.path.to_absolute(): # For each point in the path
                if ptoken.letter == 'M': # Starting point
                    # Hold this point in case we receive a Z
                    ptx1 = mx = ptoken.x
                    pty1 = my = ptoken.y
                    '''
                    Assign a structure to the new path. We assume that there is
                    only one path and, therefore, it isn't enclosed by another
                    path. However, we'll suffix the ID, if we find a
                    sub-path.
                    '''
                    npath = pathStruct()
                    npath.enclosed = False
                    if sstr == None:
                        if 'style' in elem.attrib:
                            lsstr = elem.attrib['style'].split(';')
                            for stoken in range(len(lsstr)):
                                if lsstr[stoken].startswith('stroke:'):
                                    swt = lsstr[stoken].split(':')[1]
                                    if swt == markercolor:
                                        # stroke is markercolor. This is tab marker
                                        npath.tabmarker = True
                            npath.style = elem.attrib['style']
                    else:
                        npath.style = sstr
                    if not npath.tabmarker: # tabmarkers don't get an id
                        if idmod > 0:
                            npath.id = elem.get_id()+"-"+str(idmod)
                        else:
                            npath.id = elem.get_id()
                        idmod += 1
                    npath.path.append(Move(ptx1,pty1))
                elif npath != None: # This condition is part of a workaround described further down
                    if last_letter != 'M':
                        ptx1 = ptx2
                        pty1 = pty2
                    if ptoken.letter == 'L':
                        ptx2 = ptoken.x
                        pty2 = ptoken.y
                    elif ptoken.letter == 'H':
                        ptx2 = ptoken.x
                        pty2 = pty1
                    elif ptoken.letter == 'V':
                        ptx2 = ptx1
                        pty2 = ptoken.y
                    elif ptoken.letter == 'Z':
                        ptx2 = mx
                        pty2 = my
                    else:
                        raise inkex.AbortExtension("Unrecognized path command {0}".format(ptoken.letter))
                    npath.path.append(Line(ptx2,pty2))
                    if ptoken.letter == 'Z' or ((ptx2 == mx) and (pty2 == my)):
                        if npath.style != None:
                            if npath.tabmarker:
                                # add its points to tab list
                                    for npts in range(len(npath.path)-1):
                                        tablist.append([npath.path[npts], npath.path[npts+1]])
                                    # don't need this path anymore so delete it
                                    elem.delete()
                                    npath = None
                            else:
                                npaths.append(npath)
                                npath = None
                        else:
                            npaths.append(npath)
                            npath = None
                else:
                    # We could have ended up here if the original input path's last point was equal to
                    # its first point and the next path command was a 'z'. This is a workaround for
                    # what I think is an improperly closed path.
                    pass
                last_letter = ptoken.letter
            # finished reading in the path
            if npath != None: # Was this path not closed?
                if npath.style != None:
                    if npath.tabmarker:
                        # add its points to tab list
                        for npts in range(len(npath.path)-1):
                            tablist.append([npath.path[npts], npath.path[npts+1]])
                        # don't need this path anymore so delete it
                        elem.delete()
                        npath = None
                    else:
                        raise inkex.AbortExtension("Only tab markers can be open paths")
            # check for cutouts
            if idmod > 1:
                for apath in npaths: # We test these paths to see if they are fully enclosed
                    for bpath in npaths: # by these paths
                        if apath.id != bpath.id:
                            if self.pathInsidePath(bpath.path, apath.path):
                                apath.enclosed = True
            if len(npaths) > 0:
                # add tabs to current path(s)
                dsub = Path() # Used for building sub-paths
                dprop = Path() # Used for building the main path
                dscore = Path() # Used for building dashlines
                dstyle = None
                for apath in npaths:
                    dstyle = apath.style
                    mpath = Path()
                    mpath.append(Move(apath.path[0].x,apath.path[0].y)) # init output path with first point of input path
                    for ptn in range(len(apath.path)-1):
                        if (tabsets == 'both') or (((tabsets == 'inside') and (apath.enclosed)) or ((tabsets == 'outside') and (not apath.enclosed))):
                            if self.checkForTab(apath.path[ptn],apath.path[ptn+1],tablist,tabmarker):
                                tabpt1, tabpt2 = self.makeTab(apath, apath.path[ptn], apath.path[ptn+1], tab_height, tab_angle)
                                mpath.append(tabpt1)
                                mpath.append(tabpt2)
                                dscore = dscore + self.makescore(apath.path[ptn], apath.path[ptn+1],dashlength)
                        mpath.append(apath.path[ptn+1])
                    if apath.id == elem.get_id():
                        for nodes in range(len(mpath)):
                            if nodes == 0:
                                dprop.append(Move(mpath[nodes].x,mpath[nodes].y)) # This is the main path, which should appear first
                            else:
                                dprop.append(Line(mpath[nodes].x,mpath[nodes].y))
                        # and close the path
                        dprop.append(ZoneClose())
                    else:
                        for nodes in range(len(mpath)):
                            if nodes == 0:
                                dsub.append(Move(mpath[nodes].x,mpath[nodes].y)) # This is the sub path, which should appear after the main one
                            else:
                                dsub.append(Line(mpath[nodes].x,mpath[nodes].y))
                        # and close the path
                        dsub.append(ZoneClose())
                dprop = dprop + dsub # combine all the paths
                if math.isclose(dashlength, 0.0):
                    # lump together all the score lines
                    group = Group()
                    group.label = 'group'+str(pc)+'ms'
                    self.drawline(str(dprop),'model'+str(pc),group,dstyle) # Output the model
                    if dscore != '':
                        if dstyle == None:
                            dlstyle = str(Style({'stroke':'#00ff00','stroke-width':'0.25','fill':'#eeeeee'}))
                        else:
                            strokeflag = False
                            lsstr = dstyle.split(';')
                            for stoken in range(len(lsstr)):
                                if lsstr[stoken].startswith('stroke:'):
                                    swt = lsstr[stoken].split(':')[1]
                                    lsstr[stoken] = lsstr[stoken].replace(swt, dashcolor)
                                    strokeflag = True
                            if not strokeflag:
                                lsstr.append('stroke:'+dashcolor)
                            dlstyle = ";".join(lsstr)
                        self.drawline(str(dscore),'score'+str(pc),group,dlstyle) # Output the scorelines separately
                    layer.append(group)
                else:
                    dprop = dscore + dprop
                    self.drawline(str(dprop),savid+'ms',layer,dstyle)
                pc += 1

if __name__ == '__main__':
    Tabgen().run()
