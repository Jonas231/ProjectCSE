# template to create a optical system which is optimized
# including the necessary classes, functions and libraries
# by lewin

# --- general
import logging
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# --- copy function for copying the initialbundle
from copy import deepcopy

# --- optical system and raytracing
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
from pyrateoptics.raytracer.globalconstants             import canonical_ey 
from pyrateoptics.raytracer.globalconstants             import degree 

# --- optical system analysis
from pyrateoptics.raytracer.analysis.optical_system_analysis import\
                                                        OpticalSystemAnalysis
from pyrateoptics.raytracer.analysis.surface_shape_analysis  import\
                                                        ShapeAnalysis
# --- optimization
from pyrateoptics.optimize.optimize          import Optimizer
from pyrateoptics.optimize.optimize_backends import (ScipyBackend,
                                                     Newton1DBackend,
                                                     ParticleSwarmBackend,
                                                     SimulatedAnnealingBackend)
# --- debugging 
from pyrateoptics import listOptimizableVariables

#logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig()

# --- auxiliary functions
from auxiliary_functions import calculateRayPaths,\
                                error2squared,\
                                error1,\
                                setOptimizableVariables,\
                                calcBundleProps,\
                                plotBundles,\
                                inout 
#meritfunction and initialbundle
from aux_merit_bundle import buildInitialbundle, get_bundle_merit

#######################################NeuAnfang##################################
#create inout object for all io stuff
fi1=inout()

#create optical system
s = OpticalSystem.p()

#create for each surface a coordinate system which includes loading the surfaces
cs=fi1.create_coordinate_systems(s)

#create optical element
elem1 = OpticalElement.p(cs[0], name="elem1")

#create surface objects
surf=fi1.create_surfaces(cs)

#create material
fi1.create_material(cs, elem1, surf)
#######################################Neuende##################################

# ----------- assemble optical system
s.addElement(elem1.name, elem1)


# II---------------------- optical system analysis
# --- 1. elem

sysseq=fi1.get_sysseq(elem1);

# ----------- define optical system analysis object
osa = OpticalSystemAnalysis(s, sysseq)




# III ----------- defining raybundles for optimization and plotting 
bundleDict = {} 
'''
possible rays_dict keywords:
 -startx 
 -starty 
 -startz
 -rasterobj 
 -radius 
 -angley
 -anglex

default is 0.0

'''

# ----- define raybundles
# every parameter needs to be an array/list! e.g. [7] instead of 7
rays_dict = {"startz":[-7], "starty": [0], "radius": [5],
	         "anglex": [0.03, -0.05], "raster":raster.RectGrid()}
#rastertype = raster.RectGrid()
#define wavelengths
wavelength = [0.5875618e-3]#, 0.4861327e-3]#, 0.6562725e-3]
numrays = 10
wavelength = [0.5875618e-3, 0.4861327e-3]#, 0.6562725e-3]
numrays = 50

(initialbundle, meritfunctionrms) = get_bundle_merit(osa, s, sysseq, rays_dict,
                                    numrays, wavelength)


'''
# ----- 1. raybundle
numrays1    = 200
rays_dict1  = {"startz": -7,
               "anglex": 0.052, 
               "radius": 16., 
               "raster": raster.RectGrid()}
wavelength1 = 0.587e-3 # [mm]
bundletype1 = "collimated_bundle"

# do not forget the bundleDict entry, otherwise the bundle is not captured
# the order does matter
bundleDict[0] = (numrays1, rays_dict1, wavelength1, bundletype1)

# ----- 2. raybundle

numrays2    = 200
rays_dict2  = {"startz": -7,
               "radius": 16., 
               "raster": raster.RectGrid()}
wavelength2 = 0.587e-3 # [mm]
bundletype2 = "collimated_bundle"

bundleDict[1] = (numrays2, rays_dict2, wavelength2, bundletype2)

# ----- 3. raybundle
# and so on


# ----- automatically calculate bundle properties for meritfunction/plot
bundlePropDict, bundlePropDict_plot = calcBundleProps(osa, bundleDict, 
                                                      numrays_plot=100)
'''
# ----- plot the original system
# --- set the plot setting
pn = np.array([1, 0, 0])
up = np.array([0, 1, 0])

fig = plt.figure(1)
ax1 = fig.add_subplot(211)
ax2 = fig.add_subplot(212)
ax1.axis('equal')
ax2.axis('equal')

# --- plot the bundles and draw the original system
# first it is necessary to copy the initialbundle, as it's gonna be changed
# inside of the seqtrace function (called inside of plotBundles)
testbundle = deepcopy(initialbundle)
plotBundles(s, initialbundle, sysseq, ax1, pn, up)


# IV ----------- optimization
# ----- define optimizable variables
#######################################NeuAnfang##################################
fi1.setup_variables(s,elem1.name)
#######################################NeuEnde##################################

# --- print table of optimizable variables
# this is actually quite nice to get a look at the vars, especially at the end
print("listedervariablen")
listOptimizableVariables(s, filter_status='variable', max_line_width=1000)

# --- define update function
def osupdate(my_s):
#   Update all coordinate systems during run
    my_s.rootcoordinatesystem.update()

# --- define meritfunction
#def meritfunctionrms(my_s):
#    x, y = calculateRayPaths(my_s, bundleDict, bundlePropDict, sysseq)
#    xmean = np.mean(x)
#    ymean = np.mean(y)

    # choose the error function defined in auxiliary_functions
#    res = error2squared(x, xmean, y, ymean, penalty=True)
    #res = error1(x, xmean, y, ymean, penalty=True)

#    return res


# ----- choose the backend
opt_backend = ScipyBackend(method='Nelder-Mead',                                 
                           options={'maxiter': 1000, 'disp': True}, tol=1e-8)

# ----- create optimizer object
optimi = Optimizer(s,
                   meritfunctionrms,
                   backend=opt_backend,
                   updatefunction=osupdate)


#########################so kann man werte speichern###################
fi1.store_data(s)   #bei jedem aufruf werden die variablen gespeichert
fi1.store_data(s)
fi1.store_data(s)
fi1.write_to_file() #am ende einmal in ne datei schreiben
################################################

## ----- debugging
##optimi.logger.setLevel(logging.DEBUG)
#
## ----- start optimizing
s = optimi.run()
#
#
#
## V----------- plot the optimized system
#
## --- plot the bundles and draw the system
#TODO wenn fogende zeiel auskommentiert wird dauert das plotten ewig, obwhl die 
#funktion bereits vorher aufgerufen wurde und (relativ) schnell geht????????
#plotBundles(s, testbundle, sysseq, ax2, pn, up)
##
# --- draw spot diagrams

#numrays_spot = 200
#for i in bundleDict:
#    osa.aim(numrays_spot, bundleDict[i][1], wave=bundleDict[i][2])
#    osa.drawSpotDiagram()


# get a look at the vars
ls=listOptimizableVariables(s, filter_status='variable', max_line_width=1000)

plt.show()
