# aux functions 
from __future__ import print_function
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.ticker as ticker
from mpl_toolkits import mplot3d
from matplotlib import cm

from pyrateoptics.raytracer.optical_system              import OpticalSystem
from pyrateoptics.raytracer.optical_element             import OpticalElement
from pyrateoptics.raytracer.localcoordinates            import LocalCoordinates
from pyrateoptics.raytracer.surface                     import Surface
from pyrateoptics.raytracer.surface_shape               import Conic
from pyrateoptics.raytracer.aperture                    import CircularAperture
from pyrateoptics.raytracer.material.material_isotropic import\
                                                              ConstantIndexGlass
from pyrateoptics.sampling2d                            import raster
from pyrateoptics.raytracer.ray                         import RayPath
from pyrateoptics.raytracer.ray                         import RayBundle

#---------------------------------------
#Writes data to a file
#---------------------------------------
from pyrateoptics.core.iterators import OptimizableVariableKeyIterator
from pyrateoptics.raytracer.material.material_glasscat import\
     refractiveindex_dot_info_glasscatalog, CatalogMaterial
import matplotlib.pyplot as plt 
import os
import sys

'''
This class is for storing and printing the optimization results
Have a look at the readme file if you want more informations how 
the input/output data can be determined
'''
#---------------------------------------
class inout:
    def __init__(self):
        self.globpath="./Input_Output/"
        fileobj = open(self.globpath+"file_data", "r")
        readdata=[]
        for line in fileobj:
            readdata.append(line.rstrip())
        fileobj.close()
        if(len(readdata[0])==0):
            self.name="result"
        else:
            self.name=readdata[0]
        self.path=readdata[1]
        self.mode=1
        self.filter_status=readdata[2]
        self.iteration=-1
        self.search_result_var={}
        self.search_result_fix={}
        self.shorttolong_var={}
        self.shorttolong_fix={}
        self.longnames_var=[]
        self.longnames_fix=[]
        self.shortnames_var=[]
        self.shortnames_fix=[]
        #Take care if you change the input_surface file. The order below
        #hast to represent the order of the input_surface file
        self.surface_order=["name", "decx", "decxvar", "decy", \
                "decyvar", "decz", "deczvar", "tiltx", "tiltxvar",\
                "tilty", "tiltyvar", "tiltz", "tiltzvar", "maxrad",\
                "maxradvar","minrad", "minradvar", "conic", "conicvar",\
                "curvature", "curvaturevar", "conn1", "conn2", \
                "isstop","shape","aperture"]
        #the name of the stateattribute of the variables. Take care! They
        #have to end like "variablename"var with a var at the end
        self.NamesOptVariable=["decxvar","decyvar","deczvar","tiltxvar",\
                "tiltyvar","tiltzvar","conicvar","curvaturevar"]
        #Take care if you change the bundle_input file. The order below
        #hast to represent the order of the bundle_input file
        self.ray_order=["startx","starty","startz",\
                "radius","anglex","angley","raster"]
        self.surfaces=np.genfromtxt(self.globpath+"surface_input",dtype=None,\
                comments="#")
        self.rays=np.genfromtxt(self.globpath+"bundle_input",dtype=None,\
                comments="#").tolist()
        self.rays_spec=np.genfromtxt(self.globpath+"bundle_spec",dtype=None,\
                comments="#").tolist()
        self.numrays=self.rays_spec[0]
        self.wavelengths=self.convert_2_list(self.rays_spec[1])
        self.material=[]
        self.SurfNameList=[]

    def set_add(self):
        self.mode=0

    def set_first(self):
        delf.mode=1

    def print_data(self):
        print("SAVED DICTIONARY WITH DATA:")
        for (key, item) in self.search_result_item.items():
            print(key + "    " + item)

    def find_char(self, string, character):
        return [i for i, ltr in enumerate(string) if ltr==character]

    def make_shortnames(self):
        for key in self.search_result_var.keys():
            index=self.find_char(key,".")
            short=key[index[-2]+1:]
            self.shorttolong_var[short]=key
            self.shortnames_var.append(short)
    
    #prints the shortnames and the associated real (long) names
    def print_shortnames(self):
        print("SHORTNAMES ARE")
        print("^^^^^^^^^^^^^^^^")
        for (shortn, longn) in self.shorttolong_var.items():
            print(shortn +"      :=      " + longn)
    
    #argv are the shortnames that sould be printed->with this function it is 
    #possible to chosse the variables that should be printed
    #TODO Didnt work yet. All variable variables are plotted at the moment
    def plot_data(self,*argv):
        #fig1=plt.figure()
        plt.figure()
        plt.xlabel("iterations")
        plt.ylabel("values")
        for i in range(0,len(self.search_result_var.items())):
            plt.plot(range(self.iteration+1),\
                    self.search_result_var[self.longnames_var[i]])
        self.make_shortnames()
        plt.legend(self.shortnames_var)
        #fig1.show()
        if(len(self.path)==0):
            plt.savefig(self.name + ".png")
        else:
            plt.savefig(self.path+self.name+".png")
        #plt.show()

    def write_to_file(self):    
        if(self.filter_status=="NONE"):
            print("No output file generated. Specify this if needed in the file_data file")
        else:
            if(len(self.path)==0):
                dir1=self.name+"_fixed"+".csv"
                dir2=self.name+"_variable"+".csv"
            else:
                dir1=self.path+self.name+"_fixed"".csv"
                dir2=self.path+self.name+"_variable"".csv"

            if(self.filter_status=="VARIABLE" or \
                    self.filter_status=="VARIABLEANDFIXED"):
                with open(dir2, 'w') as f:
                    for key in self.search_result_var.keys():
                        f.write("%s,%s\n"%(key,self.search_result_var[key]))
                f.close()    
            if(self.filter_status=="FIXED" or \
                    self.filter_status=="VARIABLEANDFIXED"): 
                with open(dir1, 'w') as f:
                    for key in self.search_result_fix.keys():
                        f.write("%s,%s\n"%(key,self.search_result_fix[key]))
                f.close()
            #if you added residuum or merritfunction value etc. here it hast to be written to the code

    def store_data(self,os):
        lst = OptimizableVariableKeyIterator(os).variables_dictionary
        for (key,obj) in lst.items():
            if(self.filter_status=="VARIABLE" or \
                    self.filter_status=="VARIABLEANDFIXED"):
                if(obj.var_type()=="variable"):
                    if(self.mode==1):
                        self.longnames_var.append(key)
                        self.search_result_var[str(key)]=[obj.evaluate()]
                    else:
                        self.search_result_var[str(key)].append(obj.evaluate())
            if((self.filter_status=="FIXED" \
                    or self.filter_status=="VARIABLEANDFIXED") and self.mode==1):
                if(obj.var_type()=="fixed"):
                    if(self.mode==1):
                        self.longnames_fix.append(key)
                        self.search_result_fix[str(key)]=[obj.evaluate()]
                    else:
                        self.search_result_fix[str(key)].append(obj.evaluate())
        if(self.mode==1):
            self.set_add()
        
        self.iteration+=1
        #print(self.search_result_fix)
        #print(self.search_result_var)

        #if the residuum or merritfunction value is needed it can be added here in the code 
    
    def get_sufval(self, name, index):
        return self.surfaces[index][self.surface_order.index(name)]

    def get_rayval(self, name, index):
        return self.rays[index][self.ray_order.index(name)]

    def get_rayval_tupel(self, name):
        return self.rays[self.ray_order.index(name)]

    #this function creates for every surface (defined in the surface_input file) one coordinate system, and returns a list of them
    def create_coordinate_systems(self,optical_system):
        coordinate_systems=[]
        for i in range(self.surfaces.shape[0]):
            if(i==0):
                refname_=optical_system.rootcoordinatesystem.name
            else:
                refname_=coordinate_systems[i-1].name
            coordinate_systems.append(optical_system.\
                    addLocalCoordinateSystem(LocalCoordinates.p(\
                    name=self.get_sufval("name",i),\
                    decx=self.get_sufval("decx",i), decy=self.get_sufval("decy",i), \
                    decz=self.get_sufval("decz",i), tiltx=self.get_sufval("tiltx",i),\
                    tilty=self.get_sufval("tilty",i), tiltz=self.get_sufval("tiltz",i)),\
                    refname=refname_))

        return coordinate_systems

    #this function creates the sufaces defined in surface_input file and returns a list of these surfaces 
    def create_surfaces(self, cs):  #cs=coordinate Systems
        surface_objects=[]
        for i in range(self.surfaces.shape[0]):
            if(self.get_sufval("shape",i)=="Conic"):
                #hier noch cc einfuegen
                shape_=Conic.p(cs[i],cc=float(self.get_sufval("conic",i)),curv=float(self.get_sufval("curvature",i)))
                #print(self.get_sufval("curvature",i))
            else:
                shape_=None
            if(self.get_sufval("aperture",i)=="Circular"):
                aperture_=CircularAperture(cs[i],minradius=float(self.get_sufval("minrad",i)), maxradius=float(self.get_sufval("maxrad",i)))
                #print(float(self.get_sufval("maxrad",i)).__class__.__name__)
            else:
                aperture_=None

            self.SurfNameList.append(self.get_sufval("name",i))
            surface_objects.append(Surface.p(cs[i], shape=shape_, aperture=aperture_))

        return surface_objects

    #reads material from the input_surface file and creates the needed object
    #take care! A database of all materials is necessary. 
    #Store the database in refractiveindex.info-database. Different databases
    #can be downloaded from github e.g.
    #https://github.com/polyanskiy/refractiveindex.info-database
    def create_material(self, cs, elem1, surf):
        if os.path.isdir("../pyrateoptics/refractiveindex.info-database/database/"):
            for i in range(self.surfaces.shape[0]):
                tempmat1=self.get_sufval("conn1",i)
                tempmat2=self.get_sufval("conn2",i)
                if(self.material.count(tempmat1)==0 and tempmat1 != "None"):
                    self.material.append(tempmat1)
                if(self.material.count(tempmat2)==0 and tempmat2 != "None"):
                    self.material.append(tempmat2)
            
            gcat = refractiveindex_dot_info_glasscatalog("../pyrateoptics/refractiveindex.info-database/database/")
            for i in range(len(self.material)):
                #absolutely no idea why there is a coordinate system necessary for creating a material. random choice: use always cs[0].
                #result is always the same, no matter which coordinate system is used
                tempmat=gcat.createGlassObjectFromLongName(cs[0],self.material[i])
                elem1.addMaterial(self.material[i],tempmat)
             
            for i in range(self.surfaces.shape[0]):
                elem1.addSurface(self.get_sufval("name",i),surf[i], \
                        (self.get_sufval("conn1",i),self.get_sufval("conn2",i)))
        else:
            print("It looks like there is no database at refractiveindex.info-database")
            print("Please download a database e.g. from https://github.com/polyanskiy/refractiveindex.info-database")

    #"value1&value2&value3" -> [value1,value2,value3] all values get a float 
    #cast. If the cast is not possible the input string is returned 
    def convert_2_list(self,string):
        try:
            liste=list(string.split("&"))                                                    
            newlist=[]
            for i in range(len(liste)):
                newlist.append(float(liste[i]))
            return newlist
        except:
            return string

    #creates optimizable variables with fixed or variable state
    #if in the surface_input file are intervals defined, the variables
    #get modified in the determined way
    def setup_variables(self, os, elemName):
        optiVarsDict = {}                                                                
        for i in range(len(self.SurfNameList)):
            temptdict={}
            for item in self.NamesOptVariable:
                if self.get_sufval(item,i)!="f":
                    temptdict[item[:-3]]=self.convert_2_list(self.get_sufval(item,i))
            
            if(len(temptdict)!=0): optiVarsDict[self.get_sufval("name",i)]=temptdict


        for surfnames in optiVarsDict.keys():
            for params in self.NamesOptVariable[:-2]:
                if params[:-3] in optiVarsDict[surfnames]:
                    decOrTilt = getattr(os.elements[elemName].surfaces[surfnames].\
                            rootcoordinatesystem, params[:-3])
                    decOrTilt.toVariable()
                    decOrTilt.setInterval(left=optiVarsDict[surfnames][params[:-3]][0],
                            right=optiVarsDict[surfnames][params[:-3]][1])

            for params in self.NamesOptVariable[-2:]:
                if params[:-3] in optiVarsDict[surfnames]:
                    curvOrCc = getattr(os.elements[elemName].\
                            surfaces[surfnames].shape, params[:-3])
                    curvOrCc.toVariable()
                    curvOrCc.setInterval(left=optiVarsDict[surfnames]\
                            [params[:-3]][0], \
                            right=optiVarsDict[surfnames][params[:-3]][1])

    #returns a sequence of surfaces which are defined in the surface_input file 
    def get_sysseq(self, elem1):
        templist=[]
        for i in range(len(self.SurfNameList)):
            if self.get_sufval("isstop",i):
                templist.append((self.get_sufval("name",i), {"is_stop":True}))
            else:
                templist.append((self.get_sufval("name",i), {}))
            
        sysseq=[(elem1.name,templist)]
        return sysseq 

    #returns the dictionary which represents the ray bundles 
    #def get_rays_dict(self):
    #    rays_dict={}
    #    for i in range(len(self.ray_order)):
    #        value=self.get_rayval(self.ray_order[i])
    #        name=self.ray_order[i]
    #        if isinstance(value,int):
    #            rays_dict[name]=[value]
    #        elif name=="raster":
    #            if(value=="RectGrid"):
    #                rays_dict[name]=raster.RectGrid()
    #        else:    
    #            rays_dict[self.ray_order[i]]=self.convert_2_list(value)
    #    return rays_dict 
    
    #returns a list with all bundle dictionarys which represents the ray bundles 
    def get_rays_dict(self):
        rays_list=[]
        if(type(self.rays)==list):
            for line in range(len(self.rays)):
                dummy_dict={}
                for i in range(len(self.ray_order)):
                    value=self.get_rayval(self.ray_order[i], line)
                    name=self.ray_order[i]
                    if not isinstance(value,str):
                        dummy_dict[name]=value
                    elif name=="raster":
                        if(value=="RectGrid"):
                            dummy_dict[name]=raster.RectGrid()
                rays_list.append(dummy_dict)
        else:
            for i in range(len(self.ray_order)):
                value=self.get_rayval_tupel(self.ray_order[i])
                name=self.ray_order[i]
                if not isinstance(value,str):
                    dummy_dict[name]=value
                elif name=="raster":
                    if(value=="RectGrid"):
                        dummy_dict[name]=raster.RectGrid()
            rays_list.append(dummy_dict)

        return rays_list 

