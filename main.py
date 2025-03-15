#!/usr/bin/env python
import sys

from svg_generator import create_svg

import io


def main():
    if len(sys.argv) < 2:
        print("Usage: python dxf_to_paths.py <dxf_file>")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, 'r') as f:
        fileStrContent = f.read()

    stream = io.StringIO(fileStrContent)

    created_svg = create_svg(stream)

    with open('test.svg', 'w') as f:
        f.write(created_svg)


if __name__ == '__main__':
    main()
