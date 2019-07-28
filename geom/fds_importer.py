# MODULES
# {{{
import json
import shutil
import os
import re
import sys
import codecs
import itertools

from pprint import pprint
from collections import OrderedDict
from shapely.geometry import box, Polygon, LineString, Point, MultiPolygon
from shapely.ops import polygonize
from numpy.random import uniform
from math import sqrt
from math import floor
from include import Sqlite
from include import Json
from include import Dump as dd
from include import Vis

# }}}

class FDSImporter():
    def __init__(self):# {{{
        self.json=Json()
        self.s=Sqlite("{}/aamks.sqlite".format(os.environ['AAMKS_PROJECT']))
        self.raw_geometry=self.json.read("{}/cadfds.json".format(os.environ['AAMKS_PROJECT']))
        self.doors_width=32
        self.walls_width=4
        self._geometry2sqlite()
        self.geomsMap=self.json.read("{}/inc.json".format(os.environ['AAMKS_PATH']))['aamksGeomsMap']
        self._floors_meta()
        self._world_meta()
        #self._terminal_doors()
# }}}

    def _floors_meta(self):# {{{
        ''' 
        Floor dimensions are needed here and there. 
        for z_absolute high towers are not taken under account, we want the natural floor's zdim 
        for z_relative high towers are not taken under account, we want the natural floor's zdim 
        '''

        self.floors=[z['floor'] for z in self.s.query("SELECT DISTINCT floor FROM aamks_geom ORDER BY floor")]
        self.floors_meta=OrderedDict()
        self._world3d=dict()
        self._world3d['minx']=9999999
        self._world3d['maxx']=-9999999
        self._world3d['miny']=9999999
        self._world3d['maxy']=-9999999
        prev_maxz=0
        for floor in self.floors:
            world2d_ty=0
            world2d_tx=0
            minx=self.s.query("SELECT min(x0) AS minx FROM aamks_geom WHERE floor=?", (floor,))[0]['minx']
            maxx=self.s.query("SELECT max(x1) AS maxx FROM aamks_geom WHERE floor=?", (floor,))[0]['maxx']
            miny=self.s.query("SELECT min(y0) AS miny FROM aamks_geom WHERE floor=?", (floor,))[0]['miny']
            maxy=self.s.query("SELECT max(y1) AS maxy FROM aamks_geom WHERE floor=?", (floor,))[0]['maxy']
            minz_abs=self.s.query("SELECT min(z0) AS minz FROM aamks_geom WHERE type_sec NOT IN('STAI','HALL') AND floor=?", (floor,))[0]['minz']
            maxz_abs=self.s.query("SELECT max(z1) AS maxz FROM aamks_geom WHERE type_sec NOT IN('STAI','HALL') AND floor=?", (floor,))[0]['maxz']
            zdim=maxz_abs - prev_maxz
            prev_maxz=maxz_abs

            xdim= maxx - minx
            ydim= maxy - miny
            center=(minx + int(xdim/2), miny + int(ydim/2), minz_abs)
            self.floors_meta[floor]=OrderedDict([('name', floor), ('xdim', xdim) , ('ydim', ydim) , ('center', center), ('minx', minx) , ('miny', miny) , ('maxx', maxx) , ('maxy', maxy), ('minz_abs', minz_abs), ('maxz_abs', maxz_abs) , ('zdim', zdim), ('world2d_ty', world2d_ty), ('world2d_tx', world2d_tx)  ])

            self._world3d['minx']=min(self._world3d['minx'], minx)
            self._world3d['maxx']=max(self._world3d['maxx'], maxx)
            self._world3d['miny']=min(self._world3d['miny'], miny)
            self._world3d['maxy']=max(self._world3d['maxy'], maxy)

        self.s.query("CREATE TABLE floors_meta(json)")
        self.s.query('INSERT INTO floors_meta VALUES (?)', (json.dumps(self.floors_meta),))

# }}}
    def _world_meta(self):# {{{
        self.s.query("CREATE TABLE world_meta(json)")
        self.world_meta={}
        self.world_meta['world3d']=self._world3d
        self.world_meta['walls_width']=self.walls_width
        self.world_meta['doors_width']=self.doors_width

        if len(self.floors_meta) > 1:
            self.world_meta['multifloor_building']=1
        else: 
            self.world_meta['multifloor_building']=0

        self.s.query('INSERT INTO world_meta(json) VALUES (?)', (json.dumps(self.world_meta),))

