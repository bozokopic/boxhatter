import sys

from hatter.main import main


if __name__ == '__main__':
    sys.argv[0] = 'hatter'
    sys.exit(main())
