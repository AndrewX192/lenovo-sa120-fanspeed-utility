import stat
import subprocess

import pytest

import fancontrol

PAGE_LENGTH = 296  # bytes in the SA120's Enclosure Control page


def format_raw_page(tokens):
    """Format hex-dump tokens the way sg_ses --raw does: 16 bytes per line,
    a double space after the 8th."""
    lines = []
    for start in range(0, len(tokens), 16):
        chunk = tokens[start:start + 16]
        line = b' '.join(chunk[:8])
        if len(chunk) > 8:
            line += b'  ' + b' '.join(chunk[8:])
        lines.append(line)
    return b'\n'.join(lines) + b'\n'


def make_raw_page():
    # Distinct byte values so unintended modifications are detectable.
    return [format(i % 256, '02x').encode('ascii') for i in range(PAGE_LENGTH)]


class TestBuildControlPage:
    @pytest.mark.parametrize('speed', [1, 3, 7])
    def test_sets_fan_control_descriptors(self, speed):
        tokens = make_raw_page()
        result = fancontrol.build_control_page(format_raw_page(tokens), speed)
        result_tokens = result.split()
        assert len(result_tokens) == PAGE_LENGTH
        for fan in range(fancontrol.FAN_COUNT):
            idx = fancontrol.FAN_ELEMENT_OFFSET + 4 * fan
            expected_byte3 = format(0x20 | speed, '02x').encode('ascii')
            assert result_tokens[idx:idx + 4] == [b'80', b'00', b'00', expected_byte3]

    def test_leaves_other_bytes_untouched(self):
        tokens = make_raw_page()
        result_tokens = fancontrol.build_control_page(format_raw_page(tokens), 4).split()
        fan_bytes = {fancontrol.FAN_ELEMENT_OFFSET + 4 * fan + i
                     for fan in range(fancontrol.FAN_COUNT) for i in range(4)}
        for i in range(PAGE_LENGTH):
            if i not in fan_bytes:
                assert result_tokens[i] == tokens[i]

    def test_output_layout_matches_sg_ses_raw_format(self):
        tokens = make_raw_page()
        result = fancontrol.build_control_page(format_raw_page(tokens), 2)
        assert result == format_raw_page(result.split())


class TestParseArgs:
    def test_speed_only(self):
        args = fancontrol.parse_args(['3'])
        assert args.speed == 3
        assert not args.status

    @pytest.mark.parametrize('argv', [[], ['0'], ['8'], ['fast'], ['--status', '2']])
    def test_invalid_usage_exits(self, argv):
        with pytest.raises(SystemExit):
            fancontrol.parse_args(argv)

    def test_status_without_speed(self):
        args = fancontrol.parse_args(['--status'])
        assert args.status
        assert args.speed is None

    def test_device_can_repeat(self):
        args = fancontrol.parse_args(['2', '--device', '/dev/sg3', '--device', '/dev/sg4'])
        assert args.device == ['/dev/sg3', '/dev/sg4']

    def test_sg_ses_defaults_from_environment(self, monkeypatch):
        monkeypatch.setenv('sg_ses_path', '/opt/sg3_utils/bin/sg_ses')
        assert fancontrol.parse_args(['2']).sg_ses == '/opt/sg3_utils/bin/sg_ses'

    def test_sg_ses_flag_overrides_environment(self, monkeypatch):
        monkeypatch.setenv('sg_ses_path', '/opt/sg3_utils/bin/sg_ses')
        assert fancontrol.parse_args(['2', '--sg-ses', '/usr/bin/sg_ses']).sg_ses == '/usr/bin/sg_ses'


class FakeStat:
    def __init__(self, rdev, char_device=True):
        self.st_mode = (stat.S_IFCHR if char_device else stat.S_IFREG) | 0o600
        self.st_rdev = rdev


