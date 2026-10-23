import stat
import subprocess

import pytest

import fancontrol

PAGE_LENGTH = 296  # bytes in the SA120's Enclosure Control page


@pytest.fixture(autouse=True)
def clear_maxlen_probe_cache():
    fancontrol.sg_ses_supports_maxlen.cache_clear()


class FakeCompletedProcess:
    def __init__(self, returncode, stdout=b''):
        self.returncode = returncode
        self.stdout = stdout


class TestSgSesCommand:
    def test_includes_maxlen_when_supported(self, monkeypatch):
        monkeypatch.setattr(fancontrol.subprocess, 'run',
                            lambda cmd, **kwargs: FakeCompletedProcess(0))
        assert fancontrol.sg_ses_command('sg_ses', ['/dev/sg0']) == \
            ['sg_ses', '--maxlen=32768', '/dev/sg0']

    def test_omits_maxlen_when_unsupported(self, monkeypatch):
        """Old sg_ses builds (sg3_utils < 1.38, e.g. CentOS 7) reject
        --maxlen; the flag must be dropped or every command fails."""
        monkeypatch.setattr(fancontrol.subprocess, 'run',
                            lambda cmd, **kwargs: FakeCompletedProcess(1))
        assert fancontrol.sg_ses_command('sg_ses', ['/dev/sg0']) == \
            ['sg_ses', '/dev/sg0']

    def test_probes_each_binary_once(self, monkeypatch):
        probes = []

        def fake_run(cmd, **kwargs):
            probes.append(cmd)
            return FakeCompletedProcess(0)

        monkeypatch.setattr(fancontrol.subprocess, 'run', fake_run)
        fancontrol.sg_ses_command('sg_ses', ['/dev/sg0'])
        fancontrol.sg_ses_command('sg_ses', ['/dev/sg1'])
        assert probes == [['sg_ses', '--maxlen=32768', '--version']]


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
        args = fancontrol.parse_args(['2', '--sg-ses', '/usr/bin/sg_ses'])
        assert args.sg_ses == '/usr/bin/sg_ses'


class FakeStat:
    def __init__(self, rdev, char_device=True):
        self.st_mode = (stat.S_IFCHR if char_device else stat.S_IFREG) | 0o600
        self.st_rdev = rdev


class TestFindEnclosures:
    def setup_devices(self, monkeypatch, globs, stats, outputs):
        monkeypatch.setattr(fancontrol, 'sg_ses_supports_maxlen', lambda sg_ses: True)
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


class TestSetFanSpeeds:
    def setup_fakes(self, monkeypatch, control_returncode=0):
        self.raw_page = format_raw_page(make_raw_page())
        self.commands = []
        self.control_writes = []

        def fake_check_output(cmd, **kwargs):
            self.commands.append(cmd)
            return self.raw_page if '--raw' in cmd else b'1200\n'

        def fake_run(cmd, input=None, **kwargs):
            self.commands.append(cmd)
            self.control_writes.append(input)
            if control_returncode != 0:
                raise subprocess.CalledProcessError(
                    control_returncode, cmd, output=b'', stderr=b'permission denied\n')
            return FakeCompletedProcess(0, stdout=b'sent control page\n')

        monkeypatch.setattr(fancontrol, 'sg_ses_supports_maxlen', lambda sg_ses: True)
        monkeypatch.setattr(fancontrol.subprocess, 'check_output', fake_check_output)
        monkeypatch.setattr(fancontrol.subprocess, 'run', fake_run)
        monkeypatch.setattr(fancontrol.time, 'sleep', lambda seconds: None)

    def test_all_commands_use_given_sg_ses_binary(self, monkeypatch):
        """Regression test: the configured sg_ses path must be used for the
        control-page read/write too, not just discovery."""
        self.setup_fakes(monkeypatch)
        fancontrol.set_fan_speeds('/custom/path/sg_ses', '/dev/sg0', 2)
        assert all(cmd[0] == '/custom/path/sg_ses' for cmd in self.commands)
        assert self.control_writes == [fancontrol.build_control_page(self.raw_page, 2)]

    def test_failed_control_write_propagates(self, monkeypatch):
        self.setup_fakes(monkeypatch, control_returncode=1)
        with pytest.raises(subprocess.CalledProcessError):
            fancontrol.set_fan_speeds('sg_ses', '/dev/sg0', 2)


class TestSelectDevices:
    def setup_fakes(self, monkeypatch, stats, sa120_devices):
        monkeypatch.setattr(fancontrol.os, 'stat', lambda device: stats[device])
        monkeypatch.setattr(fancontrol, 'is_sa120',
                            lambda sg_ses, device: device in sa120_devices)

    def test_accepts_verified_sa120(self, monkeypatch):
        self.setup_fakes(monkeypatch, {'/dev/sg0': FakeStat(100)}, {'/dev/sg0'})
        assert fancontrol.select_devices('sg_ses', ['/dev/sg0']) == ['/dev/sg0']

    def test_rejects_non_sa120_device(self, monkeypatch):
        """--device must not bypass the enclosure identity check: the control
        page we write uses SA120-specific offsets."""
        self.setup_fakes(monkeypatch, {'/dev/sg0': FakeStat(100)}, set())
        with pytest.raises(ValueError, match='does not identify'):
            fancontrol.select_devices('sg_ses', ['/dev/sg0'])

    def test_deduplicates_aliases_of_one_enclosure(self, monkeypatch):
        self.setup_fakes(
            monkeypatch,
            {'/dev/sg0': FakeStat(100), '/dev/ses0': FakeStat(100)},
            {'/dev/sg0', '/dev/ses0'})
        assert fancontrol.select_devices(
            'sg_ses', ['/dev/sg0', '/dev/ses0']) == ['/dev/sg0']

    def test_missing_device_raises_value_error(self, monkeypatch):
        def raising_stat(device):
            raise OSError(2, 'No such file or directory', device)

        monkeypatch.setattr(fancontrol.os, 'stat', raising_stat)
        with pytest.raises(ValueError, match='cannot access'):
            fancontrol.select_devices('sg_ses', ['/dev/nosuch'])


class TestMainErrorHandling:
    def test_sg_ses_failure_is_reported_not_raised(self, monkeypatch, capsys):
        monkeypatch.setattr(fancontrol, 'select_devices',
                            lambda sg_ses, requested: ['/dev/sg0'])

        def failing_set(sg_ses, device, speed):
            raise subprocess.CalledProcessError(
                1, ['sg_ses', '/dev/sg0'], stderr=b'permission denied\n')

        monkeypatch.setattr(fancontrol, 'set_fan_speeds', failing_set)
        assert fancontrol.main(['2', '--device', '/dev/sg0']) == 1
        captured = capsys.readouterr()
        assert 'permission denied' in captured.err
        assert 'exit status 1' in captured.err

    def test_short_control_page_is_reported_not_raised(self, monkeypatch, capsys):
        monkeypatch.setattr(fancontrol, 'select_devices',
                            lambda sg_ses, requested: ['/dev/sg0'])
        monkeypatch.setattr(fancontrol, 'sg_ses_supports_maxlen', lambda sg_ses: True)
        monkeypatch.setattr(fancontrol.subprocess, 'check_output',
                            lambda cmd, **kwargs: b'00 01 02 03\n')
        assert fancontrol.main(['2', '--device', '/dev/sg0']) == 1
        assert 'control page too short' in capsys.readouterr().err
