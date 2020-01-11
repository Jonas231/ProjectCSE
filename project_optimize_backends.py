from __future__ import print_function
import math
import random
import numpy
import scipy
import sys
from scipy.optimize import minimize
from scipy.optimize import OptimizeResult
from pyrateoptics.core.log import BaseLogger
from pyrateoptics.optimize.optimize_backends import Backend
from derivatives import grad, grad_pen, grad_lag, grad_log, hessian
from auxiliary_functions import get_bdry, eval_h, eval_c, my_log, printArray,\
                                termcondition

class ProjectScipyBackend(Backend):
    def __init__(self, optimize_func, methodparam=None, tau0=1.0,
                 options={}, stochagradparam=False, **kwargs):
        self.optimize_func   = optimize_func
        self.options         = options
        self.methodparam     = methodparam
        self.stochagradparam = stochagradparam
        self.kwargs          = kwargs
        self.tauk            = tau0
        self.lamk            = 1.
        self.stochagrad      = None
        # self.func = MeritFunctionWrapper is set within the Optimizer __init__ 

    def update_PSB(self, optimi) :
        '''
        function gets the boundaries for the variables. THis is necessary if 
        you want to run the optimization with penalty/lagrange terms. It is
        important to call this function AFTER the Optimizer object was created
        and BEFORE you run the optimization.
        '''

        self.bdry = get_bdry(optimi)
        printArray('bdry in ProjectScipyBackend = ', self.bdry)
    
    def run(self, x0):
        # tolerance for the infeasibility measurement 
        tol_seq = 10*numpy.finfo(float).eps 
        # number of iterations
        iterNum = 0
        # h for the gradient
        h = 1e-8
        # number of digits after the point of xk
        points = 7
        
        printArray('x0 =', x0, point=points)
        print('\nmeritfunction(x_0) = %10.6f' % (self.func(x0)))

        if (self.methodparam == 'standard'):

            # optimize: meritfunction(x)

            print('----------------- run standard -----------------')

            # find local minimizer of meritfunction(x)
            res = minimize(self.func, 
                           x0=x0, 
                           args=(), 
                           method=self.optimize_func,
                           options=self.options, 
                           **self.kwargs)

        elif (self.methodparam == 'penalty'):

            # optimize: meritfunction(x) + 0.5*tau*||h(x)||_2^2

            print('----------------- run penalty -----------------')

            xk_1 = x0
            xk   = x0
            while (1): 
                # define the gradient for the penalty method
                if (self.stochagradparam == True):
                    def stochagrad_total(x):
                        res = self.stochagrad(self.func, x, h) + \
                              grad_pen(x,self.bdry,self.tauk)
                        return res
                    def grad_total(x):
                        res = grad(self.func, x, h) + \
                              grad_pen(x,self.bdry,self.tauk)
                        return res
                    self.options['stochagrad'] = stochagrad_total
                else: # this is the default case
                    def grad_total(x):
                        res = grad(self.func, x, h) + \
                              grad_pen(x,self.bdry,self.tauk)
                        return res
                # store the grad-function in options
                self.options['grad'] = grad_total

                # for benchmark
                self.kwargs['jac'] = grad_total
 
                # update iteration number
                iterNum += 1
                print('\niteration number = %d' % (iterNum))
                printArray('bdry =', self.bdry)
                print('\ntau = %6.3f' % (self.tauk))
                printArray('gradient of the penalty term =',\
                           grad_pen(xk,self.bdry, self.tauk))

                # find local minimizer of 
                # meritfunction(x) + 0.5*tau_k*||h(x)||_2^2
                penalty_func = lambda x: self.func(x) +\
                                        0.5*self.tauk*numpy.square(\
                                        numpy.linalg.norm(eval_h(x,self.bdry)))
                
                res = minimize(penalty_func,
                               x0=xk, 
                               args=(), 
                               method=self.optimize_func,
                               options=self.options, 
                               **self.kwargs)
                # update xk
                xk = res.x

                printArray('x_k =', res.x, point=points)
                print('\nmeritfunction(x_k) = %10.6f' % (self.func(res.x)))

                # check if xk is in the feasible set with ||h(x)||_inf < 10*eps
                if (numpy.linalg.norm(eval_h(xk, self.bdry), numpy.inf) < tol_seq):
                    print('\n----------- end of penalty run -----------')
                    print('\nTerminated in iteration = %d' % (iterNum))
                    print('\n||h(x)||_inf = %5.3f' % \
                          (numpy.linalg.norm(eval_h(xk, self.bdry), numpy.inf)))
                    break
                else: # xk is not in the feasible set -> update tauk
                    # update tau
                    self.tauk = 7*self.tauk 

                # update xk-1 
                xk_1 = xk


        elif (self.methodparam == 'penalty-lagrange'):

            # optimize: meritfunction(x) + lambda^T h(x) + 0.5*tau*||h(x)||_2^2

            print('----------------- run penalty lagrange -----------------')

            # choose the initial lamda
            self.lamk = 0.333*numpy.ones(2*len(x0))

            xk_1 = x0
            xk   = x0
            while (1): 
             
                # define the gradient for the penalty-lagrange-function
                if (self.stochagradparam == True):
                    def stochagrad_total(x):
                        res = self.stochagrad(self.func, x, h) + \
                              grad_lag(x,self.bdry,self.tauk,self.lamk)
                        return res
                    def grad_total(x):
                        res = grad(self.func, x, h) + \
                              grad_lag(x,self.bdry,self.tauk,self.lamk)
                        return res
                    self.options['stochagrad'] = stochagrad_total
                else: # this is the default case
                    def grad_total(x):
                        res = grad(self.func, x, h) + \
                              grad_lag(x,self.bdry,self.tauk,self.lamk)
                        return res

                # store the grad-function in options
                self.options['grad']= grad_total
            
                # for benchmark
                self.kwargs['jac'] = grad_total

                # update iteration number
                iterNum += 1

                print('\niteration number = %d' % (iterNum))
                printArray('bdry =', self.bdry)
                print('\ntau = %6.3f' % (self.tauk))
                printArray('lambda_k =', self.lamk)
                printArray('gradient of the penalty term =',\
                           grad_lag(xk,self.bdry, self.tauk, self.lamk))


                # find local minimizer of 
                # meritfunction(x) + (lambda_k)^T h(x) + 0.5*tau_k*||h(x)||_2^2
                penalty_lag_func = lambda x: self.func(x) +\
                                       0.5*self.tauk*numpy.square(\
                                       numpy.linalg.norm(eval_h(x,self.bdry)))+\
                                       numpy.dot(self.lamk,eval_h(x,self.bdry))

                res = minimize(penalty_lag_func,
                               x0=xk, 
                               args=(), 
                               method=self.optimize_func,
                               options=self.options, 
                               **self.kwargs)
                # update xk
                xk = res.x

                printArray('x_k =', res.x, point=points)
                print('\nmeritfunction(x_k) = %10.6f' % (self.func(res.x)))

                # check if xk is in the feasible set with ||h(x)||_inf < 10*eps
                if (numpy.linalg.norm(eval_h(xk, self.bdry), numpy.inf) < tol_seq):
                    print('\n---------- end of penalty lagrange run ----------')
                    print('\nTerminated in iteration = %d' % (iterNum))
                    print('\n||h(x)||_inf = %5.3f' % \
                          (numpy.linalg.norm(eval_h(xk, self.bdry), numpy.inf)))
                    break
                else: # xk is not in the feasible set -> update tauk and lambdak
                    # update tau
                    self.tauk = 7*self.tauk
                    # update lambda
                    self.lamk = numpy.add(self.lamk, 
                                          self.tauk*eval_h(xk, self.bdry))
                # update xk-1
                xk_1 = xk


        elif (self.methodparam == 'log'):
            # Logarithmic Barrier Method
            print('----------------- run log barrier -----------------')

            self.my = 1.0 # '.0' is important, otherwise its an integer and my=0 
                          # in second step!

            xk_1 = x0
            xk   = x0
            while (1):
                # define the gradient for the penalty-lagrange-function
                if (self.stochagradparam == True):
                    def stochagrad_total(x):
                        res = self.stochagrad(self.func, x, h) + \
                              grad_log(x,self.bdry,self.my)
                        return res
                    def grad_total(x):
                        res = grad(self.func, x, h) + \
                              grad_log(x,self.bdry,self.my)
                        return res
                    self.options['stochagrad'] = stochagrad_total
                else: # this is the default case
                    def grad_total(x):
                        res = grad(self.func, x, h) + \
                              grad_log(x,self.bdry,self.my)
                        return res

                # store the grad-function in options
                self.options['grad']= grad_total

                # for benchmark
                self.kwargs['jac'] = grad_total

               # update iteration number
                iterNum += 1
                print('\niteration number = %d' % (iterNum))

                # find local minimizer of for the barrier method
                log_func = lambda x: self.func(x) - self.my*numpy.sum(\
                                     my_log(eval_c(x,self.bdry)))

                res = minimize(log_func,
                               x0=xk, 
                               args=(), 
                               method=self.optimize_func,
                               options=self.options, 
                               **self.kwargs)
                # update xk
                xk = res.x
                
                # why do you need this line?
                normneu = numpy.linalg.norm(xk)

                printArray('x_k =', res.x, point=points)
                print('\nmeritfunction(x_k) = %10.6f' % (self.func(res.x)))

                # check if xk is in the feasible set with ||h(x)||_inf < 10*eps
                if (numpy.linalg.norm(eval_h(xk, self.bdry), numpy.inf) < tol_seq):
                    print('\n---------- end of log barrier run----------')
                    print('\nTerminated in iteration = %d' % (iterNum))
                    print('\n||h(x)||_inf = %5.3f' % \
                          (numpy.linalg.norm(eval_h(xk, self.bdry), numpy.inf)))
                    break
                else: # xk is not in the feasible set -> update my
                    # update my
                    self.my = self.my/10

                # update xk-1
                xk_1 = xk

        else:
            print('Methodparam not found!')
            sys.exit()

        printArray('x_k =', res.x, point=points)
        print('\nmeritfunction(x_k) = %10.6f' % (self.func(res.x)))
        self.res = res
        return res.x


