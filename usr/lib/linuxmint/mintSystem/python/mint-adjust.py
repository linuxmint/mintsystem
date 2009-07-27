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

def overwriteSplash (source, dest):
	resource = "/usr/lib/linuxmint/mintSystem/service/resource/" + source
	editionResource = "/usr/share/linuxmint/splash/" + source
	if os.path.exists(dest):
			if os.path.exists(editionResource):
				splash = editionResource			
			elif os.path.exists(resource):
				splash = resource
			os.system("cp " + splash + " " + dest)
			log(dest + " overwritten with " + splash)

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
	if ('splash-screens' not in config['restore']):
		config['restore']['splash-screens'] = "True"	
	if ('ctrl-alt-backspace' not in config['restore']):
		config['restore']['ctrl-alt-backspace'] = "True"		
	if ('update-grub' not in config['restore']):
		config['restore']['update-grub'] = "True"	
	config.write()


	# Exit if disabled
	if (config['global']['enabled'] == "False"):
		log("Disabled - Exited")
		sys.exit(0)

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

	# Restore Splash screens
	if (config['restore']['splash-screens'] == "True"):
		overwriteSplash("openoffice.bmp", "/usr/lib/openoffice/program/openintro_ubuntu_sun.bmp")
		overwriteSplash("openoffice_about.bmp", "/usr/lib/openoffice/program/openabout_ubuntu_sun.bmp")
		overwriteSplash("gimp.png", "/usr/share/gimp/2.0/images/gimp-splash.png")				

	# Restore CTRL+ALT+BACKSPACE
	if (config['restore']['ctrl-alt-backspace'] == "True"):
		dontzap = commands.getoutput("cat /etc/X11/xorg.conf | grep -i dontzap | grep -i false | wc -l")
		if dontzap == "0":
			if os.path.exists("/usr/bin/dontzap"):
				os.system("/usr/bin/dontzap --disable")
				log("X11 shortcut CTRL+ALT+BACKSPACE restored")
	
	# Restore execution permission on /usr/sbin/update-grub
	if (config['restore']['update-grub'] == "True"):
		if os.path.exists("/usr/sbin/update-grub"):
			os.system("chmod a+rx /usr/sbin/update-grub")
			log("Execution permissions restored on /usr/sbin/update-grub")

except Exception, detail:
	print detail

log("minSystem stopped")
logfile.close()
