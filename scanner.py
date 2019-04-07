
#
# Scan a set of Ada files and look for circular dependencies
#
# Ada filenames are of the format <PackageName>.1.ada, <PackageName>.2.ada, <PackageName>.ads or <PackageName>.adb
# PackageNames with '.' in them are currently assumed to by sub-packages
# Subpackages get their 'with' clauses added to the parent package
# 
# TODO: For each package check each 'with'ed package recursively to see if it returns to the original package

import re                       # For regular expression usage

from collections import deque   # Use a deque for with stack
from pathlib import Path        # To allow easy access to folders and files

# Constants
IGNORE = [r".git", r".vscode"]  # List of directories to ignore
STANDARD_PACKAGES = [r"ada", r"system", r"text_io"]

# Regular expression used, as they should be cached and there aren't many they haven't been compiled
# Putting them here will make it easy to create compiled versions if needed
RE_ADA_FILE = r"\.?[12]?\.ad[abs]$"             # Regular expression to match Ada files
RE_ROOT_PACKAGE_NAME = r"^(\w+)[\.\-]?.*"       # Regular expression to extract the root package name from a filename
RE_WITH_PACKAGE_NAME = r"^\s*with\s+([\w\.*]+)" # Regular expression to extract a with'd package name from a source file
RE_WITH_CHILD_PACKAGE = r"\."                   # Regular expression to detect the with of a child package

# Global Data
withData = {}                   # With data for each package read, dictionary keyed on package name containing a list of withs
withStack = deque()             # TODO: Should the with stack be a separate class?
circularStacks = []             # List of circular stacks

def parseDir(cwd):
    """Parse a directory of files

    Will recursively enter any sub-directories found unless they match one of the IGNORE directories.
    Each Ada file in the directory will be examined and an entry made/updated in the withData for the package
    related to the file. Each with'd package will be added to the list except if it matches the source package
    or is one of the standard library packages.
    All package names are lower cased.

    Global Data affected: withData

    Input: cwd => Path object pointing to the directory to parse
    """

    print("Parsing directory {}".format(cwd.name))

    for f in cwd.iterdir():
        if f.is_dir():
            # If we get a directory then recurse into it, unless it is to be ignored
            if not f.name in IGNORE:
                parseDir(f)
        else:
            # Got a file, but is it an Ada file?
            if re.search(RE_ADA_FILE, f.suffix):
                # Got an Ada file so extract the package name from the filename
                package = re.search(RE_ROOT_PACKAGE_NAME, f.stem).group(1).lower()
                print("Parsing file {} Package = ".format(f.name), package)

                # Set the package with list empty then override if a list already exists
                packageWithList = []
                if package in withData:
                    # Already in the list so add any new withs
                    packageWithList = withData[package]
                else:
                    # Add new list to withData
                    withData[package] = packageWithList
                # Parse the file to get all the withs
                with open(f) as file:
                    for line in file:
                        match = re.search(RE_WITH_PACKAGE_NAME, line)
                        if match:
                            withMatch = match.group(1).lower()
                            # If this looks like with'ing a child package then output a warning
                            if re.search(RE_WITH_CHILD_PACKAGE, withMatch):
                                print("+++ Possible child package included in {} ({})".format(f.name, withMatch))
                            # Only add the package if it is not already in the list and 
                            # it does not match the source package name or any of the standard Ada packages
                            if packageWithList.count(withMatch) == 0 \
                                and withMatch != package \
                                and not re.search(RE_ROOT_PACKAGE_NAME, withMatch).group(1) in STANDARD_PACKAGES:
                                packageWithList.append(withMatch)

def parseWiths(start):
    """
    Parse a packages with list recursively

    GLobal data affected: withStack

    Input: start the package to start from
    """

    # Only process the start point if it has withs
    if start in withData:
        for withs in withData[start]:
            if withStack.count(withs) > 0:
                # This with package is already in the stack, copy the current stack and add it to the list of circular stacks
                newStack = deque(withStack)
                # Add the current one to make it circular
                newStack.append(withs)
                circularStacks.append(newStack)
                # Don't descend into this with as that way leads to madness
            else:
                # New with so add it to the stack and recurse into it, 
                # when it returns remove with from stack as it has been processed
                withStack.append(withs)
                parseWiths(withs)
                withStack.pop()

#
# Main program when run
#
if __name__ == "__main__":
    cwd = Path.cwd()
    print("Starting directory = {}".format(cwd))

    # Build the dictionary of packages and what they include
    parseDir(cwd)

    # Check the with lists to see if it includes any child packages
    for key in withData:
        for data in withData[key]:
            if re.search(RE_WITH_CHILD_PACKAGE, data):
                print("Child package found {} includes {}".format(key, data))

    for key in withData:
        print("{} => {}".format(key, withData[key]))

    # Iterate over each package, using it as the start point looking for a loop
    for key in withData:
        print("Checking {} for circularity".format(key))
        # Clear the stack and start it with the first package
        withStack.clear()
        withStack.append(key)
        parseWiths(key)

    # Tidy up the circularity list
    # Remove stacks that don't start and end with the same package
    # They contain an inner circularity that will be picked up in other stacks
    for cs in circularStacks:
        start = cs.popleft()
        cs.appendleft(start)
        if cs.count(start) < 2:
            circularStacks.remove(cs)

    # Remove stacks that are the same circularity
    # This is done by removing the end point (which is the same as the start), 
    # the remaining items them form the sequence of withs without returning to a start point. 
    # By rotating these and comparing with other stacks identical loops can be removed
    # At the end replace the end item to keep the circularity
    for cs in circularStacks:
        cs.pop()
    for cs in circularStacks:
        for ts in circularStacks:
            if cs == ts:
                continue
            else:
                for i in range(1, len(ts)+1):
                    ts.rotate(1)
                    if cs == ts:
                        circularStacks.remove(ts)
                        break
    for cs in circularStacks:
        start = cs.popleft()
        cs.appendleft(start)
        cs.append(start)



    for cs in circularStacks:
        print("Circular Withs {}".format(cs))