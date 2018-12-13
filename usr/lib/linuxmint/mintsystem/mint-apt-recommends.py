#!/usr/bin/python3

import sys

import apt


class RecommendsFinder:

    def __init__(self, _cache, _package, recursive):
        self.cache = _cache
        self.found_missing_recommends = []
        self.already_looked_at = []

        if recursive:
            level = 1
        else:
            level = 0
        self.get_recommends(_package, level)

    def get_recommends(self, pkg, level):
        if pkg.name not in self.already_looked_at:
            self.already_looked_at.append(pkg.name)
            if pkg.is_installed:
                pkg = pkg.installed
            else:
                pkg = pkg.candidate
            # go through the recommends
            for recommend in pkg.recommends:
                for base_rec in recommend.or_dependencies:
                    rec_name = base_rec.name
                    if (rec_name not in self.found_missing_recommends and
                        rec_name in self.cache and
                        not self.cache[rec_name].is_installed
                        ):
                        self.found_missing_recommends.append(rec_name)
                        if level > 0:
                            self.get_recommends(self.cache[rec_name], level + 1)
            # go through the dependencies
            for dep in pkg.dependencies:
                for base_dep in dep.or_dependencies:
                    dep_name = base_dep.name
                    if dep_name in self.cache:
                        dep_pkg = self.cache[dep_name]
                        # if the package is installed but the dep isn't, ignore it
                        # (it means another dep honored the dependency)
                        if pkg.is_installed and not dep_pkg.is_installed:
                            continue
                        if level > 0:
                            self.get_recommends(dep_pkg, level + 1)

if __name__ == "__main__":
    package_name = next((item for item in sys.argv[1:] if not item.startswith("-")), None)
    if len(sys.argv) in (2, 3) and package_name:
        cache = apt.Cache()
        if package_name in cache.keys():
            package = cache[package_name]
            finder = RecommendsFinder(cache, package,
                [x for x in ["--recursive","-R"] if x in sys.argv[1:]])
            missing_recommends = sorted(finder.found_missing_recommends)
            if len(missing_recommends) > 0:
                if len(missing_recommends) > 1:
                    msg = "The following missing recommended packages were found for"
                else:
                    msg = "The following missing recommended package was found for"
                print(msg + " %s:\n" % package_name)
                for missing in missing_recommends:
                    print("    %s" % missing)
                if len(missing_recommends) > 1:
                    msg = "You can install them by running the following command:"
                else:
                    msg = "You can install it by running the following command:"
                print("\n%s\n\n    apt install %s\n" % (msg, " ".join(missing_recommends)))
            else:
                print("No missing recommended packages were found for %s" % package_name)
        else:
            print("E: Unable to locate package %s" % package_name, file=sys.stderr)
            sys.exit(1)
    else:
        print("""\
Usage:  apt recommends [options] <package>

List not installed recommended packages for the given package.

Options:
        -R | --recursive
            Also list missing recommended packages of dependent or
            recommended packages.""")
        sys.exit(1)
