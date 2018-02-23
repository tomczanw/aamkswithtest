# IMPORT# {{{
from collections import OrderedDict
import itertools
import numpy as np
import os
import sys
import inspect
import json
from shapely.geometry import box, Polygon, LineString, Point, MultiPolygon
from numpy.random import randint
from include import Sqlite
from include import Json
from include import Dump as dd
from gui.vis.vis import Vis

# }}}

class CfastTessellate():
    def __init__(self): # {{{
        ''' 
        Divide space into cells for smoke conditions queries asked by evacuees.
        A cell may be a square or a rectangle. First divide space into squares
        of self._square_side. Iterate over squares and if any square is crossed by an
        obstacle divide this square further into rectangles. 
        
        In the final structure of tessellation.json we encode each cell.
        Each cell is sorted by x, which allows quick bisections.

        * In each cell we always encode the first sub-cell - the square itself.
        (2000, 2449): OrderedDict([('x', (2000,)), ('y', (2449,))])

        * Then we can add more sub-cells (rectangles).
        (1600, 2449): OrderedDict([('x', (1600, 1600, 1842, 1842)), ('y', (2449, 2541, 2449, 2541))])

        Tessellation will be later used for filling the cells with smoke
        conditions. Finally we get a tool for quick altering of the state of an
        evacuee at x,y.

        '''

        self._square_side=300
        self.s=Sqlite("{}/aamks.sqlite".format(os.environ['AAMKS_PROJECT']))
        try:
            self.s.query("DROP TABLE tessellation")
        except:
            pass
        self.s.query("CREATE TABLE tessellation(json)")

        self.json=Json() 
        self._save=OrderedDict()
        floors=json.loads(self.s.query("SELECT * FROM floors")[0]['json'])
        for floor in floors.keys():
            self._init_space(floor) 
            self._intersect_space() 
            self._optimize(floor)
            # self._plot_space(floor)  # debug
        #Vis(None, 'image', 'tessellation') # debug
        self._dbsave()
# }}}
    def _init_space(self,floor):# {{{
        ''' Divide floor into squares. Prepare empty rectangles placeholders. '''

        floors=json.loads(self.s.query("SELECT * FROM floors")[0]['json'])
        fdims=floors[floor]

        self.squares=OrderedDict()
        self.rectangles=OrderedDict()
        self.lines=[]

        for i in self.s.query("SELECT * FROM aamks_geom WHERE type_pri='COMPA' ORDER BY x0,y0"):
            self.lines.append(LineString([ Point(i['x0'],i['y0']), Point(i['x0'], i['y1'])] ))
            self.lines.append(LineString([ Point(i['x0'],i['y0']), Point(i['x1'], i['y0'])] ))
            self.lines.append(LineString([ Point(i['x1'],i['y1']), Point(i['x0'], i['y1'])] ))
            self.lines.append(LineString([ Point(i['x1'],i['y1']), Point(i['x1'], i['y0'])] ))

        x=int(fdims['width']/self._square_side)+1
        y=int(fdims['height']/self._square_side)+1
        for v in range(y):
            for i in range(x):
                x_=fdims['minx']+self._square_side*i
                y_=fdims['miny']+self._square_side*v
                xy=(x_, y_)
                self.squares[xy]=box(x_, y_, x_+self._square_side, y_+self._square_side)
                self.rectangles[xy]=[]
# }}}
    def _candidate_intersection(self,id_,points):# {{{
        ''' 
        So there's an intersection "points" of the square and the walls of the
        room. We get 2 points in this call. Should we create a rectangle of any
        of these points? The rectangle is defined by it's (minX,minY) vertex.
        We only accept the points that belong to the square but don't lie on
        the maxX (right) and maxY (top) edges. 
        '''

        right_limit=id_[0]+self._square_side
        top_limit=id_[1]+self._square_side
        for pt in list(zip(points.xy[0], points.xy[1])):
            if right_limit != pt[0] and top_limit != pt[1]:
                self.rectangles[id_].append((int(pt[0]), int(pt[1])))
# }}}
    def _optimize(self, floor):# {{{
        ''' 
        * self.squares (collection of shapely boxen) is not needed anymore
        * self.rectangles must have duplicates removed and must be sorted by x
        * xy_vectors must be of the form: [ [x0,x1,x2,x3], [y0,y1,y2,y3] ]. 

        query_vertices are of the form:

        square        : optimized rectangles 
        (1000 , -1000): OrderedDict([('x' , (1000 , 1100)) , ('y' , (-1000 , -1000))])
        (1400 , -1000): OrderedDict([('x' , (1400 , 1500)) , ('y' , (-1000 , -1000))])
        (1800 , -1000): OrderedDict([('x' , (1800 , ))     , ('y' , (-1000 , ))])
        (2200 , -1000): OrderedDict([('x' , (2200 , ))     , ('y' , (-1000 , ))])
        '''

        del(self.squares)

        for id_,rects in self.rectangles.items():
            rects.append(id_)
            self.rectangles[id_]=list(sorted(set(rects)))

        query_vertices=OrderedDict()
        for id_,v in self.rectangles.items():
            query_vertices[str(id_)]=OrderedDict()
            xy_vectors=list(zip(*self.rectangles[id_]))
            try:
                query_vertices[str(id_)]['x']=xy_vectors[0]
                query_vertices[str(id_)]['y']=xy_vectors[1]
            except:
                query_vertices[str(id_)]['x']=()
                query_vertices[str(id_)]['y']=()

        self._save[floor]=OrderedDict()
        self._save[floor]['square_side']=self._square_side
        self._save[floor]['query_vertices']=query_vertices

# }}}
# }}}
    def _intersect_space(self):# {{{
        ''' 
        We want to further tessellate the square into rectangles based on obstacles.
        '''

        for line in self.lines: 
            for id_,square in self.squares.items():
                if square.intersects(line):
                    points=square.intersection(line)
                    if points.length>0:
                        self._candidate_intersection(id_,points)
        
# }}}
    def _plot_space(self,floor):# {{{
        ''' 
        Plots the tessellation on top of the rooms. 
        '''

        z=self.json.read('{}/dd_geoms.json'.format(os.environ['AAMKS_PROJECT']))

        radius=5
        a=self._square_side
        for k,v in self.rectangles.items():
            z[floor]['rectangles'].append( { "xy": k, "width": a , "depth": a , "strokeColor": "#f80" , "strokeWidth": 20 , "opacity": 0.2 } )
            z[floor]['circles'].append(    { "xy": k, "radius": radius , "fillColor": "#fff", "opacity": 0.3 } )
            z[floor]['texts'].append(      { "xy": k, "content": k, "fontSize": 5, "fillColor":"#f0f", "opacity":0.7 })
            for mm in v:
                z[floor]['circles'].append( { "xy": mm, "radius": radius, "fillColor": "#fff", "opacity": 0.3 } )
                z[floor]['texts'].append(   { "xy": mm, "content": mm, "fontSize": 5, "fillColor":"#f0f", "opacity":0.7 })
        self.json.write(z, '{}/dd_geoms.json'.format(os.environ['AAMKS_PROJECT']))
# }}}
    def _dbsave(self):# {{{
        self.s.query('INSERT INTO tessellation VALUES (?)', (json.dumps(self._save),))
# }}}
