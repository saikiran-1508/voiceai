import unittest
from pathlib import Path
from unittest.mock import patch

from commands import CommandRunner, PROJECT, parse_command


class CommandTests(unittest.TestCase):
    def test_only_complete_commands(self):
        for text in ['open chrome', 'do not computer open chrome', 'computer open chrome and delete files', 'computer run powershell', 'computer open chrome; whoami']:
            self.assertIsNone(parse_command(text), text)
        self.assertEqual(parse_command(' Computer   open Chrome! '), 'chrome')
        self.assertEqual(parse_command('computer open visual studio code'), 'vscode')

    @patch('commands.subprocess.Popen')
    def test_unknown_and_missing_apps_do_not_launch(self, launch):
        runner = CommandRunner()
        runner.run('computer delete files')
        with patch('commands.find_app', return_value=None):
            self.assertIn('Could not find', runner.run('computer open chrome'))
        launch.assert_not_called()

    @patch('commands.subprocess.Popen')
    def test_launch_fixed_args_and_suppress_duplicates(self, launch):
        runner = CommandRunner()
        with patch('commands.find_app', return_value=Path('C:/Apps/Code.exe')):
            runner.run('computer open visual studio code')
            self.assertIn('Repeated', runner.run('computer open v s code'))
        launch.assert_called_once_with(['C:\\Apps\\Code.exe', str(PROJECT)], shell=False, cwd=PROJECT)


if __name__ == '__main__':
    unittest.main()
