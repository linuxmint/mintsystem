#!/usr/bin/python3

import os
import sys
import time
import datetime
import fileinput
import filecmp
import configparser
import glob

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

    def time_log(self, string):
        self.log("%s - %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), string))

    def log(self, string):
        self.logfile.writelines("%s\n" % string)

    def quit(self):
        stop_time = datetime.datetime.now()
        self.log("Execution time: %s" % (stop_time - self.start_time))
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
            try:
                config = configparser.RawConfigParser()
                config.read('/etc/linuxmint/mintSystem.conf')
                self.enabled = (config.get('global', 'enabled') == "True")
            except:
                config = configparser.RawConfigParser()
                config.add_section('global')
                config.set('global', 'enabled', 'True')
                config.add_section('restore')
                with open('/etc/linuxmint/mintSystem.conf', 'w') as configfile:
                    config.write(configfile)
                self.enabled = True

            # Exit if disabled
            if not self.enabled:
                self.log("Disabled - Exited")
                self.quit()

            adjustment_directory = "/usr/share/linuxmint/adjustments/"

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
                            if (line):
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
                    if "*" not in destination:
                        self.replace_file(source, destination)
                    else:
                        # Wildcard destination, find all possible matching destinations
                        for matching_destination in glob.glob(destination):
                            self.replace_file(source, matching_destination)

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
                                        os.system("grep -q -F 'NoDisplay=true' %s || echo '\nNoDisplay=true' >> %s" % (desktop_file, desktop_file))
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "show":
                                if len(line_items) == 2:
                                    action, desktop_file = line.split()
                                    if self.has_changed(desktop_file, self.edited, "show"):
                                        os.system("sed -i -e '/^NoDisplay/d' \"%s\"" % desktop_file)
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "categories":
                                if len(line_items) == 3:
                                    action, desktop_file, categories = line.split()
                                    if self.has_changed(desktop_file, self.edited, "categories"):
                                        categories = categories.strip()
                                        os.system("sed -i -e 's/Categories=.*/Categories=%s/g' %s" % (categories, desktop_file))
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "onlyshowin":
                                if len(line_items) == 3:
                                    action, desktop_file, onlyshowins = line.split()
                                    if self.has_changed(desktop_file, self.edited, "onlyshowin"):
                                        onlyshowins = onlyshowins.strip()
                                        os.system("sed -i -e 's/OnlyShowIn=.*/OnlyShowIn=%s/g' %s" % (onlyshowins, desktop_file))
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
                                            print (desktop_line.strip())
                                        self.update_timestamp(desktop_file)
                            elif line_items[0] == "rename":
                                if len(line_items) == 3:
                                    action, desktop_file, names_file = line.split()
                                    names_file = names_file.strip()
                                    if os.path.exists(names_file) and os.path.exists(desktop_file) and (self.has_changed(desktop_file, self.edited, "name") or self.has_changed(names_file, self.edited, "name")):
                                        # remove all existing names, generic names, comments
                                        os.system("sed -i -e '/^Name/d' -e '/^GenericName/d' -e '/^Comment/d' \"%s\"" % desktop_file)
                                        # add provided ones
                                        os.system("cat \"%s\" >> \"%s\"" % (names_file, desktop_file))
                                        self.update_timestamp(desktop_file)
                                        self.update_timestamp(names_file)
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

        except Exception as detail:
            print (detail)
            self.log(detail)

mintsystem = MintSystem()
mintsystem.adjust()
mintsystem.quit()