def str_to_class(classname):
    return getattr(sys.modules[__name__], classname)


def error2squared(x, x_ref, y, y_ref):
    '''
    computes the squared
    '''
    res = np.sum((x - x_ref)**2 + (y - y_ref)**2) 

    return res


def error1(x, x_ref, y, y_ref, penalty=False):
    '''
    computes the 
    L1-error = sum_{i=1 to #rays}(||(x_i, y_i)^T - (x_ref, y_ref)^T||_1)
    '''
    res = np.sum(np.absolute(x - x_ref) + np.absolute(y - y_ref))

    return res


def setOptimizableVariables(os, elemName, optiVarsDict, SurfNamesList):
    '''
    os: OpticalSystem object
    optiVarsDict: dictionary for all parameters
    SurfNamesList: dictionary with all surface names
    elemName: name of the optical element

    transforms all the parameters in optiVarsList into the variable state
    '''

    allParamsList = ["decz", "decx", "decy", "tiltx", "tilty", "tiltz",
                     "curvature", "cc"]

    for surfnames in optiVarsDict.keys():
        for params in allParamsList[:-2]:
            if params in optiVarsDict[surfnames]:
                decOrTilt = getattr(os.elements[elemName].surfaces[surfnames].\
                                    rootcoordinatesystem, params)
                decOrTilt.toVariable()
                decOrTilt.setInterval(left=optiVarsDict[surfnames][params][0],
                                      right=optiVarsDict[surfnames][params][1])

        for params in allParamsList[-2:]:
            if params in optiVarsDict[surfnames]:
                curvOrCc = getattr(os.elements[elemName].surfaces[surfnames].\
                                   shape, params)
                curvOrCc.toVariable()
                curvOrCc.setInterval(left=optiVarsDict[surfnames][params][0],
                                     right=optiVarsDict[surfnames][params][1])


