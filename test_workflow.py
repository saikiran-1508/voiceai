import unittest
from unittest.mock import Mock
from workflow import build_workflow


class WorkflowTests(unittest.TestCase):
    def test_success_route(self):
        runner = Mock()
        runner.run.return_value = 'Launch requested.'
        updates = list(build_workflow(runner).stream({'text': 'computer open notepad'}, stream_mode='updates'))
        self.assertEqual([next(iter(item)) for item in updates], ['interpret', 'validate', 'execute', 'report'])
        runner.run.assert_called_once_with('computer open notepad')
        self.assertEqual(updates[-1]['report']['detail'], 'Launch requested.')

    def test_unknown_skips_execution(self):
        runner = Mock()
        updates = list(build_workflow(runner).stream({'text': 'computer delete files'}, stream_mode='updates'))
        self.assertEqual([next(iter(item)) for item in updates], ['interpret', 'validate', 'reject', 'report'])
        runner.run.assert_not_called()

    def test_cancel_between_validation_and_execution(self):
        runner = Mock()
        cancelled = [False]
        graph = build_workflow(runner, cancelled=lambda: cancelled[0])
        updates = graph.stream({'text': 'computer open chrome'}, stream_mode='updates')
        for update in updates:
            if 'validate' in update:
                cancelled[0] = True
        runner.run.assert_not_called()

    def test_error_is_reported_without_retry(self):
        runner = Mock()
        runner.run.side_effect = OSError('launch failed')
        state = build_workflow(runner).invoke({'text': 'computer open chrome'})
        self.assertIn('Action failed: launch failed', state['result'])
        self.assertEqual(runner.run.call_count, 1)

    def test_stop_and_demo_do_not_launch(self):
        runner = Mock()
        graph = build_workflow(runner, dry_run=True)
        self.assertTrue(graph.invoke({'text': 'computer stop listening'})['stop_requested'])
        state = graph.invoke({'text': 'computer open chrome'})
        self.assertFalse(state['stop_requested'])
        self.assertIn('Demo only', state['result'])
        runner.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
