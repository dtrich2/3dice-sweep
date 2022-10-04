from scipy.optimize import fsolve
import numpy as np

def tmax(lh,tj,p_dens, k, t, pitch, x=0):
	lh=lh*1e-6
	return p_dens*1e4/(t*1e-6)*np.power(lh,2)/k*(1-np.cosh((x*1e-6)/lh)/np.cosh(pitch*1e-6/(2*lh)))-tj

def get_lh(tj,p_dens, k, t, pitch):
	lh = fsolve(tmax, 25, args=(tj,p_dens, k, t, pitch))[0]
	g=k*t*1e-6/(lh*1e-6)**2
	return (g, lh)