def sgd(func, x0, args, 
        maxiter=500,
        stepsize=1e-9,
        methods='nag',
        gamma=0.9,
        **kwargs):

    gradient = kwargs['grad']
    stochagrad = kwargs['stochagrad']
    iternum = 0
    xk_1 = x0
    fk_1 = func(x0)

    # momentum vector
    vk_1 = numpy.zeros(len(x0))

    while (1):
        # update iteration number
        iternum += 1

        # choose the method
        if (methods == 'vanilla'):
            vk = stepsize*stochagrad(xk_1)
        if (methods == 'momentum'):
            # momentum vector
            vk = gamma*vk_1+stepsize*stochagrad(xk_1)
            vk_1 = vk
        if (methods == 'nag'):
            # nesterov accelerated gradient
            vk = gamma*vk_1+stepsize*stochagrad(xk_1-gamma*vk_1)
            vk_1 = vk

        # iteration rule
        xk = xk_1 - vk 
        # debugging
        fk = func(xk)
        gk = gradient(xk)
        gknorm = numpy.linalg.norm(gk, numpy.inf)
        print('gknorm = %7.4f' %(gknorm))
        print('fk     = %7.4f' %(fk))

        # termination
        if ((iternum >= maxiter) or (gknorm <= 500)):
            break
        xk_1 = xk
        fk_1 = fk

    return OptimizeResult(fun=fk, x=xk, nit=iternum)