class TestFindEnclosures:
    def setup_devices(self, monkeypatch, globs, stats, outputs):
        monkeypatch.setattr(fancontrol.glob, 'glob', lambda pattern: globs.get(pattern, []))
        monkeypatch.setattr(fancontrol.os, 'stat', lambda device: stats[device])
        self.commands = []

        def fake_check_output(cmd, **kwargs):
            self.commands.append(cmd)
            device = cmd[-1]
            if device not in outputs:
                raise subprocess.CalledProcessError(1, cmd)
            return outputs[device]

        monkeypatch.setattr(fancontrol.subprocess, 'check_output', fake_check_output)

    def test_detects_sa120_and_skips_other_enclosures(self, monkeypatch):
        self.setup_devices(
            monkeypatch,
            globs={'/dev/sg*': ['/dev/sg0', '/dev/sg1', '/dev/sg2']},
            stats={'/dev/sg0': FakeStat(100), '/dev/sg1': FakeStat(101),
                   '/dev/sg2': FakeStat(102)},
            outputs={'/dev/sg0': b'  LENOVO    ThinkServerSA120  1008',
                     '/dev/sg1': b'some other enclosure'})
        assert fancontrol.find_enclosures('sg_ses') == ['/dev/sg0']

    def test_deduplicates_devices_by_device_number(self, monkeypatch):
        sa120 = b'ThinkServerSA120'
        self.setup_devices(
            monkeypatch,
            globs={'/dev/sg*': ['/dev/sg0'], '/dev/ses*': ['/dev/ses0']},
            stats={'/dev/sg0': FakeStat(100), '/dev/ses0': FakeStat(100)},
            outputs={'/dev/sg0': sa120, '/dev/ses0': sa120})
        assert fancontrol.find_enclosures('sg_ses') == ['/dev/sg0']

    def test_skips_non_character_devices(self, monkeypatch):
        self.setup_devices(
            monkeypatch,
            globs={'/dev/sg*': ['/dev/sg0']},
            stats={'/dev/sg0': FakeStat(100, char_device=False)},
            outputs={'/dev/sg0': b'ThinkServerSA120'})
        assert fancontrol.find_enclosures('sg_ses') == []
        assert self.commands == []

    def test_uses_given_sg_ses_binary(self, monkeypatch):
        self.setup_devices(
            monkeypatch,
            globs={'/dev/sg*': ['/dev/sg0']},
            stats={'/dev/sg0': FakeStat(100)},
            outputs={'/dev/sg0': b'ThinkServerSA120'})
        fancontrol.find_enclosures('/custom/path/sg_ses')
        assert all(cmd[0] == '/custom/path/sg_ses' for cmd in self.commands)


def make_fake_popen(instances):
    class FakePopen:
        def __init__(self, cmd, **kwargs):
            self.cmd = cmd
            self.stdin_data = None
            instances.append(self)

        def communicate(self, input=None):
            self.stdin_data = input
            return (b'sent control page\n', b'')

    return FakePopen


class TestSetFanSpeeds:
    def test_all_commands_use_given_sg_ses_binary(self, monkeypatch):
        """Regression test: the configured sg_ses path must be used for the
        control-page read/write too, not just discovery."""
        raw_page = format_raw_page(make_raw_page())
        commands = []

        def fake_check_output(cmd, **kwargs):
            commands.append(cmd)
            return raw_page if '--raw' in cmd else b'1200\n'

        popen_instances = []
        monkeypatch.setattr(fancontrol.subprocess, 'check_output', fake_check_output)
        monkeypatch.setattr(fancontrol.subprocess, 'Popen', make_fake_popen(popen_instances))
        monkeypatch.setattr(fancontrol.time, 'sleep', lambda seconds: None)

        fancontrol.set_fan_speeds('/custom/path/sg_ses', '/dev/sg0', 2)

        assert all(cmd[0] == '/custom/path/sg_ses' for cmd in commands)
        assert len(popen_instances) == 1
        popen = popen_instances[0]
        assert popen.cmd[0] == '/custom/path/sg_ses'
        assert popen.stdin_data == fancontrol.build_control_page(raw_page, 2)
