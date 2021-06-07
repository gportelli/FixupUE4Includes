#!/usr/bin/python

import os, sys
import re

project_path = "C:/Projects/MyAwesomeProject"
engine_path  = "C:/Program Files/Epic Games/UE_4.26/Engine"

response = input("""This script will analyze all project source files (includng plugins), searching for #include directives to fix:
 - old one-file #include paths will be replaced by long paths, as requested by the 4.24 new default build settings
 - include style for engine includes (<,>) and project includes (\",\") will be enforced

The paths used for the analysis are:
 Engine: """ + engine_path + """
 Project: """ + project_path + """

If you want to change these paths, edit the source code of this script.

Start with the analysis? (y/n)""")

if(response != "y") : exit(0)

def ExtractIncludePaths(basepath, localpath="", computed_map={}, excluded_folders=[]):	
	dirs = os.listdir( basepath + "/" + localpath)
	for file in dirs:
		currlocalpath = localpath + "/" + file
		currpath = basepath + "/" + currlocalpath
		
		if(os.path.isdir(currpath)) : 
			if(not ("" + file) in excluded_folders) : ExtractIncludePaths(basepath, currlocalpath, computed_map, excluded_folders)
		else:
			(name, ext) = os.path.splitext(file)
			
			if(ext==".h"):
				computed_map[file] = currlocalpath				

	return computed_map

def PrintIncludePaths(include_paths):
	for key in include_paths:
		print(key + " -> " + include_paths[key])

def MinimizePath(path):
	if(path.startswith('/')): path = path[1:] # strip first slash
	
	searches = ["Public", "Private", "Classes", "Source"]

	backup = path
	for search in searches:
		path = backup.split("/")
		found = False
		while True: # removing all path folders until Public/ (included)
			tmp = path[0]
			path.remove(tmp)

			if(tmp == search): 
				found = True
				break

			if(len(path) == 0) : break

		if(found) : break

	return "/".join(path) if len(path) > 0 else backup

def FixInclude(include, source_local_path, project_includes = {}, engine_includes={}, engine_plugins_includes={}):
	include_path = ""

	x = re.search("\"(.+)\"", include)
	if(not x is None):
		include_path = x.groups()[0]
	else:
		x = re.search("<(.+)>", include)
		if(not x is None):
			include_path = x.groups()[0]

	if(include_path == "") : return include

	# take the last part of the include path
	tmp = include_path.split("/")
	include_filename = tmp[len(tmp)-1]

	complete_path = ""
	include_style = ['"', '"']

	if(include_filename in project_includes): # project
		complete_path = project_includes[include_filename]
	elif(include_filename in engine_includes): # engine
		complete_path = engine_includes[include_filename]
		include_style = ['<', '>']
	elif(include_filename in engine_plugins_includes): #engine plugins
		complete_path = engine_plugins_includes[include_filename]
		include_style = ['<', '>']

	if(complete_path != ""):
		if(complete_path.find(include_path) != -1):
			return '#include ' + include_style[0] + MinimizePath(complete_path) + include_style[1] + '\n'
	
	return include

def FixFile(basepath, localpath, filename, project_includes = {}, engine_includes={}, engine_plugins_includes={}):
	print("Fixing: " + basepath + "/" + localpath + "...")

	fixed_content = ""

	with open(basepath + "/" + localpath, "r") as f:
		lines = f.readlines()

		for line in lines:
			x = re.search("^\s*#include ", line)

			if(not x is None) :
				fixed_content = fixed_content + FixInclude(line, localpath, project_includes, engine_includes, engine_plugins_includes)
			else:
				fixed_content = fixed_content + line

	f = open(basepath + "/" + localpath, "w")
	f.write(fixed_content)
	f.close()

	#exit(0)

def FixFiles(basepath, localpath="", project_includes = {}, engine_includes={}, engine_plugins_includes={}):
	dirs = os.listdir( basepath + "/" + localpath)
	for file in dirs:
		currlocalpath = localpath + "/" + file  if localpath != "" else file
		currpath = basepath + "/" + currlocalpath
		
		if(os.path.isdir(currpath)) : 			
			FixFiles(basepath, currlocalpath, project_includes, engine_includes, engine_plugins_includes)
		else:
			(name, ext) = os.path.splitext(file)
			
			if((ext==".h" or ext==".cpp") and file != "RzChromaSDKTypes.h"): #avoid RzChromaSDKTypes.h cause it contains non utf8 characters
				FixFile(basepath, currlocalpath, file, project_includes, engine_includes, engine_plugins_includes)

project_include_paths = {}
ExtractIncludePaths(project_path + "/Source", "", project_include_paths)

engine_include_paths = {}
ExtractIncludePaths(engine_path + "/Source", "", engine_include_paths, ["ThirdParty", "Private"])

engine_plugins_include_paths = {}
ExtractIncludePaths(engine_path + "/Plugins", "", engine_plugins_include_paths, ["ThirdParty", "Private"]) 

FixFiles(project_path + "/Source", "", project_include_paths, engine_include_paths, engine_plugins_include_paths)

if not os.path.exists(project_path + "/Plugins"):
	os.makedirs(project_path + "/Plugins")
dirs = os.listdir( project_path + "/Plugins")
for file in dirs:
	print(file)
	
	src_path = project_path + "/Plugins/" + file + "/Source"

	if(os.path.isdir(src_path)) :
		plugin_include_paths = {}
		ExtractIncludePaths(src_path, "", plugin_include_paths)

		FixFiles(src_path, "", plugin_include_paths, engine_include_paths, engine_plugins_include_paths)
	else:
		print(project_path + "/Plugins/" + file + " is not a directory or doesn't contain any /Source subfolder, skipping" +
			" (if it's not a binary plugin folder maybe you don't need it anymore?)")
