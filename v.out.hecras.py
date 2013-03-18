#!/usr/bin/env python
#
############################################################################
#
# MODULE:       v.out.hecras
# AUTHOR(S):   	Micha Silver 
#				micha@arava.co.il  Arava Drainage Authority	
# PURPOSE:      Creates a river system schematic vector map and a cross sections vector map 
#				from an input river network
# COPYRIGHT: 	This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################

#%module
#% description: Creates a HEC RAS formatted ascii text file
#% of a river system and cross sections from GRASS vector maps 
#% keywords: vector
#% keywords: HEC RAS
#% keywords: cross sections
#%end
#% option
#% key: river
#% type:string
#% description: Name of input of river schematic line vector (from v.xsections output)
#% required: yes
#%end
#%option
#% key: xsections
#% type: string
#% description: Name of input cross sections line vector (from v.xsections output)
#% required: yes
#%end
#%option
#% key: stations
#% type: string
#% description: Name of input river stations point vector (from v.xsections output)
#% required: yes
#%end
#%option
#% key: sdf
#% type: string
#% description: Name of output HEC RAS geometry file
#% required: yes
#%end

import sys
import os
import math
import grass.script as grass

def cleanup():
	grass.message("Finished")

def output_start_end_points(invect, outfile):
	""" 
	"""


def output_centerline(invect, outfile):
	""" 
	"""

def output_xsections(invect, outfile):
	""" 
	"""

def main():
	river = options['input']
	stations = options['stations']
	xsections = options['xsections']
	sdf = options['sdf']
	
	# do input maps exist in CURRENT mapset?
	mapset = grass.gisenv()['MAPSET']
	if not grass.find_file(river, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % river)
	if not grass.find_file(stations, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % stations)
	if not grass.find_file(xsections, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % xsections)

	# The work starts here
	output_headers(sdf)	
	output_start_end_points(river, sdf)
	output_centerline(stations, sdf)
	output_xsections(xsections, sdf)

	cleanup()
	return 0

if __name__ == "__main__":
	options, flags = grass.parser()
	sys.exit(main())