# }}}
    def _geometry2sqlite(self):# {{{

        data=[]
        for floor,gg in self.raw_geometry.items():
            for k,arr in gg.items():
                if k in ('META'):
                    continue
                for v in arr:
                    zz=list(zip(*v['points']))
                    bbox=[ int(min(zz[0])), int(min(zz[1])), int(max(zz[0])), int(max(zz[1])) ]
                    attrs=self._prepare_attrs(v)
                    record=self._prepare_geom_record(k,v,bbox,floor,attrs, gg['META'])
                    if record != False:
                        data.append(record)
        self.s.query("CREATE TABLE aamks_geom(name,floor,type_pri,type_sec,type_tri,x0,y0,z0,x1,y1,z1,global_type_id,exit_type, room_enter, terminal_door, points)")
        self.s.executemany('INSERT INTO aamks_geom VALUES ({})'.format(','.join('?' * len(data[0]))), data)
        dd(self.s.dump())
#}}}
    def _prepare_attrs(self,v):# {{{
        aa={"exit_type": None, "room_enter": None }
        if 'attrs' in v:
            for k,v in attrs.items():
                aa[k]=v
        return aa
# }}}
    def _prepare_geom_record(self,k,v,bbox,floor,attrs,meta):# {{{
        ''' Format a record for sqlite. Hvents get fixed width self.doors_width cm '''
        # OBST
        if k in ('OBST',):
            type_pri='OBST'
            type_tri=''

        # EVACUEE
        elif k in ('EVACUEE',):                  
            type_pri='EVACUEE'
            type_tri=''

        # FIRE
        elif k in ('FIRE',):                  
            type_pri='FIRE'
            type_tri=''

        # MVENT      
        elif k in ('MVENT',):                  
            type_pri='MVENT'
            type_tri=''

        # VVENT      
        elif k in ('VVENT',):                  
            type_pri='VVENT'
            height=10 
            type_tri=''

        # COMPA
        elif k in ('ROOM', 'COR', 'HALL', 'STAI'):      
            type_pri='COMPA'
            type_tri=''
        
        
        # HVENT  
        elif k in ('DOOR', 'DCLOSER', 'DELECTR', 'HOLE', 'WIN'): 
            type_pri='HVENT'
            if k in ('DOOR', 'DCLOSER', 'DELECTR', 'HOLE'): 
                type_tri='DOOR'
            elif k in ('WIN'):
                type_tri='WIN'

        if 'name' not in v:
            v['name']=''

        #self.s.query("CREATE TABLE aamks_geom(name , floor , type_pri , type_sec , type_tri , x0      , y0      , z0         , x1      , y1      , z1         , global_type_id , exit_type          , room_enter          , terminal_door , points)")
        return (v['name']                           , floor , type_pri , k        , type_tri , bbox[0] , bbox[1] , meta['z0'] , bbox[0] , bbox[1] , meta['z1'] , None           , attrs['exit_type'] , attrs['room_enter'] , None          , json.dumps(v['points']))

# }}}
    def _terminal_doors(self):# {{{
        ''' 
        Doors that lead to outside or lead to staircases are terminal
        '''
        terminal_rooms=self.s.query("SELECT global_type_id FROM aamks_geom WHERE type_sec='STAI'")

        update=[]
        for i in terminal_rooms:
            z=self.s.query("SELECT name,exit_type FROM aamks_geom WHERE type_pri='HVENT' AND (vent_from=? OR vent_to=? OR vent_to_name='outside')", (i['global_type_id'], i['global_type_id']))
            for ii in z:
                update.append((ii['exit_type'], ii['name']))
        self.s.executemany("UPDATE aamks_geom SET terminal_door=? WHERE name=?", update)
        #dd(self.s.query("SELECT name,terminal_door,vent_from_name,vent_to_name from aamks_geom order by name"))

# }}}
    def _debug(self):# {{{
        #dd(os.environ['AAMKS_PROJECT'])
        #self.s.dumpall()
        #self.s.dump_geoms()
        #dd(self.s.query("select * from aamks_geom"))
        #dd(self.s.query("select * from world2d"))
        #exit()
        #self.s.dump()
        pass
        
# }}}
