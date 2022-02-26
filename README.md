# LenovoSA120-Fanspeed

LenovoSA120-Fanspeed but with Python 3

## Requirements

Requires Python 3 and the `sg_ses` utility, provided by [the `sg3_utils` package](http://sg.danny.cz/sg/sg3_utils.html)

Most Linux/BSD/Solaris systems support the sg3_utils package. This conversion to Python 3 has only been tested on Debian Buster. In theory it may be possible to use it on Solaris, OmniOS, OpenIndiana SmartOS, and OmniOS.

Debian-based systems:

    # apt install sg3-utils


FlynnLivesForks/LenovoSA120-Fanspeed
## Usage/configuration

Since most *nix based systems will place the device under `/dev/sg*`, `/dev/ses*`, or `/dev/bsg/*` the script should find the ThinkServer Enclosure automatically. 

You may need to use the `root` user or `sudo` to make this script work properly

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
## Acknowledgements

 - Original Developer [AndrewX192](https://awesomeopensource.com/project/elangosundar/awesome-README-templates)
 - Original Project Forked From [lenovo-sa120-fanspeed-utility](https://github.com/AndrewX192/lenovo-sa120-fanspeed-utility)
