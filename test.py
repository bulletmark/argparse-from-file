import argparse_from_file as argparse

opt = argparse.ArgumentParser()
opt.add_argument('-b', '--bool', action='store_true', help='sample bool option')
opt.add_argument('-s', '--str', help='sample str option')
args = opt.parse_args()

print(args, '\n')

opt.print_help()
