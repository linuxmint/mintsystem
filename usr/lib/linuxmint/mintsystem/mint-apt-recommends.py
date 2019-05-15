#!/usr/bin/python3

import apt
import sys
import subprocess

class RecommendsFinder:

    def __init__(self, cache, package):
        self.cache = cache
        self.package = package
        self.missing_recommends = []
        output = subprocess.getoutput("aptitude search '?broken-reverse-recommends(?installed)' | awk {'print $2;'}")
        for line in output.split("\n"):
            line = line.strip()
            self.missing_recommends.append(line)

        self.found_missing_recommends = []
        self.already_looked_at = []

        self.get_recommends(self.package, 1)

    def get_recommends(self, package, level):
        if package.name not in self.already_looked_at:

            # Uncomment this to debug ;)
            # prefix = ""
            # for i in range(level):
            #     prefix = " %s" % prefix
            # print (prefix, package.name)

            self.already_looked_at.append(package.name)
            if package.is_installed:
                pkg = package.installed
            else:
                pkg = package.candidate
            # go through the recommends
            for recommend in pkg.recommends:
                for base_rec in recommend.or_dependencies:
                    if base_rec.name in self.missing_recommends and base_rec.name not in self.found_missing_recommends:
                        self.found_missing_recommends.append(base_rec.name)
                        if base_rec.name in self.cache:
                            rec_pkg = self.cache[base_rec.name]
                            self.get_recommends(rec_pkg, level + 1)
            # go through the dependencies
            for dep in pkg.dependencies:
                for base_dep in dep.or_dependencies:
                    dep_name = base_dep.name
                    if dep_name in self.cache:
                        dep_pkg = self.cache[dep_name]
                        # if the package is installed but the dep isn't, ignore it (it means another dep honored the dependency)
                        if package.is_installed and not dep_pkg.is_installed:
                            continue
                        # If the dependency is missing but is part of an OR dependency, ignore it
                        # (it means another package honors the OR dependency)
                        if not package.is_installed and len(dep.or_dependencies) > 1:
                            continue
                        self.get_recommends(dep_pkg, level + 1)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        package_name = sys.argv[1]
        cache = apt.Cache()
        if package_name in cache:
            package = cache[package_name]
            finder = RecommendsFinder(cache, package)
            missing_recommends = sorted(finder.found_missing_recommends)
            print("")
            if len(missing_recommends) > 0:
                print("The following missing recommended packages were found for %s:\n" % package_name)
                for missing in missing_recommends:
                    print("    %s" % missing)
                print("")
                print("You can install them by typing the following command:")
                print("")
                print("    apt install --install-recommends %s" % " ".join(missing_recommends))
            else:
                print("No missing recommended packages were found for %s" % package_name)
            print("")
        else:
            print("Error: package %s not found in APT cache!" % package_name)
            sys.exit(1)

    else:
        print("Usage:  apt recommends [package]")
        sys.exit(1)