def calcBundleProps(osa, bundleDict, numrays_plot=100):
    '''
    osa: OpticalSystemAnalysis-object
    bundleDict: all bundle data in a dictionary
    numrays_plot: number of rays for plotting
    
    return are the two dictionaries with all o1,k1,E0 matrizes
    '''
    bundlePropDict      = {}
    bundlePropDict_plot = {}

    for i in bundleDict.keys():
        bundlePropDict[i] = getattr(osa, bundleDict[i][3])(bundleDict[i][0],
                                                           bundleDict[i][1],
                                                           bundleDict[i][2])

    for i in bundleDict.keys():
        bundlePropDict_plot[i] = getattr(osa, bundleDict[i][3])(numrays_plot,
                                                                bundleDict[i][1],
                                                                bundleDict[i][2])
    return bundlePropDict, bundlePropDict_plot


def calculateRayPaths(os, bundleDict, bundlePropDict, sysseq):
    '''
    os: OpticalSystem
    bundleDict: all bundle data in a dictionary
    bundlePropDict: dictionary which contains all the bundle properties(o1,k1,E1)
                    from above
    sysseq: system sequence

    return are the x,y vectors which contain the (x,y)-coordinates from the 
    raytracer 
    '''
    x = np.array([])
    y = np.array([])

    for i in bundlePropDict.keys():
        bundle = RayBundle(x0      = bundlePropDict[i][0], 
                           k0      = bundlePropDict[i][1],
                           Efield0 = bundlePropDict[i][2],
                           wave    = bundleDict[i][2])
        rpaths = os.seqtrace(bundle, sysseq)
        x = np.append(x, rpaths[0].raybundles[-1].x[-1, 0, :])
        y = np.append(y, rpaths[0].raybundles[-1].x[-1, 1, :])
    
    return x, y

