
#
# Scan a set of Ada files and look for circular dependencies
#
# Ada filenames are of the format <PackageName>.1.ada, <PackageName>.2.ada, 
# <PackageName>.ads, <PackageName>.adb or <PackageName>.ada
# PackageNames with '.' in them are currently assumed to by sub-packages
# Subpackages get their 'with' clauses added to the parent package
#
# There is no list of standard packages to ignore as they should not exists in the files
# being searched and will therefore not appear in the list of files that need to be checked
# 
# TODO: Handling of child packages, should they be elaborated as part of the main package?

import re                       # For regular expression usage

from collections import deque   # Use a deque for with stack
from pathlib import Path        # To allow easy access to folders and files

# Constants
IGNORE = [r".git", r".vscode"]  # List of directories to ignore

# Regular expression used, as they should be cached and there aren't many they haven't been compiled
# Putting them here will make it easy to create compiled versions if needed
RE_ADA_FILE = r"\.?[12]?\.ad[abs]$"                 # Regular expression to match Ada files
RE_ROOT_PACKAGE_NAME = r"^(\w+)[\.\-]?"             # Regular expression to extract the root package name from a filename
RE_FULL_PACKAGE_NAME = r"^(.*?)\.?[12]?\.ad[abs]$"  # Regular expression to get a full package name from the filename
RE_WITH_PACKAGE_NAME = r"^\s*with\s+([\w\.*]+)"     # Regular expression to extract a with'd package name from a source file
RE_WITH_CHILD_PACKAGE = r"\."                       # Regular expression to detect the with of a child package
RE_SEPARATE = r"^\s*separate\s*\("                  # Regular expression to detect a separate statement

# Global Data
withData = {}                   # With data for each package read, dictionary keyed on package name containing a list of withs
withStack = deque()             # deque to hold the current state of with'd units as they are processed
circularStacks = []             # List of circular stacks


def parseFile(f):
    """
    Extract a list of withs from a file, also indicate if it is a sub-unit

    File is read and any with lines processed to extract the with'd package
    Any separate (); statements are detected and flag the file as a sub-unit
    All package names are lower cased

    Global Data: None
    Input: f => Path object pointing to the file to parse
    Output: tuple (withsList, isSubUnit)
        withsList => List of with'd packages
        isSubUnit => Boolean True if this file is a sub-unit i.e. has a separate statement, otherwise False
    """

    withList = []
    isSubUnit = False

    with open(f) as file:
        for line in file:
            match = re.search(RE_WITH_PACKAGE_NAME, line.lower())
            if match:
                withMatch = match.group(1)
                # If this looks like with'ing a child package then output a warning
                if re.search(RE_WITH_CHILD_PACKAGE, withMatch):
                    print("+++ Possible child package included in {} ({})".format(f.name, withMatch))
                # Only add the package if it is not already in the list
                if withList.count(withMatch) == 0:
                    withList.append(withMatch)
                
            # Look for a separate statement
            if re.search(RE_SEPARATE, line.lower()):
                isSubUnit = True
                break       # IF we get to a separate statement then the contex has finished

    return withList, isSubUnit


def parseAdaFile(f):
    """
    Extract information about the file

    The Ada file will be examined and an entry made/updated in the withData for the package related to the file
    Each with'd package will be added to the list except if it matches the source package or is laready in the list
    All package names are lower cased

    Global Data: withData
    Input: f => Path object pointing to the file to parse
    Returns: None

    """
    # Got an Ada file so extract the package name from the filename
    package = re.search(RE_FULL_PACKAGE_NAME, f.name.lower()).group(1)
    print("--- Parsing file {} Package = {}".format(f.name, package))

    withsList, isSubUnit = parseFile(f)
    if isSubUnit:
        # For subunits add the withs to the parent package
        package = re.search(RE_ROOT_PACKAGE_NAME, f.stem.lower()).group(1)
    # Remove with of itself (just in case)
    if package in withsList:
        withsList.remove(package)

    if package in withData:
        # Already in the list so add any new withs
        for w in withsList:
            if not w in withData[package]:
                withData[package].append(w)
    else:
        # Add new list to withData
        withData[package] = withsList


def parseDir(cwd):
    """
    Parse a directory of files

    Will recursively enter any sub-directories found unless they match one of the IGNORE directories
    Each Ada file in the directory will be processed
    All package names are lower cased

    Global Data: None
    Input: cwd => Path object pointing to the directory to parse
    Returns: None
    """

    print("--- Parsing directory {}".format(cwd.name))

    for f in cwd.iterdir():
        if f.is_dir():
            # If we get a directory then recurse into it, unless it is to be ignored
            if not f.name.lower() in IGNORE:
                parseDir(f)
        else:
            # Got a file, but is it an Ada file?
            if re.search(RE_ADA_FILE, f.suffix.lower()):
                parseAdaFile(f)
               

def parseWiths(start):
    """
    Parse a packages with list recursively

    Global Data: withStack
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
    print("--- Starting directory = {}".format(cwd))

    # Build the dictionary of packages and what they include
    parseDir(cwd)

    # Check the with lists to see if it includes any child packages
    for key in withData:
        for data in withData[key]:
            if re.search(RE_WITH_CHILD_PACKAGE, data):
                print("+++ Child package found {} includes {}".format(key, data))

    for key in withData:
        print("--- {} => {}".format(key, withData[key]))

    # Iterate over each package, using it as the start point looking for a loop
    for key in withData:
        print("--- Checking {} for circularity".format(key))
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
        print("--- Circular Withs {}".format(list(cs)))

            
