#!/usr/bin/python3

import os

FLAG_DIR = "/var/lib/linuxmint/mintsystem"
FLAG_FILE = os.path.join(FLAG_DIR, "set-apt-recommends.flag")
RECOMMENDS_FILE = "/etc/apt/apt.conf.d/00recommends"
SYNAPTIC_FILE = "/etc/apt/apt.conf.d/99synaptic"

if not os.path.exists(FLAG_DIR):
    os.system("mkdir -p %s" % FLAG_DIR)

if not os.path.exists(FLAG_FILE):
    with open(FLAG_FILE, "w") as flag_file:
        # Remove the APT Recommends file
        if os.path.exists(RECOMMENDS_FILE):
            os.system("rm %s" % RECOMMENDS_FILE)
            flag_file.write("Removed %s\n" % RECOMMENDS_FILE)
        # Reset the synaptic configuration for recommends
        if os.path.exists(SYNAPTIC_FILE):
            outlines = []
            with open(SYNAPTIC_FILE, "r") as synaptic_file:
                for line in synaptic_file:
                    if "APT::Install-Recommends" in line:
                        line = line.replace("false", "true")
                    outlines.append(line)
            with open(SYNAPTIC_FILE, "w") as synaptic_file:
                for line in outlines:
                    synaptic_file.write(line)
            flag_file.write("Set configuration in %s\n" % SYNAPTIC_FILE)
        # Restart packagekit
        os.system("service packagekit restart")
