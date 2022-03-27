import sys

from boxhatter.main import main


if __name__ == '__main__':
    sys.argv[0] = 'boxhatter'
    sys.exit(main())
