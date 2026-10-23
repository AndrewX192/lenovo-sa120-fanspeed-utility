#!/usr/bin/env python3
"""Fan speed utility for the Lenovo ThinkServer SA120 disk enclosure.

Finds SA120 enclosures via sg_ses and sets all six fans to a requested
speed, from 1 (slowest/quietest) to 7 (fastest).
"""

import argparse
import functools
import glob
import os
import stat
import subprocess
import sys
import time

__version__ = '0.2.0'

DEVICE_GLOBS = ['/dev/sg*', '/dev/ses*', '/dev/bsg/*', '/dev/es/ses*']

FAN_COUNT = 6

# Byte offset of the first cooling (fan) element's control descriptor within
# the SES Enclosure Control page (0x2) as the SA120 returns it: an 8-byte page
# header followed by 4-byte control descriptors for the element types that
# precede the cooling elements in the enclosure's configuration page (0x1).
# The six fan descriptors are contiguous from here.
FAN_ELEMENT_OFFSET = 88


@functools.lru_cache(maxsize=None)
def sg_ses_supports_maxlen(sg_ses):
    """Check whether this sg_ses binary accepts --maxlen.

    FreeBSD terminates SES requests whose response buffer exceeds 65535
    bytes, so we cap the response length where we can. But sg_ses only
    gained --maxlen in sg3_utils 1.38 (2014); older builds such as the
    one on CentOS 7 reject the whole command when given the option.
    """
    result = subprocess.run([sg_ses, '--maxlen=32768', '--version'], check=False,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def sg_ses_command(sg_ses, args):
    command = [sg_ses]
    if sg_ses_supports_maxlen(sg_ses):
        command.append('--maxlen=32768')
    return command + args


def read_fan_speed(sg_ses, device, fan):
    output = subprocess.check_output(
        sg_ses_command(sg_ses, [f'--index=coo,{fan}', '--get=1:2:11', device]))
    return output.decode('utf-8').split('\n')[0]


def print_fan_speeds(sg_ses, device):
    for fan in range(FAN_COUNT):
        print(f'Fan {fan} speed: {read_fan_speed(sg_ses, device, fan)}')


def is_sa120(sg_ses, device):
    try:
        output = subprocess.check_output(
            sg_ses_command(sg_ses, [device]), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return False
    return b'ThinkServerSA120' in output


def find_enclosures(sg_ses):
    devices = []
    seen_devices = set()
    for device_glob in DEVICE_GLOBS:
        for device in glob.glob(device_glob):
            try:
                stats = os.stat(device)
            except OSError:
                continue
            if not stat.S_ISCHR(stats.st_mode):
                print('Enclosure not found on ' + device)
                continue
            device_id = (os.major(stats.st_rdev), os.minor(stats.st_rdev))
            if device_id in seen_devices:
                print('Enclosure already seen on ' + device)
                continue
            seen_devices.add(device_id)
            if is_sa120(sg_ses, device):
                print('Enclosure found on ' + device)
                devices.append(device)
            else:
                print('Enclosure not found on ' + device)
    return devices


def select_devices(sg_ses, requested):
    """Validate devices named with --device: drop nodes that alias an
    already-selected device, and refuse anything that does not identify as
    an SA120 — the control page we write uses SA120-specific byte offsets
    and could misconfigure other SES hardware.
    """
    devices = []
    seen_devices = set()
    for device in requested:
        try:
            stats = os.stat(device)
        except OSError as error:
            raise ValueError(f'cannot access {device}: {error.strerror}') from error
        device_id = (os.major(stats.st_rdev), os.minor(stats.st_rdev))
        if device_id in seen_devices:
            print('Enclosure already seen on ' + device)
            continue
        seen_devices.add(device_id)
        if not is_sa120(sg_ses, device):
            raise ValueError(f'{device} does not identify as a ThinkServer SA120')
        devices.append(device)
    return devices


def build_control_page(raw, speed):
    """Return a modified copy of a raw Enclosure Control page with all fans
    set to the requested speed.

    ``raw`` is the page as dumped by ``sg_ses --raw``: a whitespace-separated
    hex dump, one token per byte. The result is formatted the same way, which
    is what ``sg_ses --control --data -`` expects back.
    """
    tokens = raw.split()
    needed = FAN_ELEMENT_OFFSET + 4 * FAN_COUNT
    if len(tokens) < needed:
        raise ValueError(
            f'enclosure control page too short: {len(tokens)} bytes, '
            f'need at least {needed}')
    for fan in range(FAN_COUNT):
        idx = FAN_ELEMENT_OFFSET + 4 * fan
        tokens[idx] = b'80'  # SELECT bit: apply this control descriptor
        tokens[idx + 1] = b'00'
        tokens[idx + 2] = b'00'
        # Bit 5 is RQST ON; bits 2:0 are the requested speed code.
        tokens[idx + 3] = format(1 << 5 | speed & 7, '02x').encode('ascii')
    lines = []
    for start in range(0, len(tokens), 16):
        chunk = tokens[start:start + 16]
        line = b' '.join(chunk[:8])
        if len(chunk) > 8:
            line += b'  ' + b' '.join(chunk[8:])
        lines.append(line)
    return b'\n'.join(lines) + b'\n'


def set_fan_speeds(sg_ses, device, speed):
    print_fan_speeds(sg_ses, device)
    print('Reading current configuration...')
    raw = subprocess.check_output(
        sg_ses_command(sg_ses, ['-p', '0x2', device, '--raw']))
    print(f'Setting fans 0-{FAN_COUNT - 1} to {speed}')
    page = build_control_page(raw, speed)
    result = subprocess.run(
        sg_ses_command(sg_ses, ['-p', '0x2', device, '--control', '--data', '-']),
        input=page, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    print(result.stdout.decode('utf-8'))
    print('Set fan speeds... Waiting to get fan speeds (ctrl+c to skip)')
    try:
        time.sleep(10)
        print_fan_speeds(sg_ses, device)
    except KeyboardInterrupt:
        pass


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description='Set the fan speed on Lenovo ThinkServer SA120 enclosures.')
    parser.add_argument('speed', nargs='?', type=int, choices=range(1, 8),
                        metavar='speed',
                        help='fan speed: 1 (slowest) to 7 (fastest)')
    parser.add_argument('--status', action='store_true',
                        help='report current fan speeds without changing them')
    parser.add_argument('--device', action='append', metavar='DEV',
                        help='SES device of an enclosure (may be given more than '
                             'once); default: scan for SA120 enclosures')
    parser.add_argument('--sg-ses', metavar='PATH',
                        default=os.environ.get('sg_ses_path', 'sg_ses'),
                        help='path to the sg_ses binary (default: sg_ses from '
                             'PATH, or the sg_ses_path environment variable)')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')
    args = parser.parse_args(argv)
    if args.speed is None and not args.status:
        parser.error('a fan speed is required unless --status is given')
    if args.speed is not None and args.status:
        parser.error('--status cannot be combined with a fan speed')
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.device:
            devices = select_devices(args.sg_ses, args.device)
        else:
            devices = find_enclosures(args.sg_ses)
        if not devices:
            print('Could not find enclosure')
            return 1
        for device in devices:
            if args.status:
                print_fan_speeds(args.sg_ses, device)
            else:
                set_fan_speeds(args.sg_ses, device, args.speed)
    except FileNotFoundError:
        print(f"error: could not run sg_ses binary '{args.sg_ses}'", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or b'').decode('utf-8').strip()
        if stderr:
            print(stderr, file=sys.stderr)
        print(f'error: {" ".join(error.cmd)} failed with exit status {error.returncode}',
              file=sys.stderr)
        return 1
    except ValueError as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    print('\nDone')
    return 0


if __name__ == '__main__':
    sys.exit(main())
