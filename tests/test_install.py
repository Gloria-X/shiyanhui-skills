import http.server
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / 'shiyanhui-platform/SKILL.md').read_bytes()


class DownloadHandler(http.server.BaseHTTPRequestHandler):
    primary = SKILL
    fallback = SKILL
    primary_status = 200
    fallback_status = 200
    requests = []

    def do_GET(self):
        self.requests.append(self.path)
        primary = self.path == '/api/platform-skill/SKILL.md'
        body = self.primary if primary else self.fallback
        self.send_response(self.primary_status if primary else self.fallback_status)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class InstallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), DownloadHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.destination = self.root / 'codex/skills/shiyanhui-platform'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        # Only redirect the pinned GitHub URL to the local fixture; real curl still downloads it.
        shim = self.bin / 'curl'
        shim.write_text('''#!/usr/bin/env python3
import os
args = [os.environ['SKILL_TEST_GITHUB_URL'] if a.startswith('https://raw.githubusercontent.com/') else a for a in __import__('sys').argv[1:]]
# The fixture is HTTP; the production installer still requires HTTPS for GitHub.
args = ['=http,https' if a == '=https' else a for a in args]
os.execv('/usr/bin/curl', ['curl', *args])
''')
        shim.chmod(0o700)
        self.env = {**os.environ, 'CODEX_HOME': str(self.root / 'codex'),
                    'PATH': f'{self.bin}:{os.environ["PATH"]}',
                    'SKILL_TEST_GITHUB_URL': f'{self.origin}/github'}
        DownloadHandler.primary = SKILL
        DownloadHandler.fallback = SKILL
        DownloadHandler.primary_status = 200
        DownloadHandler.fallback_status = 200
        DownloadHandler.requests = []

    def run_installer(self, origin=None):
        return subprocess.run(['bash', str(ROOT / 'install.sh'), origin or self.origin],
                              env=self.env, capture_output=True, text=True, timeout=10)

    def test_minio_first_and_repeat_is_noop(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('from MinIO', result.stdout)
        self.assertEqual((self.destination / 'SKILL.md').read_bytes(), SKILL)
        self.assertEqual((self.destination / 'SKILL.md').stat().st_mode & 0o777, 0o600)
        self.assertEqual(DownloadHandler.requests, ['/api/platform-skill/SKILL.md'])
        timestamp = (self.destination / 'SKILL.md').stat().st_mtime_ns
        self.assertEqual(self.run_installer().returncode, 0)
        self.assertEqual((self.destination / 'SKILL.md').stat().st_mtime_ns, timestamp)
        self.assertEqual(len(DownloadHandler.requests), 1)

    def test_minio_failure_uses_github(self):
        DownloadHandler.primary_status = 503
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('from GitHub', result.stdout)
        self.assertEqual(DownloadHandler.requests, ['/api/platform-skill/SKILL.md', '/github'])
        self.assertEqual((self.destination / 'SKILL.md').read_bytes(), SKILL)

    def test_corrupt_minio_uses_verified_github(self):
        DownloadHandler.primary = b'<html>not a skill</html>'
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('from GitHub', result.stdout)

    def test_both_corrupt_install_nothing(self):
        DownloadHandler.primary = b'partial'
        DownloadHandler.fallback = b'also invalid'
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.destination.exists())

    def test_both_unavailable_install_nothing(self):
        DownloadHandler.primary_status = 503
        DownloadHandler.fallback_status = 404
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.destination.exists())

    def test_existing_local_changes_are_preserved(self):
        self.destination.mkdir(parents=True)
        (self.destination / 'SKILL.md').write_text('local changes')
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertEqual((self.destination / 'SKILL.md').read_text(), 'local changes')
        self.assertEqual(DownloadHandler.requests, [])

    def test_symlink_is_not_followed(self):
        other = self.root / 'other'
        other.mkdir()
        self.destination.parent.mkdir(parents=True)
        self.destination.symlink_to(other, target_is_directory=True)
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertEqual(list(other.iterdir()), [])

    def test_origin_cannot_be_a_path_or_shell_expression(self):
        for origin in ['file:///etc/passwd', self.origin + '/path', "http://host'; touch /tmp/no"]:
            self.assertNotEqual(self.run_installer(origin).returncode, 0)
        self.assertEqual(DownloadHandler.requests, [])


if __name__ == '__main__':
    unittest.main()
