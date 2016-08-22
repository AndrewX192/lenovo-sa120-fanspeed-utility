#!/usr/bin/env python
import sys
import time
import glob

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from subprocess import check_output, Popen, PIPE, STDOUT

def print_speeds(device):
  for i in range(0, 6):
    print("Fan {} speed: {}".format(i, check_output(['sg_ses', '--index=coo,{}'.format(i), '--get=1:2:11', device]).decode('utf-8').split('\n')[0]))

if len(sys.argv) < 1:
  print("python fancontrol.py 1-7")
  sys.exit(-1)

fan = int(sys.argv[1])

if fan <= 0 or fan > 6:
  raise Exception("Fan speed must be between 1 and 7")


devices_to_check = ['/dev/sg*','/dev/ses*']

device = ""

for chk_device in devices_to_check:
  for dev_node in glob.glob(chk_device):
    try:
      out = check_output(["sg_ses", dev_node], stderr=STDOUT)
      if 'ThinkServerSA120' in out:
        device = dev_node
	print("Enclosure found on " + device);

	print_speeds(device)
	print("Reading current configuration...")
	out = check_output(["sg_ses", "-p", "0x2", device, "--raw"]).decode('utf-8')
	s = out.split()

	for i in range(0, 6):
	  print("Setting fan {} to {}".format(i, fan))
	  idx = 88 + 4 * i
	  s[idx+0] = "80"
	  s[idx+1] = "00"
	  s[idx+2] = "00"
	  s[idx+3] = format(1 << 5 | fan & 7, "x")

	output = StringIO()
	off = 0
	count = 0
	line = ''

	while True:
	  output.write(s[off])
	  off = off + 1
	  count = count + 1
	  if count == 8 :
	    output.write("  ")
	  elif count == 16:
	    output.write("\n")
	    count=0
	  else:
	    output.write(" ")
	  if off >= len(s):
	    break

	output.write("\n")
	p = Popen(['sg_ses', '-p', '0x2', device, '--control', '--data', '-'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
	print("Set fan speeds... Waiting to get fan speeds (ctrl+c to skip)")
	print(p.communicate(input=bytearray(output.getvalue(), 'utf-8'))[0].decode('utf-8'))
	time.sleep(10)
	print_speeds(device)
    except:
      print("Enclosure not found on " + dev_node)

if device == "":
  print("Could not find enclosure")
  sys.exit(1)
