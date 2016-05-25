#!/usr/bin/env python
import sys
import time
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from subprocess import check_output, Popen, PIPE, STDOUT

def print_speeds(device):
  for i in range(0, 6):
    print("Fan {} speed: {}".format(i, check_output(['sg_ses', '--index=coo,{}'.format(i), '--get=1:2:11', device]).decode('utf-8').split('\n')[0]))

if len(sys.argv) < 2:
  print("python fancontrol.py /dev/sgX 1-7")
  sys.exit(-1)

device = sys.argv[1]
fan = int(sys.argv[2])

if fan <= 0 or fan > 6:
  raise Exception("Fan speed must be between 1 and 7")

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