def adam(func, x0, args, 
         maxiter=300,
         stepsize=1e-2,
         beta1=0.1,
         beta2=0.99,
         epsilon=1e-2,
         **kwargs):

    gradient = kwargs['grad']
    stochagrad = kwargs['stochagrad']
    iternum = 0
    xk_1 = x0
    fk_1 = func(x0)

    # 1st moment vector
    mk_1 = numpy.zeros(len(x0))
    # 2nd moment vector
    vk_1 = numpy.zeros(len(x0))

    while (1):
        # update iteration number
        iternum += 1
        # get stochastic gradient
        gk = stochagrad(xk_1)
        # update first moment estimate
        mk   = beta1*mk_1+(1-beta1)*gk
        mk_1 = mk
        # update second moment estimate
        vk   = beta2*vk_1+(1-beta2)*numpy.power(gk,2)
        vk_1 = vk
        # compute bias-corrected first moment estimate
        mk_hat = mk/(1-numpy.power(beta1,iternum))
        # compute bias-corrected first moment estimate
        vk_hat = vk/(1-numpy.power(beta2,iternum))
        # iteration rule
        xk = xk_1 - stepsize*mk_hat/(numpy.power(vk_hat,0.5)+epsilon)

        fk = func(xk)
        gk = gradient(xk)
        gknorm = numpy.linalg.norm(gk, numpy.inf)
        print('gknorm = %7.4f' %(gknorm))
        print('fk     = %7.4f' %(fk))

        # termination
        if ((iternum >= maxiter) or (gknorm <= 500)):
            break
        xk_1 = xk
        fk_1 = fk

    return OptimizeResult(fun=fk, x=xk, nit=iternum)


def adamax(func, x0, args, 
           maxiter=300,
           stepsize=1e-2,
           beta1=0.09,
           beta2=0.99,
           thetaf=1e-1,
           p=None,
           **kwargs):

    gradient = kwargs['grad']
    stochagrad = kwargs['stochagrad']
    iternum = 0
    xk_1 = x0
    fk_1 = func(x0)
    ismin = False

    # 1st moment vector
    mk_1 = numpy.zeros(len(x0))
    # 2nd moment vector
    vk_1 = numpy.zeros(len(x0))

    while (1):
        iternum += 1
        # get stochastic gradient
        gk = stochagrad(xk_1)
        # update first moment estimate
        mk   = beta1*mk_1+(1-beta1)*gk
        mk_1 = mk
        # update second moment estimate
        vk   = numpy.maximum(beta2*vk_1, numpy.absolute(gk))
        vk_1 = vk
        # iteration rule
        xk = xk_1 - (stepsize/(1-numpy.power(beta1,iternum)))*mk/vk

        fk = func(xk)
        gk = gradient(xk)
        gknorm = numpy.linalg.norm(gk, numpy.inf)
        print('gknorm = %7.4f' %(gknorm))
        print('fk     = %7.4f' %(fk))

        # termination
        if ((iternum >= maxiter) or (gknorm <= 500)):
            break
        xk_1 = xk
        fk_1 = fk

    return OptimizeResult(fun=fk, x=xk, nit=iternum)


