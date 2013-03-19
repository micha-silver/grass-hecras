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
#% description: Creates a HEC RAS formatted ascii text file of a river system and cross sections from GRASS vector maps 
#% keywords: vector
#% keywords: elevation profile
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
#% key: elevation
#% type: string
#% description: Name of input elevation raster for making cross section profiles
#% required: yes
#%end
#%option
#% key: stations
#% type: string
#% description: Name of input river stations point vector (from v.xsections output)
#% required: yes
#%end
#%option
#% key: output
#% type: string
#% description: Name of output HEC RAS geometry file
#% required: yes
#%end

import sys
import os
import math
import datetime
import grass.script as grass

def cleanup():
	grass.message("Finished")

def output_headers(river, xsections, outfile):
	""" 
	Prepare the output sdf file, and add header section
	"""
	# Start header section
	ver=grass.read_command('g.version')
	dt=str(datetime.date.today())

	outfile.write("# RAS geometry file create on: "+dt+"\n")
	outfile.write("# exported from GRASS GIS version: "+ver+"\n\n")
	outfile.write("BEGIN HEADER:\n")
	proj=grass.read_command('g.proj',flags="g")
	d=grass.parse_key_val(proj)
	if d['units'] == "metres":
		units="METRIC"
	elif d['units'] == "feet":
		units="US CUSTOMARY"
	else:
		units=""

	outfile.write(" UNITS: "+ units + "\n")
	outfile.write(" DTM TYPE: GRID\n")
	outfile.write(" STREAM LAYER: "+ river +"\n")
	info = grass.read_command('v.info', map=river, flags="t")
	d = grass.parse_key_val(info)
	num_reaches=d['lines']
	outfile.write(" NUMBER OF REACHES: "+ num_reaches +"\n")
	

	outfile.write(" CROSS-SECTION LAYER: "+ xsections +"\n")
	info = grass.read_command('v.info', map=xsections, flags="t")
	d=grass.parse_key_val(info)
	num_xsects=d['lines']
	outfile.write(" NUMBER OF CROSS-SECTIONS: "+ num_xsects +"\n")

	info = grass.read_command('v.info', map=river, flags="g")
	d=grass.parse_key_val(info)
	xmin=d['west']
	xmax=d['east']
	ymin=d['south']
	ymax=d['north']
	outfile.write(" BEGIN SPATIALEXTENT: \n")
	outfile.write("   Xmin: "+ xmin +"\n")
	outfile.write("   Xmax: "+ xmax +"\n")
	outfile.write("   Ymin: "+ ymin +"\n")
	outfile.write("   Ymax: "+ ymax +"\n")	
	outfile.write(" END SPATIALEXTENT: \n")

	outfile.write("END HEADER:\n\n")

def output_centerline(river, stations, outfile):
	""" 
	Output the river network, including centerline for each reach
	and coordinates for all stations along each reach
	"""
	# Begin with the list of reach cats
	reach_cats=grass.read_command('v.category', input=river, option="print").strip().split("\n")

	outfile.write("BEGIN STREAM NETWORK:\n")
	# Now get pairs of endpoints from the river vector, one pair for each reach
	for i in range(len(reach_cats)):
		where_cond="reach_id="+str(reach_cats[i])
		select=grass.read_command('v.db.select',map=stations, separator=" ", where=where_cond, flags="c")
		s=select.strip().split("\n")
		first,last = 0,len(s)-1
		pt=s[first].split()
		pi,x,y=pt[0],pt[1],pt[2]
		outfile.write(" ENDPOINT: "+x+","+y+", ,"+pi+"\n")
		pt=s[last].split()
		pi,x,y=pt[0],pt[1],pt[2]
		outfile.write(" ENDPOINT: "+x+","+y+", ,"+pi+"\n")

	outfile.write("END STREAM NETWORK:\n\n")


def output_xsections(xsects, outfile):
	""" 
	"""
	outfile.write("BEGIN CROSS-SECTIONS:\n")

	outfile.write("END CROSS-SECTIONS:\n\n")


def main():
	river = options['river']
	stations = options['stations']
	xsections = options['xsections']
	elev = options['elevation']
	output = options['output']
	
	# do input maps exist in CURRENT mapset?
	mapset = grass.gisenv()['MAPSET']
	if not grass.find_file(river, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % river)
	if not grass.find_file(stations, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % stations)
	if not grass.find_file(xsections, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % xsections)
	if not grass.find_file(elev, element = 'raster', mapset = mapset)['file']:
		grass.fatal(_("Raster map <%s> not found in current mapset") % elev)

	# The work starts here
	if ".sdf" == output.lower()[-4]:
		sdf=output
	else:
		sdf=output+".sdf"

	sdf_file=open(sdf, 'w')

	output_headers(river, xsections, sdf_file)	
	output_centerline(river, stations, sdf_file)
	output_xsections(xsections, sdf_file)

	sdf_file.close()
	cleanup()
	return 0

if __name__ == "__main__":
	options, flags = grass.parser()
	sys.exit(main())
