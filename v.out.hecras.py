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
#% key: stations
#% type: string
#% description: Name of input river stations point vector (from v.xsections output)
#% required: yes
#%end
#%option
#% key: elevation
#% type: string
#% description: Name of input elevation raster for making cross section profiles
#% required: yes
#%end
#%option
#% key: resolution
#% type: integer
#% description: Resolution along the cross sections for getting elevation points (if not given, the elevation raster resolution will be used)
#% required: no
#%end
#%option
#% key: output
#% type: string
#% description: Name of output HEC RAS geometry file (without .sdf extension)
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
	outfile.write(" CROSS-SECTION LAYER: "+ xsections +"\n")
	
	# write out the extents
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

	# write out how many reaches and cross sections
	info = grass.read_command('v.info', map=river, flags="t")
	d = grass.parse_key_val(info)
	num_reaches=d['lines']
	outfile.write(" NUMBER OF REACHES: "+ num_reaches +"\n")
	

	info = grass.read_command('v.info', map=xsections, flags="t")
	d=grass.parse_key_val(info)
	num_xsects=d['lines']
	outfile.write(" NUMBER OF CROSS-SECTIONS: "+ num_xsects +"\n")

	outfile.write("END HEADER:\n\n")


def output_centerline(river, stations, outfile):
	""" 
	Output the river network, including centerline for each reach
	and coordinates for all stations along each reach
	"""

	# Begin with the list of reach cats
	rc=grass.read_command('v.category', input=river, type="line", option="print")
	reach_cats=rc.strip().split("\n")
	
	outfile.write("BEGIN STREAM NETWORK:\n")
	# Now get points from the river vector, one pair for each reach
	for i in range(len(reach_cats)):
		where_cond="cat="+str(reach_cats[i])
		riv=grass.read_command('v.db.select',map=river, separator=" ", 
				columns="cat,start_x,end_x,start_y,end_y", where=where_cond, flags="c")
		r_pts=riv.strip().split(" ")
		pi,x1,y1,x2,y2 = r_pts[0],r_pts[1],r_pts[2],r_pts[3],r_pts[4]
		# Give the start point a point id of "cat"1, and the endpoint a n id of "cat"2
		pi1 = pi+"1"
		pi2 = pi+"2"
		outfile.write(" ENDPOINT: "+x1+","+y1+", ,"+pi1+"\n")
		outfile.write(" ENDPOINT: "+x2+","+y2+", ,"+pi2+"\n")

	# Loop thru the reach_cats again, and output a REACH: section for each reach, 
	# with all points for that reach
	for i in range(len(reach_cats)):
		outfile.write(" REACH:\n")
		outfile.write("   STREAM ID: %s\n" % river)
		reach_id=str(reach_cats[i])
		outfile.write("   REACH ID: %s\n" % reach_id)
		# Get the FROM POINT and TO POINT ids just like above
		where_cond="cat="+str(reach_cats[i])
		riv=grass.read_command('v.db.select',map=river, separator=" ", 
				columns="cat,start_x,end_x,start_y,end_y", where=where_cond, flags="c")
		r_pts=riv.strip().split(" ")
		pi,x1,y1,x2,y2 = r_pts[0],r_pts[1],r_pts[2],r_pts[3],r_pts[4]
		# Give the start point a point id of "cat"1, and the endpoint a n id of "cat"2
		pi1 = pi+"1"
		pi2 = pi+"2"
		outfile.write("   FROM POINT: %s\n" % pi1)
		outfile.write("   TO POINT: %s\n" % pi2)

		# Now the actual points along centerline
		outfile.write("   CENTERLINE:\n")
		# loop thru the stations point vector to get each station's x,y and id
		reach_cond="reach_id="+reach_cats[i]
		p=grass.pipe_command('v.db.select', map=stations, where=reach_cond, quiet=True, flags="c")
		st_list=[]
		for line in p.stdout:
			st=line.strip().split('|')
			s,x,y = st[0], st[1], st[2]
			st_list.append([s,x,y])

		p.stdout.close()
		p.wait()
		# Now write out all station points to the CENTERLINE section
		for i in range(len(st_list)):
			outfile.write("    "+st_list[i][1]+","+st_list[i][2]+", ,"+st_list[i][0]+"\n")

		outfile.write(" END:\n")

	# Close STREAM NETWORK section
	outfile.write("END STREAM NETWORK:\n\n")

