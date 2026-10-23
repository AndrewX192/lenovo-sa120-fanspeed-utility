# lenovo-sa120-fanspeed-utility

Sets the fan speed on Lenovo ThinkServer SA120 disk enclosures, which are
notoriously loud at their default setting. Speed `1` is the slowest (and
quietest); `7` is the fastest.

## Requirements

- Python 3.6 or later (CI tests 3.9–3.13)
- The `sg_ses` utility from [the `sg3_utils` package](http://sg.danny.cz/sg/sg3_utils.html)

Older `sg_ses` builds (sg3_utils before 1.38, e.g. CentOS 7) are detected
automatically and work fine; the script simply omits the `--maxlen` response
cap on those systems.

Debian-based systems:

    # apt-get install sg3-utils

RHEL/CentOS/Fedora systems:

    # yum install sg3_utils

FreeBSD systems via `pkg`:

    # pkg install sysutils/sg3_utils

FreeNAS/TrueNAS includes `sg_ses` as part of the standard image.

### Solaris/OmniOS/OpenIndiana/SmartOS

Native Solaris should have sg3_utils installed. If `sg_ses` is not present,
build it from source. Installing napp-it, for the ZFS GUI, also installs all
the requisite development tools.

On OmniOS CE, the steps involved were:

* Download [the `sg3_utils` package](http://sg.danny.cz/sg/sg3_utils.html).
  Move to somewhere like `/root` and extract.
* Change into the directory, configure with `./configure --prefix=/root/sg3_utils`.
* `make && make install`
* Point the script at the binary:
  `python3 fancontrol.py --sg-ses /root/sg3_utils/bin/sg_ses 2`
  (setting the `sg_ses_path` environment variable also works)

## Usage

Finds ThinkServer SA120 enclosures automatically, whether the SES devices are
`/dev/sg*`, `/dev/ses*`, `/dev/bsg/*`, or `/dev/es/ses*`. Run as root:

    # python3 fancontrol.py 1
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
    Setting fans 0-5 to 1
      LENOVO    ThinkServerSA120  1008
    Sending Enclosure Control [0x2] page, with page length=296 bytes

    Set fan speeds... Waiting to get fan speeds (ctrl+c to skip)
    Fan 0 speed: 440
    Fan 1 speed: 596
    Fan 2 speed: 593
    Fan 3 speed: 449
    Fan 4 speed: 583
    Fan 5 speed: 607

To check fan speeds without changing anything:

    # python3 fancontrol.py --status

To skip auto-discovery and target a specific enclosure (the device is still
verified to be an SA120 before anything is written to it):

    # python3 fancontrol.py --device /dev/sg6 2

See `python3 fancontrol.py --help` for all options.

## Setting the fan speed at boot

The enclosure reverts to its default fan speed when it loses power, so you
may want to re-apply your preferred speed at boot. On systemd-based systems,
create `/etc/systemd/system/sa120-fancontrol.service`:

    [Unit]
    Description=Set ThinkServer SA120 fan speed

    [Service]
    Type=oneshot
    ExecStart=/usr/bin/python3 /opt/lenovo-sa120-fanspeed-utility/fancontrol.py 2

    [Install]
    WantedBy=multi-user.target

Then enable it:

    # systemctl daemon-reload
    # systemctl enable --now sa120-fancontrol.service

## Development

Run the tests with [pytest](https://pytest.org/):

    $ pip install pytest
    $ pytest

The test suite mocks out `sg_ses`, so no SA120 hardware is needed.