def plotBundles(s, initialbundle, sysseq, 
                ax, pn, up2, color="blue"):
    '''
    EDITED BY LEANDRO 29.11.2019
    os: OpticalSystem-object optimization
    bundleDict: all bundle data in a dictionary
    bundlePropDict_plot: dictionary which contains all the bundle properties
                         (o1,k1,E1) for plotting
    sysseq: system sequence
    color: the color for the rays

    draws all rays in the bundleDict and the optical system os
    '''

    # Get dimensions and initialise r2
    m = len(initialbundle)
    n = len(initialbundle[0])
    r2 = [0 for x in range(m*n)]

    # Calculate rays
    counter = 0
    for i in range(0,m):
        for j in range(0,n):
            r2 = s.seqtrace(initialbundle[i][j], sysseq)
            for r in r2:
                r.draw2d(ax, color="green", plane_normal=pn, up=up2)

    s.draw2d(ax, color="grey", vertices=50, plane_normal=pn, up=up2) 

def plotSpotDia(osa, numrays, rays_dict, wavelength):

    #Set defaults for dictionary
    rays_dict.setdefault("startx", [0])
    rays_dict.setdefault("starty", [0])
    rays_dict.setdefault("startz", [-7])
    rays_dict.setdefault("angley", [0])
    rays_dict.setdefault("anglex", [0])
    rays_dict.setdefault("rasterobj", raster.RectGrid())
    rays_dict.setdefault("radius", [15])

    #Iterate over all entries
    for i in rays_dict["startx"] :
        for j in rays_dict["starty"] :
            for k in rays_dict["startz"] :
                for l in rays_dict["angley"] :
                    for m in rays_dict["anglex"] :
                        for n in rays_dict["radius"] :
                            #Setup dict for current Bundle
                            bundle_dict = {"startx":i, "starty":j, "startz":k,
                                           "angley":l, "anglex":m, "radius":n,
                                           "rasterobj":rays_dict["rasterobj"]}
                            for o in wavelength :
                                osa.aim(numrays, bundle_dict, wave=o)
                                osa.drawSpotDiagram()


