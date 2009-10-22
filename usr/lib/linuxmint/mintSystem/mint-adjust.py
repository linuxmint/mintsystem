#!/usr/bin/python

import os
import commands
import sys
from time import strftime

# Prepare the log file
global logfile
logfile = open("/var/log/mintsystem.log", "w")

def log (string):
	logfile.writelines("%s - %s\n" % (strftime("%Y-%m-%d %H:%M:%S"), string))
	logfile.flush()

log("minSystem started")

try:
	# Read configuration
	from configobj import ConfigObj
	config = ConfigObj("/etc/linuxmint/mintSystem.conf")
	
	# Default values
	if ('global' not in config):
		config['global'] = {}
	if ('enabled' not in config['global']):
		config['global']['enabled'] = "True"
	if ('restore' not in config):
		config['restore'] = {}
	if ('lsb-release' not in config['restore']):
		config['restore']['lsb-release'] = "True"
	if ('etc-issue' not in config['restore']):
		config['restore']['etc-issue'] = "True"	
	if ('ctrl-alt-backspace' not in config['restore']):
		config['restore']['ctrl-alt-backspace'] = "True"		
	if ('update-grub' not in config['restore']):
		config['restore']['update-grub'] = "True"	
	config.write()


	# Exit if disabled
	if (config['global']['enabled'] == "False"):
		log("Disabled - Exited")
		sys.exit(0)

	# Perform file overwriting adjustments
	adjustment_directory = "/etc/linuxmint/adjustments/"
	array_preserves = []
	if os.path.exists(adjustment_directory):
		for filename in os.listdir(adjustment_directory):
    			basename, extension = os.path.splitext(filename)
			if extension == ".preserve":
				filehandle = open(adjustment_directory + "/" + filename)
				for line in filehandle:
					line = line.strip()
					array_preserves.append(line)
				filehandle.close()
	overwrites = {}
	if os.path.exists(adjustment_directory):
		for filename in sorted(os.listdir(adjustment_directory)):
    			basename, extension = os.path.splitext(filename)
			if extension == ".overwrite":
				filehandle = open(adjustment_directory + "/" + filename)
				for line in filehandle:
					line = line.strip()					
					line_items = line.split()
					if len(line_items) == 2:
						source, destination = line.split()
						if destination not in array_preserves:							
							overwrites[destination] = source
				filehandle.close()

	for key in overwrites.keys():
		source = overwrites[key]
		destination = key
		if os.path.exists(source):
			if not "*" in destination:
				# Simple destination, do a cp
				if os.path.exists(destination):
					os.system("cp " + source + " " + destination)
					log(destination + " overwritten with " + source)
			else:
				# Wildcard destination, find all possible matching destinations
				matching_destinations = commands.getoutput("find " + destination)
				matching_destinations = matching_destinations.split("\n")
				for matching_destination in matching_destinations:					
					matching_destination = matching_destination.strip()
					if os.path.exists(matching_destination):
						os.system("cp " + source + " " + matching_destination)
						log(matching_destination + " overwritten with " + source)		

	# Restore LSB information
	if (config['restore']['lsb-release'] == "True"):
		if os.path.exists("/etc/lsb-release"):
			lsbfile = open("/etc/lsb-release", "w")			
			lsbfile.writelines("DISTRIB_ID=LinuxMint\n")
			lsbfile.writelines("DISTRIB_" + commands.getoutput("cat /etc/linuxmint/info | grep RELEASE") + "\n")
			lsbfile.writelines("DISTRIB_" + commands.getoutput("cat /etc/linuxmint/info | grep CODENAME") + "\n")
			lsbfile.writelines("DISTRIB_" + commands.getoutput("cat /etc/linuxmint/info | grep DESCRIPTION") + "\n")
			lsbfile.close()
			log("/etc/lsb-release overwritten")

	# Restore /etc/issue and /etc/issue.net
	if (config['restore']['etc-issue'] == "True"):
		issue = commands.getoutput("cat /etc/linuxmint/info | grep DESCRIPTION").replace("DESCRIPTION=", "").replace("\"", "")
		if os.path.exists("/etc/issue"):
			issuefile = open("/etc/issue", "w")					
			issuefile.writelines(issue + " \\n \\l")			
			issuefile.close()
			log("/etc/issue overwritten")
		if os.path.exists("/etc/issue.net"):
			issuefile = open("/etc/issue.net", "w")					
			issuefile.writelines(issue)			
			issuefile.close()
			log("/etc/issue.net overwritten")			

	# Restore CTRL+ALT+BACKSPACE
	if (config['restore']['ctrl-alt-backspace'] == "True"):
		os.system("setxkbmap -option terminate:ctrl_alt_bksp")
		log("X11 shortcut CTRL+ALT+BACKSPACE restored")
	
	# Restore execution permission on /usr/sbin/update-grub
	if (config['restore']['update-grub'] == "True"):
		if os.path.exists("/usr/sbin/update-grub"):
			os.system("chmod a+rx /usr/sbin/update-grub")
			log("Execution permissions restored on /usr/sbin/update-grub")

except Exception, detail:
	print detail
	log(detail)

log("minSystem stopped")
logfile.close()

