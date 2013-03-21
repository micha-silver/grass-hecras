#!/usr/bin/env python
#
############################################################################
#
# MODULE:       v.xsections
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
#% description: Creates a river system schematic vector map and a cross sections vector map from a river network
#% keywords: vector
#% keywords: HEC RAS
#% keywords: cross sections
#%end
#%flag
#%  key: s
#%  description: Perform smoothing on input map with v.generalize (uses "snakes" algorithm)
#%end
#% option
#% key: input 
#% description: Name of input (river) line vector
#% required: yes
#%end
#%option
#% key: xsections
#% type: string
#% description: Name of output cross sections line vector
#% required: yes
#%end
#%option
#% key: stations
#% type: string
#% description: Name of output river stations schematic point vector
#% required: yes
#%end
#%option
#% key: spacing
#% type: integer
#% description: spacing between cross sections
#% answer: 100
#% required: yes
#%end
#%option
#% key: width
#% type: integer
#% description: Width of each cross section
#% answer: 200
#% required: yes
#%end
#%option
#% key: intersects
#% type: string
#% description: Name of output point vector for cross section intersections
#% required: yes
#%end
#%option
#% key: smooth_river
#% type: string
#% description: The smoothed output vector name (only when -s flag is used)
#% required: no
#%end
#%option
#% key: layer
#% type: integer
#% description: The layer in smoothed output vector 
#% required: yes
#% answer: 1
#%end
#%option
#% key: threshold
#% type: integer
#% description: The threshold for the smoothed vector name (only when -s flag is used)
#% required: no
#%end

import sys
import os
import math
import grass.script as grass

def cleanup():
	grass.message("Finished")

def create_stations_schematic(invect, outvect, spacing, cats):
	""" 
	Loop thru all river reaches, and for each reach
	begin at the upstream start of the reach, 
	and create a series of points at each "spacing" interval. 
	Put these points into an ASCII file, formatted for v.segment
	and run v.segment to create a line vector of stations along the original river
	"""
	# Create temp file for Points
	tmp_stations = grass.tempfile()
	tmp = open(tmp_stations,'w')
	# Keep track of how many total river stations were marked
	station_cnt=0
	for c in cats:
		reach_len=float(cats[c])
		# Begins at the upstream start of each river reach, and work downstream
		# Each iteration creates a line segment "spacing" meters downstream of the previous
		# Use the same line id for each segment in the reach
		station=0
		pt=0
		# Loop until the remaining length < reach_len - spacing
		while station<=reach_len:
			# concatenate (as strings) a point iterator with the line cat value to create a point cat 
			pt+=1
			pt_id=c + "%03d" % pt
			st1=str(math.floor(station))
			tmp.write("P "+pt_id+" "+c+" "+st1+"\n")
			station += spacing
			station_cnt+=1
	
	tmp.close()
	
	grass.run_command('v.segment',input=invect, output=outvect, file=tmp_stations, overwrite=True, quiet=True)
	os.unlink(tmp_stations)

	# Add coordinates to each station
	grass.run_command('v.db.addtable', map=outvect, quiet=True)
	grass.run_command('v.db.addcolumn', map=outvect, columns="x DOUBLE PRECISION, y DOUBLE PRECISION", quiet=True)
	grass.run_command('v.to.db', map=outvect, option="coor", columns="x,y", quiet=True)
	
	# Also get the reach id for each station
	# The point ids are created from line (reach) cats + three more digits.
	# Dividing point id by 1000 returns original line id
	grass.run_command('v.db.addcolumn', map=outvect, columns="reach_id INTEGER", quiet=True)
	grass.run_command('v.to.db', map=outvect, option="query", columns="reach_id", qcolumn="cat/1000", quiet=True)
	
	return station_cnt