def get_bdry(optimi) :
    '''
    Returns an array that has the boundaries of the optimizable
    variable in it, meaning:
    [lowerbound_x1 upperbound_x1 ... lowerbound_xn upperbound_xn]
    '''
    
    n = len(optimi.collector.variables_list)
    bdry = np.zeros(2*n)
    cnt = 0
    for i in optimi.collector.variables_list :
        bdry[cnt] = i.interval_trafo_fo._FunctionObject__global_variables['left']
        cnt = cnt + 1
        bdry[cnt] = i.interval_trafo_fo._FunctionObject__global_variables['right']
        cnt = cnt + 1

    return bdry


def eval_h(x, bdry) :
    '''
    returns vector with the values of h(x) according to
    Nocedal p. 494, meaning evaluating the min(0,h(x_i))
    respectively max(0,h(x_i)) (depending whether it is
    upper/lower boundary
    '''

    x = np.asfarray(x).flatten()
    h_x = np.zeros(len(bdry))
    cnt = 0
    for xi in x :
        h_x[cnt] = np.maximum(0, bdry[cnt]-xi)  #lower bound
        cnt = cnt + 1
        h_x[cnt] = np.maximum(0, xi-bdry[cnt])  #upper bound
        cnt = cnt + 1

    return h_x


def eval_c(x, bdry) :
    '''
    returns vector with the values of c(x), with c(x) being the function
    c(x) >= 0
    '''

    x = np.asfarray(x).flatten()
    c_x = np.zeros(len(bdry))
    cnt = 0
    for xi in x :
        c_x[cnt] = xi - bdry[cnt] #lower bound
        cnt = cnt + 1
        c_x[cnt] = bdry[cnt] - xi  #upper bound
        cnt = cnt + 1

    return c_x


def my_log(x) :
    '''
    Returns log(x) if x>0, and -999999999999999 if x<=0
    '''

    res = np.zeros(len(x))
    cnt = 0
    for xi in x :
        if xi>0:
            res[cnt] = np.log(xi)
            cnt = cnt + 1
        else:
            res[cnt] = -9999999999999999
            cnt = cnt + 1

    return res

def printArray(name, x, typ='float', point=5):                                   
    '''
    point is the number of digits after the point
    '''
    x = np.asarray(x)

    if (typ == 'float'):
        style = '{:0.'+str(point)+'f}'
        np.set_printoptions(formatter={typ: style.format})
    elif (typ == 'int'):
        x = np.array(x, dtype=int)
        np.set_printoptions(formatter={typ: '{:d}'.format})
    elif (typ == 'bool'):
        np.set_printoptions(formatter={typ: '{:b}'.format})
    else:
        style = '{:0.3f}'
        np.set_printoptions(formatter={typ: style.format})
    print('\n', end='')
    print(name, end=' ')
    print(x, end='')
    print('\n')


