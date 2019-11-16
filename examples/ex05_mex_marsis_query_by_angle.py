# das2 module example 6:
#   Plotting Mars Express MARSIS plasma density.  Demonstrates:
#     
#     1) Subsetting data in dimensions other than time
#     2) Usage of test data sources
#     3) Reading X-Y-Z pattern stream usage
#     4) Overlapping polar and cartesian plots

import numpy as np
import das2
import das2.mpl

import matplotlib.pyplot  as pyplot
import matplotlib.patches as patches
import matplotlib.colors  as colors

# ########################################################################### #

def make_axes(
   fig, location, r_max, r_offset, title, sub_title, theta_label, rad_label
):
   """Create a set of axes consisting of a 0 to 180 degree polar plot 
   in front of a cartesian plot sharing the same origin.  
   
   Since this will be used for Solar Zenith angle, include a day/night Mars
   of radius r_offset at the center.
   """
   
   radius = r_max + r_offset  # The real radius in data coordinates
   
   # To make the cartesian axis overlap with 1/2 semi-circle polar axis
   # scoot the y limits down by half the radius.
   cart_ax = fig.add_axes(
      location, aspect='equal',
      xlim = (-radius, radius),
      ylim = (-radius + 0.5*radius, radius + 0.5*radius),
      frameon=False, fc='none'
   )
   cart_ax.autoscale(False, axis='both')
   cart_ax.get_xaxis().set_visible(False)
   cart_ax.get_yaxis().set_visible(False)
   
   # The half-radius below is to adjust for the fact that a half-circle
   # polar plot uses less space than a full circle.
   day = patches.Wedge(
      (0,0), r_offset, 90, 180, width=r_offset, zorder=99.0,
      color="#c47e42"
   )
   night = patches.Wedge(
      (0,0), r_offset, 0, 90, width=r_offset, zorder=99.0,
      color="#000000"
   )
   
   #cart_ax.add_patch(day)
   #cart_ax.add_patch(night)

   pol_ax = fig.add_axes(location, projection='polar', fc='none')
   pol_ax.set_rorigin( - r_offset)
      
   pol_ax.set_theta_zero_location('W')
   pol_ax.set_thetagrids([15*i for i in range(13)])
   pol_ax.set_rticks([ i * (r_max/4) for i in range(5) ])
   pol_ax.set_rmax(r_max)
   pol_ax.set_thetamin(0)
   pol_ax.set_thetamax(180)
   pol_ax.set_theta_direction(-1)
   pol_ax.autoscale(False, axis='both')
   
   
   pol_ax.text(
      np.pi/2, 1.25*r_max, title, horizontalalignment='center', fontsize=16 
   )
   
   #pol_ax.text(
   #   np.pi/2, 1.17*r_max, sub_title, horizontalalignment='center', 
   #   fontsize=11, fontstyle='italic'
   #) 

   pol_ax.text(- np.pi/18, r_max/2, rad_label, 
              ha='center', va='center')
              
   pol_ax.text(np.pi/4, 1.15*r_max, theta_label, rotation=45, 
              ha='center', va='center', rotation_mode='anchor')

   return (cart_ax, pol_ax)
   

# ########################################################################### #

def to_cartesian(aTheta, aRad, r_offset):
   """Matching function for make_axes.  Converts polar coordinates to 
   cartesian coordinates.
   """
      
   aX = (aRad + r_offset) * np.cos(np.pi - aTheta)
   aY = (aRad + r_offset) * np.sin(np.pi - aTheta)
   
   return aX, aY

# ########################################################################### #

def main():

   # get a datasource, use it to download data
   
   sId = "test:/uiowa/mars_express/marsis/ne-density-planetographic/das2"
   src = das2.get_source(sId)
   print(src.info())

   beg = '2014-01-01'
   end = '2016-01-01'
   r_alt_max = 2000
   theta_sza_max = 135
   
   #query = {'alt':(0, 2000), 'sza':(0, theta_sza_max), 'time':(beg, end)}
   query = {'alt':(0, 2000), 'time':(beg, end)}
   datasets = src.get(query, verbose=True)
   ds = datasets[0]
   print(ds)
   

   # access the physical dimensions and numpy arrays in the dataset
   
   alt_dim = ds['alt']        # The altitude dimension
   alt_ary = ds.array('alt')  # equavalent to: ds['alt']['center'].array

   sza_dim = ds['sza']        # The solar zenith angle dimension
   sza_ary = ds.array('sza') * (np.pi / 180.0)  # scale to radians

   Ne_dim  = ds['dens']       # The plasma density dimension
   Ne_ary  = ds.array('dens')

   # Plotting...
   
   fig = pyplot.figure(figsize=(6,4))
   
   loc_in_fig = [0.03,0.0,0.9,0.9]
   r_offset = 1000
   
   title     = "MARSIS - Plasma Density by Solar Zenith Angle and Altitude"
   sub_title = "%s to %s, SZA max %d$^\\circ$, expanded altitude scale"%(
      beg, end, theta_sza_max
   )
   theta_label = das2.mpl.label(sza_dim.props['label'])
   rad_label   = das2.mpl.label(alt_dim.props['label'])
   
   cart_ax, pol_ax = make_axes(
      fig, loc_in_fig, r_alt_max, r_offset, title, sub_title, 
      theta_label, rad_label
   )
   
   # HexBin doesn't seem to work in polar space, use the cartesian axes
   x_ary, y_ary = to_cartesian(sza_ary, alt_ary, r_offset)
   
   color_scale = colors.LogNorm(10, 20000)
   hb = cart_ax.hexbin(
      x_ary, y_ary, Ne_ary, gridsize=120, mincnt=1, norm=color_scale,
      bins=None, cmap='jet'
   )
   
   # Colorbar axis
   density_label = "$\mathregular{N_{e}\\ (cm^{-3})}$"
      
   color_ax = fig.add_axes([0.87, 0.225, 0.02, 0.425])
   color_ax.text(
      3.0, 0.5, density_label, ha='center', va='center', 
      transform=color_ax.transAxes, rotation=90
   )
              
   fig.colorbar(hb, cax=color_ax)
   
   pyplot.show()

if __name__ == '__main__': main()

