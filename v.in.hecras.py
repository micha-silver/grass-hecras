#!/usr/bin/env python
#
############################################################################
#
# MODULE:	   v.in.hecras
# AUTHOR(S):   	Micha Silver 
#				micha@arava.co.il  Arava Drainage Authority	
# PURPOSE:	  Reads an *.sdf file in HEC-RAS text format 
#			The input file must include WATER SURFACE EXTENTS: rows 
#			as part of the HEC-RAS output
#			These water surface extent points are used to create a GRASS polygon vector
# COPYRIGHT: 	This program is free software under the GNU General Public
#			   License (>=v2). Read the file COPYING that comes with GRASS
#			   for details.
#
# REVISIONS:	April 2015, adapted for GRASS 7.0
#############################################################################

#%module
#% description: Read a sdf formatted ascii text file, output from a HEC-RAS analysis and create a polygon vector of water surface extent 
#% keywords: HEC-RAS
#% keywords: water surface
#%end
#% option
#% key: input
#% type:string
#% description: Name of input HEC-RAS file (from run of simulation)
#% required: yes
#%end
#%option
#% key: output
#% type: string
#% description: Name of output GRASS polygon vector
#% required: yes
#%end

import sys
import os
import grass.script as grass

def cleanup():
	grass.message("Finished")


def read_sdf(input):
	"""
	Read the input SDF, scanning for lines with "WATER SURFACE EXTENT"
	read the coords from the next line, and save to two lists
	Return the lists
	"""
	left_pairs=[]
	right_pairs=[]
	with open(input, 'r') as sdf:
		lines = sdf.readlines()
		sdf.close()
		
        for i in range(len(lines)):
            if 'WATER SURFACE EXTENT' in lines[i]:
	    # Found a surface extent line, the next line has the coord pairs
	        coords = lines[i+1].strip().replace(" ", "").split(",")
	        lpair = [coords[0], coords[1]]
                rpair = [coords[2], coords[3]]
	        left_pairs.append(lpair)
	        right_pairs.append(rpair)	
        	
        return left_pairs, right_pairs

def create_water_surface(left_pairs, right_pairs, out_vect):
	"""
	Use the two lists of coordinate pairs to create a text file for import into v.in.ascii
	The left coords first, then the right coords starting from the end, 
	in order to make a closed polygon. Starting upstream along the left side of the water surface, 
	to the end of the reach, then back to the start along the right side
	Add the first point of the left pairs a second time to complete the boundary
	"""
	tmp_coords = grass.tempfile()
	proc=os.getpid()
	tmp_vect = out_vect+"_tmp_"+str(proc)
	
	# How many total points in the boundary: all the right side+ left side +1 
	# to allow for the first point a 2nd time to close boundary
	ttl_pts = len(left_pairs)+len(right_pairs)+1
	grass.message("Total number of vertices to be added to water surface polygon: %s" % ttl_pts)
	
	with open(tmp_coords,'w') as tmp:
	# Write coords in the standard ASCII file format for a grass boundary
	# Loop thru the left coord pairs, then in reverse thru the right pairs
	    tmp.write("VERTI:\n")
	    tmp.write("B %s\n" % ttl_pts)
	    for i in range(len(left_pairs)):
	        tmp.write(" "+left_pairs[i][0]+" "+left_pairs[i][1]+"\n")
			
	    for j in range(len(right_pairs)-1, -1, -1):
		tmp.write(" "+right_pairs[j][0]+" "+right_pairs[j][1]+"\n")
	
        # Finally add the first point of the left pairs again to close the boundary
            tmp.write(" "+left_pairs[0][0]+" "+left_pairs[0][1]+"\n")
	
	tmp.close()
	
	# Now feed into v.in.ascii and also run v.centroids to make a centroid for the polygon
	grass.run_command('v.in.ascii',input=tmp_coords, output=tmp_vect, format="standard", 
				quiet=True, overwrite=True)
	grass.run_command('v.centroids', input=tmp_vect, output=out_vect, quiet=True, overwrite=True)
	grass.message("Polygon vector: %s has been created" % (out_vect))
	grass.message("Cleaning up tmp files %s,%s" %(str(tmp), str(tmp_vect)))
	grass.run_command('g.remove',type='vect', name=tmp_vect, flags="f")
	os.unlink(tmp_coords)	


def main():
	in_sdf = options['input']
	out_vect = options['output']

	if not os.path.isfile(in_sdf):
		grass.fatal(_("Input sdf: %s not found") % in_sdf)
		sys.exit(0)

        left_pairs, right_pairs = read_sdf(in_sdf)
        create_water_surface(left_pairs, right_pairs, out_vect)

        cleanup()
	
if __name__ == "__main__":
	options, flags = grass.parser()
	sys.exit(main())