def termcondition(fk, fk_1, xk, xk_1, gk, thetaf=1e-3, p=None):
    '''
    Termination condition for smooth problems out of 
    Gill, Murray and Wright: Practical Optimization, S.305ff
    fk      : function value at xk
    fk_1    : function value at xk_1
    xk      : k-th x value of the sequence
    xk_1    : k-1-th x value of the sequence
    gk      : the gradient at xk
    thetaf  : tolerance
    p       : for the p-norm
    '''
    
    ismin = False
    phi     = thetaf*(1+np.absolute(fk))
    epsilon = math.pow(thetaf, 1/2)*(1+np.linalg.norm(xk, p))
    delta   = math.pow(thetaf, 1/3)*(1+np.absolute(fk))

    # In the literature it is not the absolute value of fk_1-fk, but for 
    # algorithm which does not go to a descent direction in every step the 
    # absolute value is necessary
    if ((np.absolute(fk_1-fk) < phi) and\
        (np.linalg.norm(xk_1-xk, p) < epsilon) and\
        (np.linalg.norm(gk, p) <= delta)):

        ismin = True

    return ismin


def plot2d(xarray, yarray,
           fignum=1,
           title='',
           fonttitle=14,
           xlabel='',
           ylabel='',
           fontaxis=12,
           legend='',
           fontlegend=12,
           loclegend='best',
           xlim='auto',
           ylim='auto',
           xlog=False,
           ylog=False,
           xticks='auto',
           yticks='auto',
           axformat='sci',
           grid=True,
           linewidth=2,
           linestyle='-',
           color='red',
           marker='o',
           markersize=2,
           save=False,
           name='plot2d.png',
           show=False,
           *args):

    fig = plt.figure(fignum)
    ax = fig.add_subplot(1, 1, 1)
    # set plot
    ax.plot(xarray, yarray, linewidth=linewidth, linestyle=linestyle, 
            marker=marker, markersize=markersize, label=legend)
    ax.legend(loc=loclegend)
    # axis
    ax.set_xlabel(xlabel, fontsize=fontaxis)
    ax.set_ylabel(ylabel, fontsize=fontaxis)
    if type(xticks) is np.ndarray:
        ax.set_xticks(xticks)
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    if type(yticks) is np.ndarray:
        ax.set_yticks(yticks)
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.xaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    ax.ticklabel_format(axis='both', style=axformat)
    # log scale
    if (xlog==True):
        ax.set_xscale('log')
    if (ylog==True):
        ax.set_yscale('log')
    # set xlim and ylim
    if type(xlim) is np.ndarray:
        ax.set_xlim(xlim[0],xlim[1])
    if type(ylim) is np.ndarray:
        ax.set_ylim(ylim[0],ylim[1])
    # title
    # remark: matplotlib accepts Tex $ $-expressions,
    #         like plt.title(r'$\sigma_{i}=15$'), where the r indicates that the
    #         backslash is not to treat like in python, but in latex
    ax.set_title(title, fontsize=fonttitle)
    # set grid
    ax.grid(grid)
    # safe 
    if (save==True):
        plt.savefig(name)
    # plot
    if (show==True):
        plt.show()


def plot3d(X, Y, Z,
           fignum=1,
           title='',
           fonttitle=14,
           xlabel='',
           ylabel='',
           zlabel='',
           fontaxis=12,
           xlim='auto',
           ylim='auto',
           zlim='auto',
           xlog=False,
           ylog=False,
           zlog=False,
           grid=True,
           save=False,
           name='plot3d.png',
           show=False,
           *args):

    fig = plt.figure(fignum)
    ax = plt.axes(projection='3d')
    # set plot
    ax.plot_surface(X, Y, Z, cmap=cm.coolwarm)
    # axis
    ax.set_xlabel(xlabel, fontsize=fontaxis)
    ax.set_ylabel(ylabel, fontsize=fontaxis)
    ax.set_zlabel(zlabel, fontsize=fontaxis)
    # log scale
    if (xlog==True):
        ax.set_xscale('log')
    if (ylog==True):
        ax.set_yscale('log')
    if (zlog==True):
        ax.set_zscale('log')
    # set xlim and ylim
    if not (xlim=='auto'):
        ax.set_xlim(xlim[0],xlim[1])
    if not (ylim=='auto'):
        ax.set_ylim(ylim[0],ylim[1])
    if not (zlim=='auto'):
        ax.set_zlim(zlim[0],zlim[1])
    # title
    # remark: matplotlib accepts Tex $ $-expressions,
    #         like plt.title(r'$\sigma_{i}=15$'), where the r indicates that the
    #         backslash is not to treat like in python, but in latex
    ax.set_title(title, fontsize=fonttitle)
    # set grid
    ax.grid(grid)
    # safe 
    if (save==True):
        plt.savefig(name)
    # plot
    if (show==True):
        plt.show()

