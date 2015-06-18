#!/usr/bin/env python
#
############################################################################
#
# MODULE:	   v.in.hecras
# AUTHOR(S):Micha Silver 
#	    micha@arava.co.il  Arava Drainage Authority	
# PURPOSE:  Reads an *.sdf file in HEC-RAS text format 
#	The input file must include BANK POSITION: rows 
#	as part of the HEC-RAS output
# COPYRIGHT:    This program is free software under the GNU General Public
#		License (>=v2). Read the file COPYING that comes with GRASS
#		for details.
#
# REVISIONS:	June 2015, adapted for GRASS 7.0
#############################################################################

#%module
#% description: Read a sdf formatted ascii text file, output from a HEC-RAS analysis and create a point vector of bank points 
#% keywords: HEC-RAS
#% keywords: banks
#%end
#% option
#% key: input
#% type:string
#% description: Name of input HEC-RAS file (from run of simulation), with BANK POSITIONS
#% required: yes
#%end
#%option
#% key: output
#% type: string
#% description: Name of output GRASS point vector
#% required: yes
#%end

import sys
import os
import grass.script as grass

def cleanup():
    grass.message("Finished")


def read_sdf(input):
    """
    Read the input SDF, scanning for lines with "CUT LINE"
    Read the coords from the next three lines, and save to list
    Read the bank postions from the following line and save to another list
    Return both lists
    """
    with open(input, 'r') as sdf:
        lines = sdf.readlines()
        sdf.close()
		
    cutline_pts=[]
    bank_dist=[]
    for i in range(len(lines)):
        if 'CUT LINE' in lines[i]:
            coords1 = lines[i+1].strip().replace(" ", "").split(",")
            coords2 = lines[i+2].strip().replace(" ", "").split(",")
            coords3 = lines[i+3].strip().replace(" ", "").split(",")
            pt1 = [coords1[0],coords1[1]]
            pt2 = [coords2[0],coords2[1]]
            pt3 = [coords3[0],coords3[1]]
            cutline_pts.append([pt1,pt2,pt3])
            if 'BANK POSITIONS' in lines[i+4]:
                coords=lines[i+4].strip().split(':')[1]
                bank_pt = coords.split(',')
                bank_dist.append(bank_pt)
            else:
                grass.fatal("No BANK POSITIONS data in sdf file")
                return None
                    
    return cutline_pts, bank_dist


def create_banks(cutline_pts, bank_dist, out_vect):
    """
    Use the two lists of cutline point locations, and distances along those cutlines
    To create points for the left and right bank locations
    """
    cl_cnt = len(cutline_pts)
    bk_cnt = len(bank_dist)
    if (cl_cnt <> bk_cnt):
        grass.fatal("Number of cutlines: %s, not equal to number of bank points: %s" % (cl_cnt, bk_cnt))
        sys.exit(0)

    tmp_coords = grass.tempfile()
    tmp_banks = grass.tempfile()
    proc=os.getpid()
    # tmp_line holds a temporary line vector for each single cutline
    # The locations in bank_dist will be used to create new points as bank points
    # and added to the bank points vector, tmp_pts
    tmp_line = "cutline_tmp_"+str(proc)
    tmp_pts = "bankpt_tmp_"+str(proc)

    grass.run_command('v.edit', map=out_vect, tool='create', type_='point',overwrite=True)

    for i in range(len(cutline_pts)):
        with open(tmp_coords,'w') as tmp:
            tmp.write("VERTI:\n")
            tmp.write("L 3 1\n")
            tmp.write(" "+cutline_pts[i][0][0]+" "+cutline_pts[i][0][1]+"\n" )
            tmp.write(" "+cutline_pts[i][1][0]+" "+cutline_pts[i][1][1]+"\n" )
            tmp.write(" "+cutline_pts[i][2][0]+" "+cutline_pts[i][2][1]+"\n" )
            tmp.write(" 1 1\n")
        tmp.close()
        # Create one cutline (from 3 points)
        grass.run_command('v.in.ascii',input_=tmp_coords, output=tmp_line, overwrite=True, format_='standard', quiet=True)

        # Now find the point locations at the bank dist distances along that line
        # Use the same list index, i, to get the points for the current cutline
        # and multiply fraction by 100 to create % distance along cutline
        with open(tmp_banks, 'w') as tmp:
            rule_line1 = "P 1 1\n"
            tmp.write("P 1 1 %s" % str(float(bank_dist[i][0])*100) + "%\n")
            tmp.write("P 2 1 %s" % str(float(bank_dist[i][1])*100) + "%\n")
        tmp.close()
        # Create a new point vector, and append to existing bank points
        grass.run_command('v.segment', input_=tmp_line, output=tmp_pts, rules=tmp_banks, overwrite=True, quiet=True)
        grass.run_command('v.patch', input_=tmp_pts, output=out_vect, overwrite=True, flags='a', quiet=True )

    # Cleanup
    os.unlink(tmp_coords)
    os.unlink(tmp_banks)
    grass.run_command('g.remove', type_='vect', name=tmp_line, flags='f')
    grass.run_command('g.remove', type_='vect', name=tmp_pts, flags='f')


def main():
    in_sdf = options['input']
    out_vect = options['output']
    if not os.path.isfile(in_sdf):
        grass.fatal(_("Input sdf: %s not found") % in_sdf)
	sys.exit(0)

    cutline_pts, bank_dist = read_sdf(in_sdf)
    if cutline_pts is None:
        sys.exit(0)

    create_banks(cutline_pts, bank_dist, out_vect)

    cleanup()
	
if __name__ == "__main__":
	options, flags = grass.parser()
	sys.exit(main())