def create_cross_sections(invect, outvect, stations, spacing, width, cats):
	""" 
	Loop thru all river reaches, and for each reach 
	begin at the start of each reach, and create a series of point pairs, at each "spacing" interval
	and at "width/2" offset from the original river. 
	Put these point pairs into a standard format ASCII vector line file,
	then run v.in.ascii to create cross section line segments from each pair
	"""
	# create temp file for point pairs
	tmp_pairs = grass.tempfile()
	#print tmp_pairs
	tmp = open(tmp_pairs, 'w')
	# Also create a temp map for the point pairs 
	# (this is needed as an interim step to making the cross section line segments)
	proc=os.getpid()
	tmp_pairs_map="tmp_pairs_" + str(proc) 
	# Each point will be placed at 1/2 width distance to the left and right of river
	half_width= int(width)/2
	pi = 1
	for c in cats:
		l=float(cats[c])
		station=0
		while station <= l:
			stat=str(math.floor(station))
			# write tthree points with same cat, at right and left of river line
			# and one point one the line
			tmp.write("P "+str(pi)+" "+c+" "+stat+ " " + str(-half_width)+"\n")
			tmp.write("P "+str(pi)+" "+c+" "+stat+ " " + "0"+"\n")
			tmp.write("P "+str(pi)+" "+c+" "+stat+ " " + str(half_width)+"\n")
			station += spacing
			pi +=1

	tmp.close()
	grass.run_command('v.segment',input=invect, output=tmp_pairs_map, file=tmp_pairs, overwrite=True, quiet=True)
	
	# Now dump the point pairs - selected by cats - into a new ASCII format file to create the lines
	# First add a DB connection
	grass.run_command('v.db.addtable', map=tmp_pairs_map, quiet=True)
	# Now get a list of the cats from the tmp_pairs 
	xsect_cats=[] 
	cats=grass.read_command('v.db.select', map=tmp_pairs_map, columns="cat", quiet=True)
	for c in cats.split():
		xsect_cats.append(c)
	#print xsect_cats
	
	# Loop thru the cats and extract X-Y for each pair of points, 
	# and put into a standard format ascii file as Line segments
	coord_list=[]
	tmp_xsects=grass.tempfile()
	#print tmp_xsects
	tmp=open(tmp_xsects,'w')
	xsect_cnt=0
	for i in range(len(xsect_cats)):
		c=xsect_cats[i]
		coords=grass.read_command('v.out.ascii', input=tmp_pairs_map, separator=",", quiet=True, where="cat="+c).split('\n')
		coord_list.append(coords)
		# coord_list is a list of strings, each string has two space separated entries. 
		# Each entry is a comma separated coordinate pair and the cat value for those points 
		# both points have the same cat
	
	for i in range(len(coord_list)):
		p1, p2, p3 = coord_list[i][0], coord_list[i][1], coord_list[i][2]
		x1, y1 = p1.split(',')[0], p1.split(',')[1]
		x2, y2 = p2.split(',')[0], p2.split(',')[1]
		x3, y3 = p3.split(',')[0], p3.split(',')[1]
		cat = p1.split(',')[2]
		# Write out a standard format ASCII file of line segments
		# each segment with exactly two nodes
		tmp.write("L 3 1\n")
		tmp.write(" "+x1+" "+y1+"\n")
		tmp.write(" "+x2+" "+y2+"\n")
		tmp.write(" "+x3+" "+y3+"\n")
		tmp.write(" 1 "+cat+"\n")
		xsect_cnt += 1

	tmp.close()
	grass.run_command('v.in.ascii',input=tmp_xsects, output=outvect, format="standard", 
				quiet=True, overwrite=True, flags='n')
	# Use v.distance to upload values from the stations point vector to the new cross sections line vector
	tmp_lines_map="tmp_lines_"+str(proc)
	grass.run_command('v.db.addtable', map=outvect, columns="reach INTEGER, station_id INTEGER", quiet=True)
	vdist_params='from='+stations+', to='+outvect+', output='+tmp_lines_map
	grass.run_command('v.distance', _from=outvect, to=stations, 
				upload="cat,to_attr", to_column="reach_id", column="station_id,reach", quiet=True) 

	os.unlink(tmp_pairs)
	grass.run_command('g.remove',vect=tmp_pairs_map, flags="f")
	grass.run_command('g.remove',vect=tmp_lines_map, flags="f")

	return xsect_cnt

