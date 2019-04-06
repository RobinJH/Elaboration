
#
# Scan a set of Ada files and look for circular dependencies
#
# Ada filenames are of the format <PackageName>.1.ada and <PackageName>.2.ada
# PackageNames with '.' in them are currently assumed to by sub-packages
# Subpackages get their 'with' clauses added to the parent package
# 
# TODO: For each package check each 'with'ed package recursively to see if it returns to the original package

import re                       # For regular expression usage

from collections import deque   # Use a deque for with stack
from pathlib import Path        # To allow easy access to folders and files
    
withData = {}                   # With data for each package read, dictionary keyed on package name containing a list of withs
withStack = deque()             # TODO: Should the with stack be a separate class?

def parseDir(cwd):
    """Parse a directory of files

    Will recursivly enter any sub-directories found

    Input: cwd => Path object pointing to the directory to parse
    """ 
    for f in cwd.iterdir():
        if f.is_dir():
            # If we get a directory then recurse into it
            print("Parsing directory {}".format(f.name))
            parseDir(f)
        else:
            # Got a file, but is it an Ada file?
            if re.search(r"\.ada$", f.name):
                # Got an Ada file so extract the package name from the filename
                package = re.search(r"^(\w+)\..*", f.name).group(1)
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
                        match = re.search(r"^\s*with\s+([\w\.*]+)", line)
                        if match:
                            withMatch = match.group(1)
                            if packageWithList.count(withMatch) == 0:
                                packageWithList.append(withMatch)
                file.close()


cwd = Path.cwd()
print("Starting directory = {}".format(cwd))

parseDir(cwd)

# Check the with lists to see if it includes any child packages
for key in withData:
    for data in withData[key]:
        if re.search(r"\.", data):
            print("Child package found {} includes {}".format(key, data))

print(withData)

