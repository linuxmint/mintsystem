#!/usr/bin/python2

import os
import commands
import sys
import time
import datetime
import fileinput
import filecmp

TIMESTAMPS = "/var/log/mintsystem.timestamps"

class MintSystem():
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.logfile = open("/var/log/mintsystem.log", "w")
        self.time_log("mintSystem started")
        self.executed = []
        self.overwritten = []
        self.skipped = []
        self.edited = []
        self.original_timestamps = {}
        self.timestamps = {}
        self.timestamps_changed = False
        self.read_timestamps()

    def time_log (self, string):
        self.log("%s - %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), string))

    def log (self, string):
        self.logfile.writelines("%s\n" % string)

    def quit(self):
        stop_time = datetime.datetime.now()
        self.log ("Execution time: %s" % (stop_time - self.start_time))
        self.logfile.flush()
        self.logfile.close()
        sys.exit(0)

    def read_timestamps(self):
        if os.path.exists(TIMESTAMPS):
            filehandle = open(TIMESTAMPS)
            for line in filehandle:
                line = line.strip()
                line_items = line.split()
                if len(line_items) == 2:
                    self.original_timestamps[line_items[0]] = line_items[1]
                    self.timestamps[line_items[0]] = line_items[1]

    def write_timestamps(self):
        filehandle = open(TIMESTAMPS, "w")
        for filename in sorted(self.timestamps.keys()):
            line = "%s %s\n" % (filename, self.timestamps[filename])
            filehandle.write(line)
        filehandle.close()

    def has_changed(self, filename, collection, description):
        if not os.path.exists(filename):
            return False

        timestamp = os.stat(filename).st_mtime
        if (filename not in self.original_timestamps):
            has_changed = True
        else:
            has_changed = (self.original_timestamps[filename] != str(timestamp))

        if (has_changed):
            collection.append("%s (%s)" % (filename, description))
        else:
            self.skipped.append("%s (%s)" % (filename, description))
        return has_changed

    def update_timestamp(self, filename):
        timestamp = os.stat(filename).st_mtime
        self.timestamps[filename] = timestamp
        self.timestamps_changed = True

    def replace_file(self, source, destination):
        if os.path.exists(source) and os.path.exists(destination):
            if (destination not in self.overwritten) and (destination not in self.skipped):
                if filecmp.cmp(source, destination):
                    self.skipped.append(destination)
                else:
                    self.overwritten.append(destination)
                    os.system("cp " + source + " " + destination)

    def adjust(self):
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
                self.log("Disabled - Exited")
                self.quit()

            adjustment_directory = "/etc/linuxmint/adjustments/"

            # Perform file execution adjustments
            for filename in os.listdir(adjustment_directory):
                basename, extension = os.path.splitext(filename)
                if extension == ".execute":
                    full_path = os.path.join(adjustment_directory, filename)
                    os.system(full_path)
                    self.executed.append(full_path)

            # Perform file overwriting adjustments
            array_preserves = []
            if os.path.exists(adjustment_directory):
                for filename in os.listdir(adjustment_directory):
                    basename, extension = os.path.splitext(filename)
                    if extension == ".preserve":
                        filehandle = open(os.path.join(adjustment_directory, filename))
                        for line in filehandle:
                            line = line.strip()
                            array_preserves.append(line)
                        filehandle.close()

            overwrites = {}
            if os.path.exists(adjustment_directory):
                for filename in sorted(os.listdir(adjustment_directory)):
                    basename, extension = os.path.splitext(filename)
                    if extension == ".overwrite":
                        filehandle = open(os.path.join(adjustment_directory, filename))
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
                        self.replace_file(source, destination)
                    else:
                        # Wildcard destination, find all possible matching destinations
                        matching_destinations = commands.getoutput("find " + destination)
                        matching_destinations = matching_destinations.split("\n")
                        for matching_destination in matching_destinations:
                            matching_destination = matching_destination.strip()
                            self.replace_file(source, matching_destination)
            # Restore LSB information
            if (config['restore']['lsb-release'] == "True"):
                if self.has_changed("/etc/lsb-release", self.overwritten, "lsb"):
                    lsbfile = open("/etc/lsb-release", "w")
                    if (commands.getoutput("grep DISTRIB_ID /etc/linuxmint/info").strip() != ""):
                        lsbfile.writelines(commands.getoutput("grep DISTRIB_ID /etc/linuxmint/info") + "\n")
                    else:
                        lsbfile.writelines("DISTRIB_ID=LinuxMint\n")
                    lsbfile.writelines("DISTRIB_" + commands.getoutput("grep \"RELEASE=\" /etc/linuxmint/info") + "\n")
                    lsbfile.writelines("DISTRIB_" + commands.getoutput("grep CODENAME /etc/linuxmint/info") + "\n")
                    lsbfile.writelines("DISTRIB_" + commands.getoutput("grep DESCRIPTION /etc/linuxmint/info") + "\n")
                    lsbfile.close()
                    self.update_timestamp("/etc/lsb-release")

            # Restore /etc/issue and /etc/issue.net
            if (config['restore']['etc-issue'] == "True"):
                issue = commands.getoutput("grep DESCRIPTION /etc/linuxmint/info").replace("DESCRIPTION=", "").replace("\"", "")
                if self.has_changed("/etc/issue", self.overwritten, "lsb"):
                    issuefile = open("/etc/issue", "w")
                    issuefile.writelines(issue + " \\n \\l\n")
                    issuefile.close()
                    self.update_timestamp("/etc/issue")
                if self.has_changed("/etc/issue.net", self.overwritten, "lsb"):
                    issuefile = open("/etc/issue.net", "w")
                    issuefile.writelines(issue)
                    issuefile.close()
                    self.update_timestamp("/etc/issue.net")

            # Perform menu adjustments
            for filename in os.listdir(adjustment_directory):
                basename, extension = os.path.splitext(filename)
                if extension == ".menu":
                    filehandle = open(os.path.join(adjustment_directory, filename))
                    for line in filehandle:
                        line = line.strip()
                        line_items = line.split()
                        if len(line_items) > 0:
                            if line_items[0] == "hide":
                                if len(line_items) == 2:
                                    action, desktop_file = line.split()
                                    if self.has_changed(desktop_file, self.edited, "hide"):
                                        os.system("grep -q -F 'NoDisplay=true' %s || echo 'NoDisplay=true' >> %s" % (desktop_file, desktop_file))
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "categories":
                                if len(line_items) == 3:
                                    action, desktop_file, categories = line.split()
                                    if self.has_changed(desktop_file, self.edited, "categories"):
                                        categories = categories.strip()
                                        os.system("sed -i -e 's/Categories=.*/Categories=%s/g' %s" % (categories, desktop_file))
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "exec":
                                if len(line_items) >= 3:
                                    action, desktop_file, executable = line.split(' ', 2)
                                    if self.has_changed(desktop_file, self.edited, "exec"):
                                        executable = executable.strip()
                                        found_exec = False
                                        for desktop_line in fileinput.input(desktop_file, inplace=True):
                                            if desktop_line.startswith("Exec=") and not found_exec:
                                                found_exec = True
                                                desktop_line = "Exec=%s" % executable
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "rename":
                                if len(line_items) == 3:
                                    action, desktop_file, names_file = line.split()
                                    names_file = names_file.strip()
                                    if os.path.exists(names_file) and self.has_changed(desktop_file, self.edited, "name"):
                                        # remove all existing names, generic names, comments
                                        os.system("sed -i -e '/^Name/d' -e '/^GenericName/d' -e '/^Comment/d' \"%s\"" % desktop_file)
                                        # add provided ones
                                        os.system("cat \"%s\" >> \"%s\"" % (names_file, desktop_file))
                                        self.update_timestamp(desktop_file)
                    filehandle.close()

            self.log("Executed:")
            for filename in sorted(self.executed):
                self.log("  %s" % filename)

            self.log("Replaced:")
            for filename in sorted(self.overwritten):
                self.log("  %s" % filename)

            self.log("Edited:")
            for filename in sorted(self.edited):
                self.log("  %s" % filename)

            self.log("Skipped:")
            for filename in sorted(self.skipped):
                self.log("  %s" % filename)


            if self.timestamps_changed:
                self.write_timestamps()

        except Exception, detail:
            print detail
            self.log(detail)

mintsystem = MintSystem()
mintsystem.adjust()
mintsystem.quit()

