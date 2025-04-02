from sys import argv

from dxf_utils import read_dxf


def doFile(filePath):
    print("Running Python code")
    print(filePath)

    fileStream = open(filePath, "r")

    doc = read_dxf(fileStream)
    msp = doc.modelspace()

    print("Entities in the drawing:")
    for entity in msp:
        print(entity.dxftype())


if __name__ == "__main__":
    doFile(argv[1])
