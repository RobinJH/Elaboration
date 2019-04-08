#! /usr/bin/python

#
# Create a set of .ada files from the output of the scanner
#


import re

from pathlib import Path

RE_FILENAME = r"^([\w\.]*)\s+"
RE_WITH_LIST = r"\[(.*?)\]"


def writeFile(filepath, withList):
    with open(filepath, "w") as f:
        f.write("\n")
        for w in withList:
            f.write("with {};\n".format(w))
        f.write("\n")

if __name__ == "__main__":
    cwd = Path.cwd()
    outputDir = Path(cwd / "testFiles")

    if not outputDir.exists():
        outputDir.mkdir()

    inputFilename = input("Enter source filename: ")

    with open(inputFilename) as file:
        for line in file:
            filename = ""
            match = re.search(RE_FILENAME, line)
            if match:
                filename = match.group(1)
            withList = ""
            match = re.search(RE_WITH_LIST, line)
            if match:
                withList = match.group(1)
            withList = withList.replace("'", "")
            withList = withList.replace(",", "")
            withs = withList.split()
            filename = filename + ".ada"
            print("New File: {}, with list = {}".format(filename, withs))

            writeFile(outputDir / filename, withs)

