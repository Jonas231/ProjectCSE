# --- general
import logging
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import random

# --- optical system and raytracing
from pyrateoptics.raytracer.optical_system              import OpticalSystem
from pyrateoptics.raytracer.optical_element             import OpticalElement
from pyrateoptics.raytracer.localcoordinates            import LocalCoordinates
from pyrateoptics.raytracer.surface                     import Surface
from pyrateoptics.raytracer.surface_shape               import Conic
from pyrateoptics.raytracer.aperture                    import CircularAperture
from pyrateoptics.raytracer.material.material_isotropic import ConstantIndexGlass
from pyrateoptics.sampling2d                            import raster
from pyrateoptics.raytracer.ray                         import RayPath
from pyrateoptics.raytracer.ray                         import RayBundle
from pyrateoptics.raytracer.globalconstants             import canonical_ey 
from pyrateoptics.raytracer.globalconstants             import degree 

# --- optical system analysis
from pyrateoptics.raytracer.analysis.optical_system_analysis import \
                                                            OpticalSystemAnalysis
from pyrateoptics.raytracer.analysis.surface_shape_analysis  import ShapeAnalysis
# --- optimization
from pyrateoptics.optimize.optimize          import Optimizer
from pyrateoptics.optimize.optimize_backends import (ScipyBackend,
                                                     Newton1DBackend,
                                                     ParticleSwarmBackend,
                                                     SimulatedAnnealingBackend)

# --- auxiliarys
from auxiliary_functions import error2squared, error1


def buildInitialbundle(osa, s, sysseq, rays_dict, numrays=10, 
                       wavelength=[0.587e-3]):
    '''
    Initialises the Initialbundles
    '''    
    #Set defaults for dictionary
    rays_dict.setdefault("startx", [0])
    rays_dict.setdefault("starty", [0])
    rays_dict.setdefault("startz", [-7])
    rays_dict.setdefault("angley", [0])
    rays_dict.setdefault("anglex", [0])
    rays_dict.setdefault("rasterobj", raster.RectGrid())
    rays_dict.setdefault("radius", [15])
    
    # We want to build a Matrix with the initialbundles as entrys
    # get size of Matrix
    p = len(wavelength)
    q = len(rays_dict["startx"])*len(rays_dict["starty"])*len(rays_dict["startz"])*\
    len(rays_dict["angley"])*len(rays_dict["anglex"])*len(rays_dict["radius"])
    # initialize Matrix
    initialbundle = [[0 for x in range(p)] for y in range(q)]
    r2 = []

    #Iterate over all entries
    counteri = 0
    counterj = 0
    for i in rays_dict["startx"] :
        for j in rays_dict["starty"] :
            for k in rays_dict["startz"] :
                for l in rays_dict["angley"] :
                    for m in rays_dict["anglex"] :
                        for n in rays_dict["radius"] :
                            counterj = 0
                            #Setup dict for current Bundle
                            bundle_dict = {"startx":i, "starty":j, "startz":k,
                                           "angley":l, "anglex":m, "radius":n,
                                           "rasterobj":rays_dict["rasterobj"]}
                            for o in wavelength :
                                (o1, k1, E1) = osa.collimated_bundle(numrays,
                                                            bundle_dict, wave=o)
                                initialbundle[counteri][counterj] = \
                                     RayBundle(x0=o1, k0=k1, Efield0=E1, wave=o)
                                counterj = counterj + 1
                            counteri = counteri + 1
    return initialbundle

def get_bundle_merit(osa, s, sysseq, rays_dict, numrays=10,
                     wavelength=[0.587e-3], whichmeritfunc='standard',
                     error='error2', sample_param='wave'):
    """
    initializes the initialBundles and forms the meritfunction
    this is necessary as the meritfunction needs the initalbundle, but in the 
    optimization the initialBundle is not a Uebergabeparameter. Therefore the 
    meritfunction needs to be wrapped inside the bundle initialisation
    """

    initialbundle = buildInitialbundle(osa, s, sysseq, rays_dict, 
                                       numrays, wavelength)
    
    # --- define meritfunctions:
    # You can add your meritfunctionsrms-implementation and then add it to 
    # the dictionary. If the string whichmeritfunc is not a key in the dict. the 
    # standard_error2 function is taken. (exception handling)
    # This is a necessary generalization, because for instance the sgd needs 
    # a special meritfunc.

    # ---------------standard meritfunction
    def meritfunctionrms_standard(my_s, **kwargs):
        """
        Standard meritfunctionrms: 
        """
        res = 0

        # Loop over all bundles
        for i in range(0, len(initialbundle)):
            x = []
            y = []
            # Loop over wavelenghts
            for j in range(0, len(initialbundle[0])):
                my_initialbundle = initialbundle[i][j]
                rpaths = my_s.seqtrace(my_initialbundle, sysseq)

                # put x and y value for ALL wavelengths in x and y array 
                # to caculate mean
                x.append(rpaths[0].raybundles[-1].x[-1, 0, :])
                y.append(rpaths[0].raybundles[-1].x[-1, 1, :])

            # Add up all the mean values of the different wavelengths
            xmean = np.mean(x)
            ymean = np.mean(y)

            # Choose error function
            if (error == 'error2'):
                res += error2squared(x, xmean, y, ymean)
            elif (error == 'error1'):
                res += error1(x, xmean, y, ymean)

        return res

    # ---------------sgd meritfunction
    wavel = len(wavelength)
    def meritfunctionrms_sgd(my_s, **kwargs):
        if (len(kwargs) == 0):
            #print('kwargs = 0')
            return meritfunctionrms_standard(my_s)
        else:
            #print('kwargs != 0')
            res = 0
            sample_num = kwargs['sample_num']

            # choose the sampled bundle
            if (sample_param == 'bundle'):
                sample_initialbundle = initialbundle[sample_num]
            if (sample_param == 'wave'):
                sample_initialbundle = [initialbundle[sample_num//wavel]\
                                                     [sample_num%wavel]]
            if (sample_param == 'ray'):
                pass #TODO: this seems to be a little bit tricky, but i expect a 
                     #      bad solution anyway
 
            # Loop over sample_initialbundle
            for i in range(0, len(sample_initialbundle)):
                x = []
                y = []
                rpaths = my_s.seqtrace(sample_initialbundle[i], sysseq)
 
                # append x and y for each bundle
                x.append(rpaths[0].raybundles[-1].x[-1, 0, :])
                y.append(rpaths[0].raybundles[-1].x[-1, 1, :])
 
                # Add up all the mean values of the different wavelengths
                xmean = np.mean(x)
                ymean = np.mean(y)
 
                # Choose error function
                if (error == 'error2'):
                    res += error2squared(x, xmean, y, ymean)
                elif (error == 'error1'):
                    res += error1(x, xmean, y, ymean)

            return res

    # for defining which meritfunction should be used
    switcher = {'standard': meritfunctionrms_standard,
                'sgd'     : meritfunctionrms_sgd      }

    return (initialbundle, switcher.get(whichmeritfunc, \
                                        meritfunctionrms_standard))