def create_xsection_intersects(invect, outvect):
	""" 
		Run v.clean on the cross section vector to find all intersection points
		using the error=... option with tool=break to create a point vector 
	"""
	proc=os.getpid()
	dummy="dummy_out_" + str(proc)

	grass.run_command('v.clean', input=invect, output=dummy, error=outvect, tool="break", quiet=True, overwrite=True)
	info = grass.read_command('v.info', map=outvect, flags="t")
	d=grass.parse_key_val(info)
	grass.run_command('g.remove',vect=dummy, flags="f")
	
	return int(d['points'])


def create_river_network(invect, outvect):
	"""
	Prepare the input river network vector by:
	possibly smoothing the line, and
	adding several columns to the vector attribute table.
	THe added columns include start and end points for output to HEC-RAS
	"""	

	thresh = options['threshold']
	layer = options['layer']
	
	if (flags['s']):
		# Perform smoothing of the input vector	
		grass.run_command('v.generalize', input=invect, output=outvect, _method='snakes',
			 threshold=thresh, overwrite=True, quiet=True)
	else:
		 grass.run_command('g.copy', vect='%s,%s' % (invect,outvect))
		 
	
	# Add a reach length column to the river vector
	# First check if column exists
	columns_exist = grass.vector_columns(outvect, int(layer)).keys()
	if not "reach_len" in columns_exist:
		grass.run_command('v.db.addcolumn', map=outvect, columns="reach_len DOUBLE PRECISION", quiet=True)
	# Also add columns for start and end point of each reach
	if not "start_x" in columns_exist:
		grass.run_command('v.db.addcolumn', map=outvect, columns="start_x DOUBLE PRECISION", quiet=True)
	if not "start_y" in columns_exist:
		grass.run_command('v.db.addcolumn', map=outvect, columns="start_y DOUBLE PRECISION", quiet=True)
	if not "end_x" in columns_exist:
		grass.run_command('v.db.addcolumn', map=outvect, columns="end_x DOUBLE PRECISION", quiet=True)
	if not "end_y" in columns_exist:
		grass.run_command('v.db.addcolumn', map=outvect, columns="end_y DOUBLE PRECISION", quiet=True)
	# Now update those columns
	grass.run_command('v.to.db',map=outvect, option="length", columns="reach_len", quiet=True)
	grass.run_command('v.to.db',map=outvect, option="start", columns="start_x,start_y",quiet=True)
	grass.run_command('v.to.db',map=outvect, option="end", columns="end_x,end_y", quiet=True)
	d=grass.read_command('v.db.select',map=outvect, separator="=", columns="cat,reach_len", flags="c")

	# Initialize dict of reach categories with their lengths
	# Each key in the dictionary is the cat of a river reach
	# each value is the length of that reach
	reach_cats=grass.parse_key_val(d, val_type=float)

	return reach_cats

	


def main():
	river = options['input']
	stations = options['stations']
	xsections = options['xsections']
	width = options['width']
	spacing = float(options['spacing'])
	smooth_river = options['smooth_river']
	thresh = options['threshold']
	layer = options['layer']
	intersects = options['intersects']

	# does input rivers map exist in CURRENT mapset?
	mapset = grass.gisenv()['MAPSET']
	if not grass.find_file(river, element = 'vector', mapset = mapset)['file']:
		grass.fatal(_("Vector map <%s> not found in current mapset") % river)

	if (flags['s']):
		if not smooth_river or not thresh:
			grass.fatal( "Missing smooth options. Check smooth_river and threshold" )

	# The work starts here
	reach_cats = create_river_network(river, smooth_river)
	# Call functions to create new vectors
	station_count = create_stations_schematic(smooth_river, stations, spacing, reach_cats)
	grass.message("Created %d stations" % station_count)
	xsection_count = create_cross_sections(smooth_river, xsections, stations, spacing, width, reach_cats)
	grass.message("Created %d cross sections" % xsection_count)
	intersect_cnt=create_xsection_intersects(xsections, intersects)
	grass.message("Found %d intersection points" % intersect_cnt)

	cleanup()
	return 0

if __name__ == "__main__":
	options, flags = grass.parser()
	sys.exit(main())
