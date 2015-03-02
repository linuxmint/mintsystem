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

log("mintSystem started")

try:
    # Read configuration
    sys.path.append('/usr/lib/linuxmint/common')
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
    config.write()


    # Exit if disabled
    if (config['global']['enabled'] == "False"):
        log("Disabled - Exited")
        sys.exit(0)

    adjustment_directory = "/etc/linuxmint/adjustments/"

    # Perform file execution adjustments
    for filename in os.listdir(adjustment_directory):
        basename, extension = os.path.splitext(filename)
        if extension == ".execute":
            full_path = adjustment_directory + "/" + filename
            os.system(full_path)
            log("%s executed" % full_path)

    # Perform file overwriting adjustments
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
            if (commands.getoutput("grep DISTRIB_ID /etc/linuxmint/info").strip() != ""):
                lsbfile.writelines(commands.getoutput("grep DISTRIB_ID /etc/linuxmint/info") + "\n")
            else:
                lsbfile.writelines("DISTRIB_ID=LinuxMint\n")
            lsbfile.writelines("DISTRIB_" + commands.getoutput("grep \"RELEASE=\" /etc/linuxmint/info") + "\n")
            lsbfile.writelines("DISTRIB_" + commands.getoutput("grep CODENAME /etc/linuxmint/info") + "\n")
            lsbfile.writelines("DISTRIB_" + commands.getoutput("grep DESCRIPTION /etc/linuxmint/info") + "\n")
            lsbfile.close()
            log("/etc/lsb-release overwritten")

    # Restore /etc/issue and /etc/issue.net
    if (config['restore']['etc-issue'] == "True"):
        issue = commands.getoutput("grep DESCRIPTION /etc/linuxmint/info").replace("DESCRIPTION=", "").replace("\"", "")
        if os.path.exists("/etc/issue"):
            issuefile = open("/etc/issue", "w")
            issuefile.writelines(issue + " \\n \\l\n")
            issuefile.close()
            log("/etc/issue overwritten")
        if os.path.exists("/etc/issue.net"):
            issuefile = open("/etc/issue.net", "w")
            issuefile.writelines(issue)
            issuefile.close()
            log("/etc/issue.net overwritten")

    # Perform menu adjustments
    for filename in os.listdir(adjustment_directory):
        basename, extension = os.path.splitext(filename)
        if extension == ".menu":
            filehandle = open(adjustment_directory + "/" + filename)
            for line in filehandle:
                line = line.strip()
                line_items = line.split()
                if len(line_items) > 0:
                    if line_items[0] == "hide":
                        if len(line_items) == 2:
                            action, desktop_file = line.split()
                            if os.path.exists(desktop_file):
                                os.system("grep -q -F 'NoDisplay=true' %s || echo '\nNoDisplay=true' >> %s" % (desktop_file, desktop_file))
                                log("%s hidden" % desktop_file)
                    elif line_items[0] == "categories":
                        if len(line_items) == 3:
                            action, desktop_file, categories = line.split()
                            if os.path.exists(desktop_file):
                                categories = categories.strip()
                                os.system("sed -i -e 's/Categories=.*/Categories=%s/g' %s" % (categories, desktop_file))
                                log("%s re-categorized" % desktop_file)
                    elif line_items[0] == "rename":
                        if len(line_items) == 3:
                            action, desktop_file, names_file = line.split()
                            names_file = names_file.strip()
                            if os.path.exists(desktop_file) and os.path.exists(names_file):
                                # remove all existing names, generic names, comments
                                os.system("sed -i -e '/^Name/d' -e '/^GenericName/d' -e '/^Comment/d' \"%s\"" % desktop_file)
                                # add provided ones
                                os.system("cat \"%s\" >> \"%s\"" % (names_file, desktop_file))
                                log("%s renamed" % desktop_file)
            filehandle.close()

except Exception, detail:
    print detail
    log(detail)

log("mintSystem stopped")
logfile.close()
