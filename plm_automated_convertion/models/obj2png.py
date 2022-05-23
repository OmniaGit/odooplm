# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 00:41:00 2018
@author: Peter M. Clausen, pclausen
MIT License
Copyright (c) 2018 pclausen
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

RE=re.compile(r'/\d+')

class ObjFile:
    """
    >>> obj_file = '../obj/bun_zipper_res2.obj'
    >>> out_file = '../obj/bun_zipper_res2.png'
    >>> obj = ObjFile(obj_file)
    >>> len(obj.nodes)==8147
    True
    >>> len(obj.faces)==16301
    True
    >>> nmin,nmax=obj.MinMaxNodes()
    >>> np.allclose(nmin, np.array([-0.094572,  0.      , -0.061874]) )
    True
    >>> np.allclose(nmax, np.array([0.060935, 0.186643, 0.05869 ]))
    True
    >>> obj.Plot(out_file)
    """
    
    def __init__(self, obj_file=None):
        self.nodes=None
        self.faces=None
        if obj_file:
            self.ObjParse(obj_file)
        
    def ObjInfo(self):
        print ("Num vertices  :    %d"%(len(self.nodes)))
        print ("Num faces     :    %d"%(len(self.faces))) 
        nmin,nmax=self.MinMaxNodes()
        print ("Min/Max       :    %s %s"%(np.around(nmin,3), np.around(nmax,3) ))

    @staticmethod
    def MinMax3d(arr):
        nmin=1E9*np.ones((3))
        nmax=-1E9*np.ones((3))
        for a in arr:
            for i in range(3):
                nmin[i]=min(nmin[i],a[i])
                nmax[i]=max(nmax[i],a[i])    
        return (nmin,nmax)
        
    def MinMaxNodes(self):
        return ObjFile.MinMax3d(self.nodes)
        

    def ObjParse(self, obj_file ):
        f=open(obj_file)
        lines=f.readlines()
        f.close()
        nodes=[]
        # add zero entry to get ids right
        nodes.append([.0,.0,.0])
        faces=[]
        for line in lines:
            if 'v' == line[0] and line[1].isspace(): # do not match "vt" or "vn"
                v=line.split()
                nodes.append( ObjFile.ToFloats(v[1:])[:3] )
            if 'f' == line[0]:
                # remove /int 
                line=re.sub(RE,'',line)                
                f=line.split()
                faces.append(ObjFile.ToInts(f[1:]))
    
        self.nodes=np.array(nodes)
        assert(np.shape(self.nodes)[1]==3)
        self.faces=faces    


    def ObjWrite(self, obj_file):
        f=open(obj_file, 'w')
        for n in self.nodes[1:]: # skip first dummy 'node'
            f.write('v ')
            for nn in n:
                f.write('%g '%(nn))
            f.write('\n')
        for ff in self.faces:
            f.write('f ')
            for fff in ff:
                f.write('%d '%(fff))
            f.write('\n')

            
    @staticmethod
    def ToFloats(n):
        if isinstance(n,list):
            v=[]
            for nn in n:
                v.append(float(nn))
            return v
        else:
            return float(n)
                
    @staticmethod
    def ToInts(n):
        if isinstance(n,list):
            v=[]
            for nn in n:
                v.append(int(nn.replace("/",'')))
            return v
        else:
            return int(n)
                
    @staticmethod
    def Normalize(v):
        v2=np.linalg.norm(v)
        if v2<0.000000001:
            return v
        else:
            return v/v2
    
    def QuadToTria(self):
        trifaces=[]
        for f in self.faces:
            if len(f)==3:
                trifaces.append(f)
            elif len(f)==4:
                f1=[f[0],f[1],f[2]]
                f2=[f[0],f[2],f[3]]
                trifaces.append(f1)
                trifaces.append(f2)
        return trifaces
    
    @staticmethod
    def ScaleVal(v,scale,minval=True):
        
        if minval:
            if v>0:
                return v*(1.-scale)
            else:
                return v*scale
        else: # maxval
            if v>0:
                return v*scale
            else:
                return v*(1.-scale)
            

    def Plot(self, output_file, elevation=None, azim=None, dpi=None,scale=None):
        plt.ioff()
        tri=self.QuadToTria()
        fig = plt.figure()
        #ax = fig.gca(projection='3d')
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_trisurf(self.nodes[:,0],self.nodes[:,1],self.nodes[:,2], triangles=tri)
        ax.axis('off')
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        # enforce aspect ratio to avoid streching, see Issue https://github.com/pclausen/obj2png/issues/7
        limits = np.array([getattr(ax, f'get_{axis}lim')() for axis in 'xyz']) 
        ax.set_box_aspect(np.ptp(limits, axis = 1))

        nmin,nmax=self.MinMaxNodes()
        if scale is not None:
            ax.set_xlim(ObjFile.ScaleVal(nmin[0],scale),ObjFile.ScaleVal(nmax[0],scale,False))
            ax.set_ylim(ObjFile.ScaleVal(nmin[1],scale),ObjFile.ScaleVal(nmax[1],scale,False))
            ax.set_zlim(ObjFile.ScaleVal(nmin[2],scale),ObjFile.ScaleVal(nmax[2],scale,False))
        if elevation is not None and azim is not None:
            ax.view_init(elevation, azim)
        elif elevation is not None:
            ax.view_init(elevation, 30)
        elif azim is not None:
            ax.view_init(30, azim)
        else:
            ax.view_init(30, 30)
         

        #fig.tight_layout()
        #fig.subplots_adjust(left=-0.2, bottom=-0.2, right=1.2, top=1.2,
        #    wspace=0, hspace=0)
        #ax.autoscale_view(tight=True)
        #ax.autoscale(tight=True)
        #ax.margins(tight=True)
        plt.savefig(output_file,dpi=dpi,transparent=True)
        plt.close()
