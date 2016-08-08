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

Finds the ThinkServer Enclosure automatically.  Works when the devices are either `/dev/sg*` or `/dev/ses*`

Use `fancontrol.py` to set the fan speed:

    # python fancontrol.py 1
    Enclosure not found on /dev/sg8
    Enclosure not found on /dev/sg7
    Enclosure found on /dev/sg6
    Fan 0 speed: 1193
    Fan 1 speed: 1205
    Fan 2 speed: 1171
    Fan 3 speed: 1217
    Fan 4 speed: 1181
    Fan 5 speed: 1218
    Reading current configuration...
    Setting fan 0 to 1
    Setting fan 1 to 1
    Setting fan 2 to 1
    Setting fan 3 to 1
    Setting fan 4 to 1
    Setting fan 5 to 1
    Set fan speeds... Waiting to get fan speeds (ctrl+c to skip)
      LENOVO    ThinkServerSA120  1008
    Sending Enclosure Control [0x2] page, with page length=296 bytes

    Fan 0 speed: 440
    Fan 1 speed: 596
    Fan 2 speed: 593
    Fan 3 speed: 449
    Fan 4 speed: 583
    Fan 5 speed: 607