def output_xsections(xsects, outfile, elev, res, river):
	"""
	Create the cross section profiles by first making a points vector from the cross sections
	loop thru the section_ids and use v.out.ascii to get the points for each cross section.
	Feed these points into r.profile to get lists of the coords and elevation at each spot along the xsection,
	and output these to the CROSS-SECTION paragraph
	"""

	# Prepare tmp vector maps to hold the points from the cross sections
	proc=os.getpid()
	xsect_pts="tmp_xsect_pts_"+str(proc)
	xsect_pts2="tmp_xsect_pts2_"+str(proc)
	grass.run_command('v.to.points', input=xsects, output=xsect_pts, flags="v", quiet=True)
	# and double check region settings
	grass.run_command('g.region', vect=xsects, quiet=True)
	
	# v.to.points returns all points on the same cross section with the same cat value
	# Dump the points with v.out.ascii and pipe directly back into v.in.ascii 
	# to get a new points file with unique cat for each point, 
	# but careful to keep the columns "reach" and "station"
	p1=grass.pipe_command('v.out.ascii', input=xsect_pts, type="point", 
			columns="reach,station_id", dp=0, separator=",")
	p2=grass.start_command('v.in.ascii', input="-", stdin=p1.stdout, output=xsect_pts2, separator=",",
			columns="x INTEGER, y INTEGER, oldcat INTEGER, reach INTEGER, station_id INTEGER", quiet=True)
	p1.stdout.close()
	p1.wait()
	p2.wait()
	if (p1.returncode != 0) or (p2.returncode != 0):
		sys.exit(1)
	
	grass.run_command('v.db.dropcolumn', map=xsect_pts2, column="oldcat")

	# Now we can begin writing out CROSS-SECTIONS to file
	outfile.write("\n")
	outfile.write("BEGIN CROSS-SECTIONS:\n")
	
	# Get the list of station ids with the reaches
	st=grass.pipe_command('v.db.select', map=xsect_pts2, columns="reach,station_id", flags="c", quiet=True)
	station_ids=[]
	for line in st.stdout:	
		station = line.rstrip('\n').split("|")
		r,s = station[0], station[1]
		station_ids.append([r,s])

	st.stdout.close()
	st.wait()
	
	# Now loop thru those stations to create the CUTLINE and SURFACE section
	for i in range(len(station_ids)):
		station_id = station_ids[i][1].strip('\n')
		reach = station_ids[i][0].rstrip('\n')
		process_msg="Processing reach: "+reach+" at station id: "+station_id
		#grass.message(process_msg)
		outfile.write(" CROSS-SECTION:\n")
		outfile.write("   STREAM ID: %s\n" % river)
		outfile.write("   REACH ID: %s\n" % reach)
		outfile.write("   STATION: %s\n" % station_id)
			
		# get point coords from this reach/station and print out CUTLINE: section
		# Save this output also for next SURFACE: section
		station_cond="station_id="+station_id
		p=grass.pipe_command('v.out.ascii', input=xsect_pts2, columns="reach,station_id", 
			where=station_cond ,separator=",", layer=1, quiet=True)
		station_pts=[]
		for line in p.stdout:
			st = line.rstrip('\n').split(',')
			station_pts.append(st)

		p.stdout.close()
		p.wait()

		outfile.write("   CUTLINE:\n")
		for j in range(len(station_pts)):
			x,y = station_pts[j][0], station_pts[j][1]
			outfile.write("     "+x+","+y+"\n")  

		# Now run the points thru r.profile, and get the elevations
		# and print elevations to SURFACE LINE: section
		outfile.write("   SURFACE LINE:\n")
		profile_pts=[]
		for k in range(len(station_pts)):
			x,y = station_pts[k][0], station_pts[k][1]
			profile_pts.append([x,y])
			
		pp=grass.pipe_command('r.profile', input=elev, profile=profile_pts, res=res, flags="g", quiet=True)
		for line in pp.stdout:
			l=line.rstrip('\n').split(" ")
			# The r.profile output has x,y in first two columns and elev in 4th column
			outfile.write("     "+l[0]+","+l[1]+","+l[3]+"\n")
		pp.stdout.close()
		pp.wait()
		
		# CLose this CROSS-SECTION paragraph
		outfile.write(" END:\n\n")

	outfile.write("END CROSS-SECTIONS:\n\n")

	# remove temp points file
	tmps=xsect_pts,xsect_pts2
	grass.run_command('g.mremove', vect=tmps, quiet=True, flags="f")


def main():
	river = options['river']
	stations = options['stations']
	xsections = options['xsections']
	elev = options['elevation']
	output = options['output']
	res = options['resolution']
	
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
	if not res:
		# No resolution given, use the resolution of the elevation raster
		info = grass.read_command('r.info', map=elev, flags="g")
		d=grass.parse_key_val(info)
		res=d['ewres']  # Assume ewres=nsres
	# Be sure region is set to river layer
	grass.run_command('g.region', vect=river, quiet=True)

	# Prepare output file
	if ".sdf" == output.lower()[-4]:
		sdf=output
	else:
		sdf=output+".sdf"
	
	sdf_file=open(sdf, 'w')

	# The work starts here
	output_headers(river, xsections, sdf_file)	
	grass.message("Headers written to %s" % sdf)
	output_centerline(river, stations, sdf_file)
	grass.message("River network written to %s" % sdf)
	output_xsections(xsections, sdf_file, elev, res, river)
	grass.message("Cross sections written to %s" % sdf)

	sdf_file.close()
	cleanup()
	return 0

if __name__ == "__main__":
	options, flags = grass.parser()
	sys.exit(main())
