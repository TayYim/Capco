#! python3
# -*- encoding: utf-8 -*-
'''
@File    :   main.py
@Time    :   2025/02/21 15:57:40
@Author  :   Songyang Yan 
@Version :   1.0
@Desc    :   Main entry of the project
@Usage   :   usage here
'''

import sys, argparse, logging, os
from datetime import datetime

log = logging.getLogger(__name__)

def main():
    # set up argument parser
    parser = argparse.ArgumentParser(description='A simple python script')
    parser.add_argument('target', help='positional argument')
    parser.add_argument("-s", "--string", help="An optional string argument")
    parser.add_argument("-b", "--bool", action="store_true", default=False, help='An optional boolean argument')
    parser.add_argument("-l", "--list", choices={"apple", "orange"}, default="apple", help="An optional list argument")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increases output verbosity")
    parser.add_argument("-sl", "--save_log", action="store_true", default=False, help="Save log output to a file")
    args = parser.parse_args()

    # set up logger
    log.setLevel(logging.INFO if not args.verbose else logging.DEBUG)
    log_screen_handler = logging.StreamHandler(stream=sys.stdout)
    log.addHandler(log_screen_handler)
    log.propagate = False
    
    if args.save_log:
      timestamp = datetime.now().strftime("%Y%m%d_%H%M")
      log_filename = f"{os.path.splitext(os.path.basename(__file__))[0]}_{timestamp}.log"
      log_file_handler = logging.FileHandler(log_filename)
      log.addHandler(log_file_handler)
    
    # run the script
    log.info(f"Script called with the following arguments: {vars(args)}")

    # Your code here

if __name__ == '__main__':
    try:
      main()
    except KeyboardInterrupt:
      log.critical('Interrupted by user')
      try:
        sys.exit(0)
      except SystemExit:
        os._exit(0)