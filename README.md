# lenovo-sa120-fanspeed-utility

This is currently in prototype status.

## Requirements

Requires Python and the `sg_ses` utility, provided by [the `sg3_utils` package](http://sg.danny.cz/sg/sg3_utils.html).

Debian-based systems might use:

    # apt-get install sg3-utils

On RHEL/CentOS systems:

    # yum install sg3_utils

FreeNAS 9.10 includes `sg_ses` as part of the standard image.

## Usage

This fork looks up the ThinkServer Enclosure automatically.  Works when the devices are either `/dev/sg*` or `/dev/ses*`

Use `fancontrol.py` to set the fan speed:

    # python fancontrol.py 2
    Enclosure not found on /dev/sg8
    Enclosure not found on /dev/sg7
    Enclosure found on /dev/sg6
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
