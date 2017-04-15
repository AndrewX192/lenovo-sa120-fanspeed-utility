#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys
import time
import glob
import stat

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from subprocess import check_output, Popen, PIPE, STDOUT, CalledProcessError

devices_to_check = ['/dev/sg*', '/dev/ses*', '/dev/bsg/*']


def usage():
    print('python fancontrol.py 1-7')
    sys.exit(-1)


def get_requested_fan_speed():
    if len(sys.argv) < 2:
        return usage()
    try:
        speed = int(sys.argv[1])
    except ValueError:
        return usage()
    if not 1 <= speed <= 7:
        return usage()
    return speed


def print_speeds(device):
    for i in range(0, 6):
        print('Fan {} speed: {}'.format(i, check_output(
            ['sg_ses', '--index=coo,{}'.format(i), '--get=1:2:11', device]).decode('utf-8').split('\n')[0]))


def find_sa120_devices():
    devices = []
    seen_devices = set()
    for device_glob in devices_to_check:
        for device in glob.glob(device_glob):
            stats = os.stat(device)
            if not stat.S_ISCHR(stats.st_mode):
                print('Enclosure not found on ' + device)
                continue
            device_id = format_device_id(stats)
            if device_id in seen_devices:
                print('Enclosure already seen on ' + device)
                continue
            seen_devices.add(device_id)
            try:
                output = check_output(['sg_ses', device], stderr=STDOUT)
                if b'ThinkServerSA120' in output:
                    print('Enclosure found on ' + device)
                    devices.append(device)
                else:
                    print('Enclosure not found on ' + device)
            except CalledProcessError:
                print('Enclosure not found on ' + device)
    return devices


def format_device_id(stats):
    return '{},{}'.format(os.major(stats.st_rdev), os.minor(stats.st_rdev))


def set_fan_speeds(device, speed):
    print_speeds(device)
    print('Reading current configuration...')
    out = check_output(['sg_ses', '-p', '0x2', device, '--raw']).decode('utf-8')

    s = out.split()

    for i in range(0, 6):
        print('Setting fan {} to {}'.format(i, speed))
        idx = 88 + 4 * i
        s[idx + 0] = '80'
        s[idx + 1] = '00'
        s[idx + 2] = '00'
        s[idx + 3] = format(1 << 5 | speed & 7, 'x')

    output = StringIO()
    off = 0
    count = 0

    while True:
        output.write(s[off])
        off = off + 1
        count = count + 1
        if count == 8:
            output.write('  ')
        elif count == 16:
            output.write('\n')
            count = 0
        else:
            output.write(' ')
        if off >= len(s):
            break

    output.write('\n')
    p = Popen(['sg_ses', '-p', '0x2', device, '--control', '--data', '-'], stdout=PIPE, stdin=PIPE,
              stderr=PIPE)
    print('Set fan speeds... Waiting to get fan speeds (ctrl+c to skip)')
    print(p.communicate(input=bytearray(output.getvalue(), 'utf-8'))[0].decode('utf-8'))
    try:
        time.sleep(10)
        print_speeds(device)
    except KeyboardInterrupt:
        pass


def main():
    speed = get_requested_fan_speed()
    devices = find_sa120_devices()
    if not devices:
        print('Could not find enclosure')
        sys.exit(1)
    for device in devices:
        set_fan_speeds(device, speed)
    print('\nDone')


if __name__ == '__main__':
    main()