def line_search_bound(func,beta0,x,d,bounds):
    beta = beta0
    f_alt = func(x)
    x_neu = x + beta*d
    while not (np.all(x_neu>=bounds.lb) and np.all(x_neu<=bounds.ub)):
        beta = beta * 0.5
        if beta < 1e-9:
            print("beta zu klein")
            return (x_neu,beta)
        x_neu = x + beta*d
    while not (func(x_neu) < f_alt):
        beta = beta * 0.5
        if beta < 1e-9:
            print("beta zu klein 2")
            return (x_neu,beta)
        x_neu = x + beta*d
    
    return (x_neu,beta)


def resettingAlgo(func, gradf, x_k, p_k, alpha, 
                  roh=0.9, c=1e-2, maxiter=50, **kwargs):
    '''
    This algorithm reduces the initial stepsize alpha until Armijos condition
    is satisfied. It is also known as backtracking algorithm.
    func   : C1 function
    gradf  : derivative of func
    x_k    : current position
    p_k    : descent direction
    alpha  : (possibly large) initial stepsize 
    roh    : reduction factor \in (0,1)
    c      : parameter \in (0,1) to reduce the slope at x_k in direction p_k
    maxiter: maximum number of iterations
    '''
    alpha_k = alpha
    iternum = 1
    while (func(x_k+alpha_k*p_k) > func(x_k) + c*alpha_k*np.dot(gradf(x_k),p_k)):
        alpha_k *= roh
        # debugging
        print(iternum)
        if (iternum > maxiter):
            print('\nmaxiter is reached, resettingAlgo has failed\n')
            break
        iternum += 1

    return alpha_k


def armijo(func, gradf, x_k, p_k, 
           alpha, 
           delta_min=1e-3, delta_max=1e-1, 
           c=1e-1, 
           maxiter=20, 
           **kwargs):
    '''
    This algorithm reduces the initial stepsize alpha until Armijos condition
    is satisfied. It is also known as backtracking algorithm.
    func     : C1 function
    gradf    : derivative of func
    x_k      : current position
    p_k      : descent direction
    alpha    : (possibly large) initial stepsize 
    delta_min: parameter for stepsize difference
    delta_max: parameter for stepsize difference
    c        : parameter \in (0,1) to reduce the slope at x_k in direction p_k
    maxiter  : maximum number of iterations for cubic interpolation
    '''
    phi_0     = func(x_k)
    phi_a0    = func(x_k + alpha*p_k)
    gradphi_0 = np.dot(gradf(x_k),p_k)

    if (phi_a0 <= phi_0 + c*alpha*gradphi_0): # check armijo
        return alpha
    else: # quadratic interpolation
        alpha_1 = -(phi_0*alpha*alpha)/(2*(phi_a0-phi_0-gradphi_0*alpha))
        phi_a1  = func(x_k+alpha_1*p_k)

    if ((alpha - alpha_1 < delta_min) or \
        (alpha - alpha_1 > delta_max)): # check stepsize difference

        alpha_1 = alpha/2 

    if (phi_a1 <= phi_0 + c*alpha_1*gradphi_0): # check armijo
        return alpha_1
    else: # cubic interpolation
        alphaj   = alpha_1
        alphaj_1 = alpha
        phij     = func(x_k + alphaj  *p_k)
        phij_1   = func(x_k + alphaj_1*p_k)
        iternum  = 1
        while (1):
            gammaj   = 1/(((alphaj_1*alphaj)**2)*(alphaj-alphaj_1))
            aj       = gammaj*(+(alphaj_1**2)*(phij  -phi_0-gradphi_0*alphaj  )\
                               -(alphaj  **2)*(phij_1-phi_0-gradphi_0*alphaj_1))
            bj       = gammaj*(-(alphaj_1**3)*(phij  -phi_0-gradphi_0*alphaj  )\
                               +(alphaj  **3)*(phij_1-phi_0-gradphi_0*alphaj_1))
            alphaj_1 = alphaj
            alphaj   = (-bj+math.sqrt((bj**2)-3*aj*gradphi_0))/(3*aj)
            phij     = func(x_k + alphaj*p_k)
            
            if ((alphaj_1 - alphaj < delta_min) or \
                (alphaj_1 - alphaj > delta_max)): # check stepsize difference

                alphaj = alphaj_1/2
            
            if (phij <= phi_0 + c*alphaj*gradphi_0): # check armijo
                return alphaj
            
            print(iternum)
            if (iternum > maxiter):
                print('\nmaxiter is reached, cubic interpolation has failed\n')
                break

            iternum += 1
            

