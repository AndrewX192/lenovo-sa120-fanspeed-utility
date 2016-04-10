import sys
import time
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from subprocess import check_output

def print_speeds():
  for i in range(0, 6):
    print("Fan {} speed: {}".format(i, check_output(['sg_ses', '--index=coo,{}'.format(i), '--get=1:2:11', '/dev/sg6']).decode('utf-8').split('\n')[0]))

print_speeds()
print("Reading current configuration...")
out = check_output(["sg_ses", "-p", "0x2", "/dev/sg6", "--raw"]).decode('utf-8')
s = out.split()
if len(sys.argv) < 1:
  print("python fanspeed.py 1-7")
  sys.exit(-1)
fan = int(sys.argv[1])
for i in range(0, 6):
  print("Setting fan {} to {}".format(i, fan))
  idx = 92 + 4 * i
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
from subprocess import Popen, PIPE, STDOUT
p = Popen(['sg_ses', '-p', '0x2', '/dev/sg6', '--control', '--data', '-'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
print(p.communicate(input=bytearray(output.getvalue(), 'utf-8'))[0].decode('utf-8'))
time.sleep(10)
print_speeds()