def adagrad(func, x0, args, 
            maxiter=300,
            stepsize=1e-3,
            epsilon=1e-3,
            **kwargs):

    gradient = kwargs['grad']
    stochagrad = kwargs['stochagrad']
    iternum = 0
    dim = len(x0)
    xk_1 = x0
    fk_1 = func(x0)
    G = numpy.zeros(dim)

    while (1):
        # update iteration number
        iternum += 1
        # get stochastic gradient
        gk = stochagrad(xk_1)
        # update G
        G += gk*gk
        # iteration rule
        xk = xk_1 - stepsize*(gk/(numpy.sqrt(G)+epsilon))

        # debugging
        fk = func(xk)
        gk = gradient(xk)
        gknorm = numpy.linalg.norm(gk, numpy.inf)
        print('gknorm = %7.4f' %(gknorm))
        print('fk     = %7.4f' %(fk))

        # termination
        if ((iternum >= maxiter) or (gknorm <= 500)):
            break
        xk_1 = xk
        fk_1 = fk

    return OptimizeResult(fun=fk, x=xk, nit=iternum)


def adadelta(func, x0, args, 
             maxiter=300,
             roh=0.9999,
             epsilon=1e-7,
             **kwargs):

    gradient   = kwargs['grad']
    stochagrad = kwargs['stochagrad']
    iternum = 0
    dim = len(x0)
    xk_1 = x0
    fk_1 = func(x0)
    Egk_1 = numpy.zeros(dim)
    Exk_1 = numpy.zeros(dim)

    while (1):
        # update iteration number
        iternum += 1
        # get stochastic gradient
        gk = stochagrad(xk_1)
        # accumulate gradient
        Egk   = roh*Egk_1+(1-roh)*gk*gk
        Egk_1 = Egk
        # calculate RMS[g]_k and RMS[delta x]_k-1
        RMSg = numpy.sqrt(Egk  +epsilon)
        RMSx = numpy.sqrt(Exk_1+epsilon)
        # delta
        delta_xk = -(RMSx/RMSg)*gk
        # iteration rule
        xk = xk_1 + delta_xk
        # accumulate updates
        Exk   = roh*Exk_1+(1-roh)*delta_xk*delta_xk
        Exk_1 = Exk

        # debugging
        fk = func(xk)
        gk = gradient(xk)
        gknorm = numpy.linalg.norm(gk, numpy.inf)
        print('gknorm = %7.4f' %(gknorm))
        print('fk     = %7.4f' %(fk))

        # termination
        if ((iternum >= maxiter) or (gknorm <= 500)):
            break
        xk_1 = xk
        fk_1 = fk

    return OptimizeResult(fun=fk, x=xk, nit=iternum)


