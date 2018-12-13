#!/usr/bin/python3
import fnmatch
import os
import shutil
import subprocess
import sys
import time
from glob import glob
from tempfile import gettempdir

import apt


def strtobool(val):
    val = val.lower()
    if val in ('y', 'yes'):
        return True
    elif val in ('n', 'no'):
        return False
    else:
        raise ValueError("Invalid response value %r" % (val,))

def get_user_input():
    while True:
        try:
            retval = strtobool(input())
            print("")
            return retval
        except ValueError:
            print('Invalid response. Try again [y/n]: ', end='')
        except KeyboardInterrupt:
            pass

def print_e(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def download_package(package, show_success_message=True):
    try:
        package.candidate.fetch_binary()
        if show_success_message:
            print('\nThe package "%s" was downloaded to the current directory as\n  %s' %
                  (package.name, os.path.basename(package.candidate.filename)))
    except Exception as e:
        print_e(f"An error occured while downloading the package:\n{e}")
        return False
    return True

def get_package(pkg_name):
    # parse =version declaration
    if "=" in pkg_name:
        (pkg_name, pkg_version) = pkg_name.split("=", 1)
        pkg_release = None
    # parse /release declaration (only if no version specified)
    elif "/" in pkg_name:
        (pkg_name, pkg_release) = pkg_name.split("/", 1)
        pkg_version = None
    else:
        pkg_version = None
        pkg_release = None

    # check if pkg_name exists
    if pkg_name in cache.keys():
        pkg = cache[pkg_name]
    else:
        print_e(f"E: Unable to locate package {pkg_name}")
        return False

    # get package data
    _candidate = None
    if pkg_release or pkg_version:
        match_found = False
        for _pkg in pkg.versions:
            if pkg_version:
                if fnmatch.fnmatch(_pkg.version, pkg_version):
                    match_found = True
            else:
                for _origin in _pkg.origins:
                    if fnmatch.fnmatch(_origin.archive, pkg_release):
                        match_found = True
            if match_found:
                _candidate = _pkg
                break
        if not match_found:
            if pkg_release:
                print_e(f'E: Release "{pkg_release}" is unavailable for "{pkg.name}"')
            else:
                print_e(f'E: Version "{pkg_version}" is unavailable for "{pkg.name}"')
            return False
    else:
        _candidate = pkg.candidate
    pkg.candidate = _candidate
    return pkg

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Update the cache first if older than 24h
        try:
            apt.apt_pkg.init_config()
            pkgcache = apt.apt_pkg.config.find_file("Dir::Cache::pkgcache")

            if not os.path.isfile(pkgcache) or \
                time.time() - os.path.getmtime(pkgcache) > 24 * 60 * 60:
                subprocess.call(["/usr/local/bin/apt", "update"])
                print ("")
        except:
            pass

        # Check permissions to download to this folder
        if not os.access(os.getcwd(), os.W_OK | os.X_OK):
            print_e("E: Current folder is not writable")
            sys.exit(1)

        # Load cache
        cache = apt.Cache()

        # Get cwd
        pwd = os.getcwd()

        for package_name_full in sys.argv[1:]:
            # Skip option parameter, we support none
            if package_name_full.startswith("-"):
                continue

            # Get package
            package = get_package(package_name_full)
            if not package:
                continue

            # Check if package is downloadable
            if not package.candidate.downloadable:
                print_e(f'E: No download source available for "{package_name_full}"')
                continue

            # INSTALLED package
            if package.candidate.is_installed:
                # Download installed package as .deb
                download_package(package)
                continue

            # NOT INSTALLED package
            package.mark_install()
            package_list = cache.get_changes()
            if not package_list or len(package_list) == 1:
                # Broken dependencies or only single package:
                # download stand-alone package as .deb instead
                download_package(package)
                continue

            # Check if target file already exists
            archive_name = f"{package.name}_{package.candidate.version}.tar.gz"
            if os.path.exists(archive_name):
                print(f'W: Target archive "{archive_name}" already exists. Overwrite? [y/n]: ', end='')
                response = get_user_input()
                if response == True:
                    os.unlink(archive_name)
                else:
                    continue

            # Download package incl. missing dependencies and compress as .tar.gz
            tmpfolder = None
            while not tmpfolder:
                _tmpfolder = os.path.join(gettempdir(), f"mint-apt-download-{package.name}-{hash(os.times())}")
                if not os.path.exists(_tmpfolder):
                    tmpfolder = _tmpfolder
            os.makedirs(tmpfolder)
            os.chdir(tmpfolder)
            try:
                for _package in package_list:
                    if _package.marked_delete:
                        continue
                    success = download_package(_package, False)
                    if not success:
                        raise ValueError(f"An error occured downloading the package: {_package.name}")
                with open(os.open("install.sh", os.O_CREAT | os.O_WRONLY, 0o775), 'w') as f:
                    f.write("sudo dpkg -i *.deb\n")
                subprocess.run(["tar", "-zcvf", f"{pwd}/{archive_name}"] + glob("*"),
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                print(f"""
All the packages necessary for offline installation of
  {package_name_full}
were downloaded to the current directory into the archive:
  {archive_name}
Extract into a folder and run the extracted install.sh to install.""")
            except subprocess.CalledProcessError as e:
                print_e(f"E: An error occured creating the archive:\n{e.stderr.decode()}")
            except ValueError as e:
                print_e(f"E: {e}")
            # Remove temporary files and folder
            shutil.rmtree(tmpfolder)
        os.chdir(pwd)
    else:
        print("Usage: apt download [package]")
        sys.exit(1)
