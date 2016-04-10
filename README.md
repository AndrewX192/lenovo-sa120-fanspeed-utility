# lenovo-sa120-fanspeed-utility

This is currently in prototype status.

## Requirements

apt-get install sg3-utils

## Usage

find your scsi controller (one of the /dev/sgX devices, perhaps using lsscsi)

change /dev/sgX in fanspeed.py if needed.

````
# python fan.py 2
Fan 0 speed: 0
Fan 1 speed: 947
Fan 2 speed: 932
Fan 3 speed: 812
Fan 4 speed: 932
Fan 5 speed: 947
Reading current configuration...
Setting fan 0 to 2
Setting fan 1 to 2
Setting fan 2 to 2
Setting fan 3 to 2
Setting fan 4 to 2
Setting fan 5 to 2
  LENOVO    ThinkServerSA120  1007
Sending Enclosure Control [0x2] page, with page length=296 bytes

Fan 0 speed: 0
Fan 1 speed: 945
Fan 2 speed: 932
Fan 3 speed: 812
Fan 4 speed: 926
Fan 5 speed: 945

````