def get_scipy_stochastic_hybrid(stocha_opt_func, scipy_method, backend_bdry):

    lb = numpy.empty([len(backend_bdry)/2])
    ub = numpy.empty([len(backend_bdry)/2])
    for i in range(len(backend_bdry)/2)):
        lb[i] = backend_bdry[2*i]
        ub[i] = backend_bdry[2*i+1]
    bound = scipy.minimize.Bounds(lb,ub)
    
    def scipy_stochastic_hybrid(func, x0, args=(),
                                maxiter=200,
                                stepsize=1e-8,
                                **kwargs):
        kwargs['bounds'] = bound
        # stochastic method to get in a surrounding of a minimum
        res_approx = stocha_opt_func(func, x0, args, 
                                     maxiter=maxiter
        x_approx = res_approx.x
        # deterministic method to get convergence
        res_sol = scipy.minimize()
        x_sol = res_sol.x
        
        return OptimizeResult(fun=fk, x=xk, nit=iternum)



def gradient_descent(func, x0, args=(),
                     maxiter=100, stepsize=1e-8, **kwargs):
    xk = x0
    grad = kwargs['grad']
    iternum = 0 

    while (iternum < maxiter):
        iternum += 1
        xk -= stepsize*grad(xk)
        if (numpy.linalg.norm(grad(xk), numpy.inf) <= 500):
            print('\ngradient is near zero\n')
            print('||grad(x_final)||_inf = %10.6'\
                  % (numpy.linalg.norm(grad(xk), numpy.inf)))
            print('\nTerminated in iteration: %d' % (iternum))
            break

    printArray('gradient in gradient decsent for x_final = ', grad(xk))
    return OptimizeResult(fun=func(xk), x=xk, nit=iternum)


def test_minimize_neldermead(func, x0, args=(), 
                             maxiter=100, 
                             xatol=1e-6, fatol=1e-6,
                             **unknown_options):
    alpha = 1
    beta = 2
    gamma = 0.5
    sigma = 0.5
    # convert x into float array and flat
    x0 = numpy.asfarray(x0).flatten()
    N = len(x0)
    nonzdelt = 0.05 # params from scipy impl
    zdelt = 0.00025 # params from scipy impl
    # set up simplex, also from scipy impl in order to get the same init simplex
    sim = numpy.zeros((N + 1, N), dtype=x0.dtype)
    sim[0] = x0
    for k in range(N):
        y = numpy.array(x0, copy=True)
        if y[k] != 0:
            y[k] = (1 + nonzdelt)*y[k]
        else:
            y[k] = zdelt
        sim[k + 1] = y

    # initilize f simplex
    fsim = numpy.zeros((N + 1,), float)
    for k in range(N + 1):
        fsim[k] = func(sim[k])

    ind = numpy.argsort(fsim)
    # sort f simplex so fsim [0,:] is the lowest function value
    fsim = numpy.take(fsim, ind, 0)
    # sort so sim[0,:] has the lowest function value
    sim = numpy.take(sim, ind, 0)
    iterNum = 1
    # we follow the implementation from the num3 lecture notes
    while (iterNum < maxiter):
        # same break condition as scipy
        if (numpy.max(numpy.ravel(numpy.abs(sim[1:] - sim[0]))) <= xatol and
                numpy.max(numpy.abs(fsim[0] - fsim[1:])) <= fatol):
            break
        xbar = numpy.add.reduce(sim[:-1],0)/N
        x_a = xbar - alpha*(sim[-1]-xbar)
        f_a = func(x_a)

        if (fsim[0] <= f_a and f_a <= fsim[-2]):
            sim[-1] = x_a
        elif (f_a < fsim[0]):
            x_ab = xbar - alpha*beta*(sim[-1]-xbar)
            f_ab = func(x_ab)
            if (f_ab < fsim[0]):
                sim[-1] = x_ab
            else: 
                sim[-1] = x_a
        else: # f_a > fsim[-2]
            if (fsim[-2] < f_a and f_a < fsim[-1]):
                x_ag = xbar - alpha*gamma*(sim[-1]-xbar)
                f_ag = func(x_ag)
                if (f_ag <= f_a):
                    sim[-1] = x_ag
                else: 
                    for i in range(N):
                        sim[i+1] = sigma*(sim[0]+sim[i+1])
            else: # f_a is the worst value
                xg = xbar + gamma*(sim[-1]-xbar)
                fg = func(xg)
                if (fg < fsim[-1]):
                    sim[-1] = xg
                else:
                    for i in range(N):
                        sim[i+1] = sigma*(sim[0]+sim[i+1])
        for i in range(N+1):
            fsim[i] = func(sim[i])

        iterNum += 1
        ind = numpy.argsort(fsim)
        sim = numpy.take(sim, ind, 0)
        fsim = numpy.take(fsim, ind, 0)

    x_sol = sim[0]
    fval = numpy.min(fsim)
    return OptimizeResult(fun=fval, x=x_sol, nit=iterNum, 
                          final_simplex=(sim, fsim))


def PSO_NM(func,x0,args=(),N=None,vel_max=None,maxiter=50,\
                 c0=None,c1=1.4,c2=1.4,**unknown_options):
    # N = population size (has to be: N >= 2n+1; with n=problem size)
    # vel_max = maximal velocity of a particle
    # c0,c1 and c2 are variables for updating the velocity of the particles

    #rm is a method which brings a solution x in a infeasible region ...
    #to a feasible region
    #---------------------------------------------------------------------------
    def rm(x,lb,ub):                      # repair method (later grad.bas.r.m)
        # moves positions on bounds if they don't be in the feasible region
        from copy import deepcopy
        x_neu = deepcopy(x)
        for t in range(len(x)):
            if (x[t]<lb[t]):
                x_neu[t] = lb[t]
            if (x[t]>ub[t]):
                x_neu[t] = ub[t]
        return x_neu

    def Cf(x,lb,ub):                        # Constraint fitness priority-based ranking method
        C = numpy.empty(len(lb)+len(ub))
        g = numpy.empty(len(lb)+len(ub))
        for t in range(len(x)):
            g[2*t] = lb[t]-x[t]             # value of g_i(x)
            g[2*t+1] = x[t]-ub[t]
        gmax = numpy.amax(g)
        for t in range(len(g)):
            if (g[t]<=0):
                C[t] = 1
            else:
                C[t] = 1-(g[t]/gmax)
        weight = 1/float((len(C)))
        Cf = 0
        for t in range(len(C)):
            Cf += weight*C[t]
        return Cf

    def nelder_mead_con(initial_simplex,func,Cf,lb,ub,maxiter=50,tolError=1e-8):
    # Nelder-Mead for constraint optimization
    # initial_simplex should be array of shape (N+1,N) with N: problem size
        alpha = 1
        beta = 0.5
        gamma = 2
        delta = 0.5
        tol = 1e-12

        n = len(initial_simplex[0])
        xfC = []                    # list with [[x1,f(x1),Cf(x1)],[x2,f(x2),Cf(x2)],...
        for t in range(n+1):
            xfC.append([initial_simplex[t],func(initial_simplex[t]),\
                        Cf(initial_simplex[t],lb,ub)])
        
        # termination condition for first check in while loop:
        f_mean = 0
        for t in range(n+1):
            f_mean += xfC[t][1]
        f_mean = f_mean * (1/(float(n)+1))
        error = 0
        for t in range(n+1):
            error += (xfC[t][1]-f_mean)**2
        error *= 1/(float(n)+1)

        it = 1
        while (it <= maxiter and error > tolError):
            # sort xfC from low to high f(x) values
            xfC = sorted(xfC,key=lambda elem: elem[1])
            # Reflection:
            # Determine x_cent without x_high:
            x_cent = numpy.zeros(n)
            for t in range(n):
                for j in range(n):
                    x_cent[j] += xfC[t][0][j]
            for t in range(n):
                x_cent[t] /= n
            # make reflection:
            x_high = xfC[n][0]
            f_high = xfC[n][1]
            x_refl = (1+alpha)*x_cent-alpha*x_high
            Cf_refl = Cf(x_refl,lb,ub)
            f_refl = func(x_refl)
            x_low = xfC[0][0]
            Cf_low = xfC[0][2]
            f_low = xfC[0][1]
            
    
            if ((Cf_refl<1 and Cf_refl>Cf_low) or ((Cf_refl<=1+tol and Cf_refl>=1-tol) and \
                f_refl<f_low)):
                # first expansion case:
                if (Cf_refl<1 and Cf_refl>Cf_low):
                    x_exp = gamma*x_refl+(1-gamma)*x_cent
                    f_exp = func(x_exp)
                    Cf_exp = Cf(x_exp,lb,ub)
                    if (Cf_exp>Cf_low or (Cf_exp>=1-tol and Cf_exp<=1+tol)):
                        # expansion accepted -> replace x_high by x_exp:
                        xfC[n][0] = x_exp
                        xfC[n][1] = f_exp
                        xfC[n][2] = Cf_exp
                    else:
                        # replace x_high by x_refl:
                        xfC[n][0] = x_refl
                        xfC[n][1] = f_refl
                        xfC[n][2] = Cf_refl
                # second expansion case:
                if ((Cf_refl>=1-tol and Cf_refl<=1+tol)and(f_refl<f_low)):
                    x_exp = gamma*x_refl+(1-gamma)*x_cent
                    f_exp = func(x_exp)
                    Cf_exp = Cf(x_exp,lb,ub)
                    if ((Cf_exp>=1-tol and Cf_exp<=1+tol)and(f_exp<f_low)):
                        # expansion ist acceptet, replace x_high by x_exp:
                        xfC[n][0] = x_exp
                        xfC[n][1] = f_exp
                        xfC[n][2] = Cf_exp
                    else:
                        # replacing x_high by x_refl:
                        xfC[n][0] = x_refl
                        xfC[n][1] = f_refl
                        xfC[n][2] = Cf_refl
    
            else:
                # first contraction case:
                if (Cf_refl<1 and Cf_refl<=Cf_low):
                    x_cont = beta*x_high+(1-beta)*x_cent
                    f_cont = func(x_cont)
                    Cf_cont = Cf(x_cont,lb,ub)
                    if ((Cf_cont>Cf_low)or(Cf_cont>=1-tol and Cf_cont<=1+tol)):
                        # contraction is accepted: replace x_high by x_cont:
                        xfC[n][0] = x_cont
                        xfC[n][1] = f_cont
                        xfC[n][2] = Cf_cont
                    else:
                        # shrinkage attempts to all points except x_low:
                        for t in range(n):
                            xfC[1+t][0] *= delta
                            xfC[1+t][0] += (1-delta)*x_low
                # second contraction case:
                if((Cf_refl>=1-tol and Cf_refl<=1+tol)and(f_refl>=f_low) \
                    and (f_refl<=f_high)):
                    # replace x_high by x_refl:
                    xfC[n][0] = x_refl
                    xfC[n][1] = f_refl
                    xfC[n][2] = Cf_refl
                    x_cont = beta*x_refl+(1-beta)*x_cent
                    f_cont = func(x_cont)
                    Cf_cont = Cf(x_cont,lb,ub)
                    if((Cf_cont>=1-tol and Cf_cont<=1+tol)and(f_cont<f_low)):
                        # contraction accepted: replace x_high by x_cont
                        xfC[n][0] = x_cont
                        xfC[n][1] = f_cont
                        xfC[n][2] = Cf_cont
                    else:
                        # shrinkage the entire simplex but not x_low
                        for t in range(n):
                            xfC[1+t][0] *= delta
                            xfC[1+t][0] += (1-delta)*x_low
                # third contraction case:
                if((Cf_refl>=1-tol and Cf_refl<=1+tol)and(f_refl>=f_low) \
                    and (f_refl>f_high)):
                    x_cont = beta*x_high+(1-beta)*x_cent
                    f_cont = func(x_cont)
                    Cf_cont = Cf(x_cont,lb,ub)
                    if((Cf_cont>=1-tol and Cf_cont<=1+tol)and(f_cont<f_low)):
                        # contraction accepted: replace x_high by x_cont
                        xfC[n][0] = x_cont
                        xfC[n][1] = f_cont
                        xfC[n][2] = Cf_cont
                    else:
                        # shrinkage the entire simplex but not x_low
                        for t in range(n):
                            xfC[1+t][0] *= delta
                            xfC[1+t][0] += (1-delta)*x_low
            it = it+1
            # termination condition:
            f_mean = 0
            for t in range(n+1):
                f_mean += xfC[t][1]
            f_mean *= 1/(float(n)+1)
            error = 0
            for t in range(n+1):
                error += (xfC[t][1]-f_mean)**2
            error *= 1/(float(n)+1)   

        final_simplex = numpy.empty([n+1,n])
        for t in range(n+1):
            final_simplex[t] = xfC[t][0]
        return final_simplex
    
    #---------------------------------------------------------------------------

    n = len(x0)             # problem size
    bounds = unknown_options['bounds']

    if (N==None):           # define swarm size
        N = 21*n+1
    if (vel_max==None):     # define maximal velocity (30% of feasible interval)
        vel_max = numpy.empty(n)
        for q in range(n):
            vel_max[q] = 0.1 * (bounds.ub[q]-bounds.lb[q])
    if (c0==None):          # define weight c0
        c0 = 0.5 + (random.random()/3)

    bounds = unknown_options['bounds']
    # Generate a class for the particles:
    class particle:
        #best_swarm = numpy.empty(n)
        #best_swarm_f = 0
        def __init__(self,pos,vel):
            self.pos = pos
            self.pos_f = func(pos)
            #self.best_part = pos        # best position of this particle
            #self.best_part_f = self.pos_f
            self.vel = vel
        def updatePos(self,pos):
            self.pos = pos
            self.pos_f = func(self.pos)
            #self.checkBestPart
        def update(self,c0,c1,c2,gBest,nBest):  # gBest:global best; nBest:neighborhood best
            r1 = random.random()       # random number between 0 and 1
            r2 = random.random()
            self.vel = c0*self.vel + c1*r1*(nBest-self.pos) + \
                        c2*r2*(gBest-self.pos)
            #check if self.vel is out of [-vel_max,vel_max]:
            for q in range(n):
                if (self.vel[q] < -vel_max[q]):
                    self.vel[q] = -vel_max[q]
                if (self.vel[q] > vel_max[q]):
                    self.vel[q] = vel_max[q]
            # Update position
            self.pos = self.pos + self.vel
            self.pos_f = func(self.pos)
            #self.checkBestPart
        #def checkBestPart():            # checks if actual pos. ist better than best_part
        #    if (self.pos_f <= self.best_part_f):
        #        self.best_part = self.pos
        #        self.best_part_f = func(self.pos)
    
    # Initialization of all particles with Position and velocity:
    swarm = []
    for i in range(N):
        pos0 = numpy.random.uniform(bounds.lb,bounds.ub)    # start position in feasible region
        vel0 = random.random() * vel_max                    # random start velocity
        swarm.append(particle(pos0,vel0))

    k = 0           # Iteration
    xBest = x0
    xBest_f = func(x0)
    stopCrit = 0            # counter for stopping criteria

    while (k <= maxiter):
        test = 0
        #Evaluate solutions and apply Repair Method if not in feasible region:
        liste = []                            # list to safe (pos(i),f(pos(i)),...
        for i in range(N):
            # check if solution is in feasibale region, else apply Repair Method
            if not (numpy.all(swarm[i].pos>=bounds.lb) and \
                    numpy.all(swarm[i].pos<=bounds.ub)):
                repairedPos = rm(swarm[i].pos,bounds.lb,bounds.ub)
                test += 1
                swarm[i].updatePos(repairedPos)
            # write tupel (i,f(i)) in liste:
            temp = [i,swarm[i].pos_f]
            liste.append(temp)
        # sort liste from low func values to high func values:
        liste = sorted(liste,key=lambda elem: elem[1])
        print("test = ",test)
        print("best value = ",liste[0][1])
        if numpy.all(swarm[liste[0][0]].pos>=bounds.lb) and numpy.all(swarm[liste[0][0]].pos<=bounds.ub):
            print("bounds are good")
        # Update xBest and xBest_f if solution is better:
        if (liste[0][1] <= xBest_f):
            xBest = swarm[liste[0][0]].pos
            xBest_f = liste[0][1]
            stopCrit = 0

        stopCrit = stopCrit+1
        print("Best = ",xBest_f)

        # check stopping criteria:
        if (k==maxiter or stopCrit>=5):
            return OptimizeResult(fun=xBest_f, x=xBest, nit = k)
            break

        # Apply Nelder-Mead to the (n+1) best particles:
        initial_simplex = numpy.empty([n+1,n])
        for i in range(n+1):
            initial_simplex[i] = swarm[liste[i][0]].pos
        final_simplex = nelder_mead_con(initial_simplex,func,Cf,bounds.lb,bounds.ub)
        # Update (n+1)th particle:
        for i in range(n+1):
            particle = liste[i][0]
            swarm[particle].updatePos(final_simplex[i])
            liste[i][1] = swarm[particle].pos_f

        # Update liste:
        liste = sorted(liste,key=lambda elem: elem[1])
        # Apply PSO to all N particles:
        #1.) Determine global best particle:
        gBest = liste[0][0]             # index of global best particle
        #2.) Divide 20n paritcles in two neighborhoods with 10N particles and
        #    determine best of these tows:
        firstN = numpy.arange(n+1,10*n+n+1,dtype=int)
        secondN = numpy.arange(10*n+n+1,20*n+n+1,dtype=int)
        random.shuffle(firstN)          # random shuffeling
        random.shuffle(secondN)         # "
        for i in range(len(firstN)):
            first = firstN[i]
            second = secondN[i]
            nBest = 0
            if (swarm[first].pos_f <= swarm[second].pos_f):
                nBest = first
            else:
                nBest = second
            swarm[first].update(c0,c1,c2,swarm[gBest].pos,swarm[nBest].pos)     # update velocity and position
            swarm[second].update(c0,c1,c2,swarm[gBest].pos,swarm[nBest].pos)

        k = k+1

    """
        # loop over all particles:
        for i in range(N):
            f_i_k = func(swarm[i].pos)
            print("f = ",f_i_k)
            if (f_i_k <= swarm[i].best_part_f): # update best position of particle
                swarm[i].best_part_f = f_i_k
                swarm[i].best_part   = swarm[i].pos
            if (f_i_k <= best_swarm_f):         # update best position of swarm
                best_swarm_f = f_i_k
                best_swarm = swarm[i].pos

        # loop over all particles for Updating:
        for i in range(N):
            swarm[i].update(c1,c2,best_swarm)
        
        # Increment Iteration
        k = k+1

    return OptimizeResult(fun=best_swarm_f, x=best_swarm, nit = k)
    """


# from:
# https://github.com/scipy/scipy/blob/v1.3.3/scipy/optimize/optimize.py#L77-L132
"""
class OptimizeResult(dict):
    Represents the optimization result.

    Attributes
    ----------
    x : ndarray
        The solution of the optimization.
    success : bool
        Whether or not the optimizer exited successfully.
    status : int
        Termination status of the optimizer. Its value depends on the
        underlying solver. Refer to `message` for details.
    message : str
        Description of the cause of the termination.
    fun, jac, hess: ndarray
        Values of objective function, its Jacobian and its Hessian (if
        available). The Hessians may be approximations, see the documentation
        of the function in question.
    hess_inv : object
        Inverse of the objective function's Hessian; may be an approximation.
        Not available for all solvers. The type of this attribute may be
        either np.ndarray or scipy.sparse.linalg.LinearOperator.
    nfev, njev, nhev : int
        Number of evaluations of the objective functions and of its
        Jacobian and Hessian.
    nit : int
        Number of iterations performed by the optimizer.
    maxcv : float
        The maximum constraint violation.

    Notes
    -----
    There may be additional attributes not listed above depending of the
    specific solver. Since this class is essentially a subclass of dict
    with attribute accessors, one can see which attributes are available
    using the `keys()` method.
    
"""
# from 
# https://github.com/scipy/scipy/blob/v1.3.3/scipy/optimize/_minimize.py#L42-L626
"""
def minimize(fun, x0, args=(), method=None, jac=None, hess=None,
             hessp=None, bounds=None, constraints=(), tol=None,
             callback=None, options=None):
    .
    .
    .
    **Custom minimizers**
    It may be useful to pass a custom minimization method, for example
    when using a frontend to this method such as `scipy.optimize.basinhopping`
    or a different library.  You can simply pass a callable as the ``method``
    parameter.
    
    The callable is called as 
    
    ``method(fun, x0, args, **kwargs, **options)``
    
    where ``kwargs`` corresponds to any other parameters passed to `minimize`
    (such as `callback`, `hess`, etc.), except the `options` dict, which has
    its contents also passed as `method` parameters pair by pair.  Also, if
    `jac` has been passed as a bool type, `jac` and `fun` are mangled so that
    `fun` returns just the function values and `jac` is converted to a function
    returning the Jacobian.  The method shall return an `OptimizeResult`
    object.
    The provided `method` callable must be able to accept (and possibly ignore)
    arbitrary parameters; the set of parameters accepted by `minimize` may
    expand in future versions and then these parameters will be passed to
    the method.  You can find an example in the scipy.optimize tutorial.
    .
    .
    .
"""

# custom optimize signature example from:
# https://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html
"""
def custmin(fun, x0, args=(), maxfev=None, stepsize=0.1,
            maxiter=100, callback=None, **options):
"""
# another from:
# https://github.com/scipy/scipy/blob/v1.3.3/scipy/optimize/optimize.py#L77-L132
"""
def _minimize_neldermead(func, x0, args=(), callback=None,
                         maxiter=None, maxfev=None, disp=False,
                         return_all=False, initial_simplex=None,
                         xatol=1e-4, fatol=1e-4, adaptive=False,
                         **unknown_options):
"""
# How they take the boundaries into account.
# from
# class FloatOptimizableVariable(OptimizableVariable):
"""
 import math

 def left_bounded(x):
     return math.fabs(left)*math.log((x - left)/math.fabs(left))

 def left_bounded_inv(x):
     return left + math.fabs(left)*math.exp(x/math.fabs(left))

 def right_bounded(x):
     return -math.fabs(right)*math.log((right - x)/math.fabs(right))

 def right_bounded_inv(x):
     return right - math.fabs(right)*math.exp(-x/math.fabs(right))

 def both_bounded(x):
     return math.log((-x + left)/(x - right)) * math.fabs(left - right)

 def both_bounded_inv(x):
     return left +\
             (right - left)/(1. + math.exp(-x/math.fabs(right - left)))


"""                                                                          
 