def interpol_hermite(alpha1, alpha2,
                     phi1, phi2,
                     gradphi1, gradphi2):
    '''
    This function interpolates a function phi with a cubic interpolation poly.
    using derivatives (Hermite interpolation).
    alpha1  : first point
    alpha2  : second point
    phi1    : phi(alpha1)
    phi2    : phi(alpha2)
    gradphi1: grad(phi)(alpha1)
    gradphi2: grad(phi)(alpha2)
    '''
    d1 = gradphi1+gradphi2-3*(phi1-phi2)/(alpha1-alpha2)
    d2 = math.copysign(1, alpha2-alpha1)*np.sqrt(d1*d1-gradphi1*gradphi2)
    alpha = alpha2-(alpha2-alpha1)*(gradphi2+d2-d1)/(gradphi2-gradphi1+2*d2)
    return alpha



def interpolation(func, gradf, x_k, p_k,
                  alpha1, alpha2, 
                  c1, c2,
                  **kwargs):
    '''
    Function for the interpolation step in strong wolfe algorithm below.
    func   : C1 function
    gradf  : derivative of func
    x_k    : current position
    p_k    : descent direction
    alpha1 : first stepsize 
    alpha2 : second stepsize 
    c1     : parameter \in (0,1) to reduce the slope at x_k in direction p_k
    c2     : parameter \in (c1,1) for the curvature condition
    maxiter: maximum number of iterations for cubic interpolation
    '''
    phi0     = func(x_k)
    phi1     = func(x_k+alpha1*p_k)
    phi2     = func(x_k+alpha2*p_k)
    gradphi0 = np.dot(gradf(x_k),p_k)
    gradphi1 = np.dot(gradf(x_k+alpha1*p_k),p_k)
    gradphi2 = np.dot(gradf(x_k+alpha2*p_k),p_k)

    while(1):
        # interpolation or ...
        alphai = interpol_hermite(alpha1, alpha2, phi1, phi2, gradphi1, gradphi2) 
        # ... bisection
        # alphai = (alpha1+alpha2)/2
        phi_ai = func(x_k+alphai*p_k)
        # check armijo and whether the function value at alphai is \ge the one 
        # at alpha_1 (which is alpha_low)
        if ((phi_ai > phi0+c1*alphai*gradphi0) or (phi_ai >= phi1)):
            alpha2 = alphai
        else:
            gradphi_ai = np.dot(gradf(x_k+alphai*p_k),p_k)
            # check strong curvature
            if (np.absolute(gradphi_ai) <= -c2*gradphi0):
                return alphai
            # check property of alpha1 and alpha2 
            if (gradphi_ai*(alpha2-alpha1) >= 0):
                alpha2 = alpha1

            alpha1 = alphai


def strongwolfe(func, gradf, x_k, p_k, 
                alpha1, alpha_max, 
                c1, c2, 
                maxiter, 
                **kwargs):
    '''
    This algorithm searches for a step size which fulfills the strong wolfe 
    condtion.
    func      : C1 function
    gradf     : derivative of func
    x_k       : current position
    p_k       : descent direction
    alpha1    : initial stepsize 
    alpha_max : maximal stepsize 
    c1        : parameter \in (0,1) to reduce the slope at x_k in direction p_k
    c2        : parameter \in (c1,1) for the curvature condition
    maxiter   : maximum number of iterations for cubic interpolation
    '''

    alpha0   = 0
    alphaj_1 = alpha0
    alphaj   = alpha1
    phi0     = func(x_k)
    phij_1   = phi0
    gradphi0 = np.dot(gradf(x_k),p_k)
    j        = 1
    while (1):
        phij = func(x_k+alphaj*p_k)

        # check armijo and whether the next function value is greater
        if ((phij > phi0+c1*alphaj*gradphi0) or ((j > 1) and (phij >= phij_1))):
            alpha = interpolation(func, gradf, x_k, p_k, alphaj_1, alphaj, c1, c2)
            return alpha
        
        gradphij = np.dot(gradf(x_k+alphaj*p_k), p_k)

        # check strong curvature (the slope has to decrease)
        if (np.absolute(gradphij) <= -c2*gradphi0):
            return alphaj
        # check whether the next slope is greater or equal zero
        if (gradphij >= 0):
            alpha = interpolation(func, gradf, x_k, p_k, alphaj, alphaj_1, c1, c2)
            return alpha

        # choose the next step size
        alphaj_1 = alphaj
        alphaj   = 2*alphaj_1
        phij_1   = phij

        print(j)
        if (j > maxiter):
            print('\nmaxiter is reached, strong wolfe algorithm has failed\n')
            break
        j += 1



