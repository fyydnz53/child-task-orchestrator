import importlib.util
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "child_task.py"


def load_module():
    if not MODULE_PATH.exists():
        raise AssertionError(f"implementation missing: {MODULE_PATH}")
    spec = importlib.util.spec_from_file_location("child_task", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChildTaskStateTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "project"
        self.project.mkdir()
        self.state = self.module.init_project(
            self.project,
            parent_thread_id="parent-thread-1",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_child(self, **overrides):
        values = {
            "project_root": self.project,
            "title": "Host Agent filter optimization",
            "objective": "Improve the refine quality gate.",
            "acceptance_criteria": [
                {"id": "ac-1", "text": "Regression tests pass"},
            ],
            "mode": "code",
            "parent_context_revision": 1,
            "writable_paths": ["host_agent_mining/", "tests/"],
            "operation_id": "op-create-1",
        }
        values.update(overrides)
        return self.module.create_child(**values)

    def test_init_project_creates_versioned_project_state(self):
        state_dir = self.project / ".codex-child-tasks"
        project = json.loads((state_dir / "project.json").read_text())

        self.assertEqual(project["schema_version"], 1)
        self.assertEqual(project["parent_thread_id"], "parent-thread-1")
        self.assertEqual(project["parent_context_revision"], 1)
        self.assertTrue(project["project_id"].startswith("prj_"))
        self.assertEqual(self.state["project_id"], project["project_id"])

    def test_create_is_idempotent_for_same_operation(self):
        first = self.create_child()
        second = self.create_child()

        self.assertEqual(first["child_id"], second["child_id"])
        self.assertEqual(first["status"], "creating")
        children = list((self.project / ".codex-child-tasks" / "children").iterdir())
        self.assertEqual(len(children), 1)

    def test_concurrent_create_is_idempotent(self):
        def create(_):
            return self.create_child(operation_id="op-concurrent-create")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, range(2)))

        self.assertEqual(results[0]["child_id"], results[1]["child_id"])
        children = list((self.project / ".codex-child-tasks" / "children").iterdir())
        self.assertEqual(len(children), 1)

    def test_create_rejects_path_escape(self):
        with self.assertRaises(self.module.ValidationError):
            self.create_child(
                writable_paths=["../other-project"],
                operation_id="op-unsafe",
            )

    def test_bind_thread_moves_child_to_active(self):
        child = self.create_child()

        result = self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-1",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )

        self.assertEqual(result["status"], "active")
        self.assertEqual(result["revision"], 2)
        binding = self.module.read_child_file(
            self.project, child["child_id"], "binding.json"
        )
        self.assertEqual(binding["thread_id"], "child-thread-1")

    def test_pending_client_thread_is_recorded_until_ready(self):
        child = self.create_child(operation_id="op-pending-thread")

        pending = self.module.record_pending_thread(
            self.project,
            child["child_id"],
            client_thread_id="client-thread-1",
            expected_revision=1,
        )
        duplicate = self.module.record_pending_thread(
            self.project,
            child["child_id"],
            client_thread_id="client-thread-1",
            expected_revision=1,
        )

        self.assertEqual(pending["client_thread_id"], "client-thread-1")
        self.assertEqual(duplicate, pending)
        self.assertIn(
            {"child_id": child["child_id"], "issue": "thread_setup_pending"},
            self.module.reconcile_project(self.project),
        )

        status = self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="ready-thread-1",
            host_id="host-returned-by-create",
            workspace_kind="worktree",
            expected_revision=1,
        )
        binding = self.module.read_child_file(
            self.project, child["child_id"], "binding.json"
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(binding["client_thread_id"], "client-thread-1")
        self.assertEqual(binding["host_id"], "host-returned-by-create")

    def test_new_child_defaults_to_collaborative_session(self):
        child = self.create_child()

        contract = self.module.read_child_file(
            self.project, child["child_id"], "contract.json"
        )
        bootstrap = self.module.render_bootstrap(self.project, child["child_id"])

        self.assertEqual(contract["session_mode"], "collaborative")
        self.assertEqual(contract["finalization_policy"], "explicit_close")
        self.assertIn("Remain active after each work turn", bootstrap)
        self.assertIn("Do not create a Git commit", bootstrap)
        self.assertIn("request-close", bootstrap)

    def test_final_handoff_is_rejected_until_close_is_requested(self):
        child = self.create_child(operation_id="op-final-gate")
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-final-gate",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )

        with self.assertRaises(self.module.ValidationError):
            self.module.submit_handoff(
                self.project,
                child["child_id"],
                kind="final",
                payload={
                    "summary": "Premature final",
                    "criteria_results": [
                        {"id": "ac-1", "status": "passed", "evidence": []}
                    ],
                    "changed_files": [],
                    "artifacts": [],
                    "tests": [],
                    "decisions_made": [],
                    "decision_proposals": [],
                    "risks": [],
                    "open_questions": [],
                    "next_steps": [],
                },
                based_on_context_revision=1,
                operation_id="op-premature-final",
                expected_status_revision=2,
            )

    def test_request_close_moves_collaborative_child_to_finalizing(self):
        child = self.create_child(operation_id="op-request-close")
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-close",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )

        status = self.module.request_close(
            self.project,
            child["child_id"],
            expected_revision=2,
            reason="User said 收子任务",
        )

        self.assertEqual(status["status"], "finalizing")
        self.assertEqual(status["revision"], 3)

    def test_stale_status_revision_is_rejected(self):
        child = self.create_child()
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-1",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )

        with self.assertRaises(self.module.ConflictError):
            self.module.transition_child(
                self.project,
                child["child_id"],
                to_status="blocked",
                expected_revision=1,
                reason="Waiting for data",
            )

    def test_generic_transition_cannot_bypass_protocol_gates(self):
        child = self.create_child(operation_id="op-managed-transition")
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-managed",
            host_id="host-1",
            workspace_kind="worktree",
            expected_revision=1,
        )

        for managed_status in ("finalizing", "handoff_submitted", "accepted"):
            with self.subTest(status=managed_status):
                with self.assertRaises(self.module.ValidationError):
                    self.module.transition_child(
                        self.project,
                        child["child_id"],
                        to_status=managed_status,
                        expected_revision=2,
                        reason="Attempted lifecycle bypass",
                    )

    def test_snapshot_joins_contract_binding_status_and_ack(self):
        child = self.create_child()
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-1",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )

        snapshot = self.module.get_child_snapshot(self.project, child["child_id"])

        self.assertEqual(snapshot["contract"]["title"], "Host Agent filter optimization")
        self.assertEqual(snapshot["binding"]["thread_id"], "child-thread-1")
        self.assertEqual(snapshot["status"]["status"], "active")
        self.assertIsNone(snapshot["parent_ack"])

    def test_final_handoff_is_immutable_and_requires_parent_review(self):
        child = self.create_child()
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-1",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )
        payload = {
            "summary": "Implemented the stricter refine gate.",
            "criteria_results": [
                {"id": "ac-1", "status": "passed", "evidence": ["tests/test_gate.py"]}
            ],
            "changed_files": ["host_agent_mining/gate.py"],
            "artifacts": [],
            "tests": [{"command": "pytest -q", "exit_code": 0}],
            "decisions_made": [],
            "decision_proposals": [],
            "risks": [],
            "open_questions": [],
            "next_steps": [],
        }
        self.module.request_close(
            self.project,
            child["child_id"],
            expected_revision=2,
            reason="User said 收子任务",
        )

        handoff = self.module.submit_handoff(
            self.project,
            child["child_id"],
            kind="final",
            payload=payload,
            based_on_context_revision=1,
            operation_id="op-handoff-1",
            expected_status_revision=3,
        )

        self.assertEqual(handoff["handoff_revision"], 1)
        status = self.module.read_child_file(
            self.project, child["child_id"], "child-status.json"
        )
        self.assertEqual(status["status"], "handoff_submitted")
        self.assertNotEqual(status["status"], "accepted")

        duplicate = self.module.submit_handoff(
            self.project,
            child["child_id"],
            kind="final",
            payload=payload,
            based_on_context_revision=1,
            operation_id="op-handoff-1",
            expected_status_revision=3,
        )
        self.assertEqual(duplicate["handoff_revision"], 1)

        changed = dict(payload)
        changed["summary"] = "Different content"
        with self.assertRaises(self.module.ConflictError):
            self.module.submit_handoff(
                self.project,
                child["child_id"],
                kind="final",
                payload=changed,
                based_on_context_revision=1,
                operation_id="op-handoff-1",
                expected_status_revision=3,
            )

    def test_parent_acceptance_is_separate_from_child_submission(self):
        child = self.create_child()
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-1",
            host_id="local",
            workspace_kind="worktree",
            expected_revision=1,
        )
        self.module.request_close(
            self.project,
            child["child_id"],
            expected_revision=2,
            reason="User said 收子任务",
        )
        handoff = self.module.submit_handoff(
            self.project,
            child["child_id"],
            kind="final",
            payload={
                "summary": "Done",
                "criteria_results": [{"id": "ac-1", "status": "passed", "evidence": []}],
                "changed_files": [],
                "artifacts": [],
                "tests": [],
                "decisions_made": [],
                "decision_proposals": [],
                "risks": [],
                "open_questions": [],
                "next_steps": [],
            },
            based_on_context_revision=1,
            operation_id="op-handoff-accept",
            expected_status_revision=3,
        )

        ack = self.module.review_handoff(
            self.project,
            child["child_id"],
            handoff_revision=handoff["handoff_revision"],
            decision="accepted",
            reason="Evidence verified",
            expected_status_revision=4,
        )

        self.assertEqual(ack["decision"], "accepted")
        status = self.module.read_child_file(
            self.project, child["child_id"], "child-status.json"
        )
        self.assertEqual(status["status"], "accepted")

    def test_parent_cannot_accept_an_old_checkpoint(self):
        child = self.create_child(operation_id="op-review-final-only")
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-review-final",
            host_id="host-1",
            workspace_kind="worktree",
            expected_revision=1,
        )
        payload = {
            "summary": "Checkpoint",
            "criteria_results": [
                {"id": "ac-1", "status": "partial", "evidence": []}
            ],
            "changed_files": [],
            "artifacts": [],
            "tests": [],
            "decisions_made": [],
            "decision_proposals": [],
            "risks": [],
            "open_questions": [],
            "next_steps": [],
        }
        checkpoint = self.module.submit_handoff(
            self.project,
            child["child_id"],
            kind="checkpoint",
            payload=payload,
            based_on_context_revision=1,
            operation_id="op-checkpoint-before-final",
            expected_status_revision=2,
        )
        self.module.request_close(
            self.project,
            child["child_id"],
            expected_revision=3,
            reason="User said 收子任务",
        )
        final_payload = dict(payload)
        final_payload["summary"] = "Final"
        final_payload["criteria_results"] = [
            {"id": "ac-1", "status": "passed", "evidence": []}
        ]
        self.module.submit_handoff(
            self.project,
            child["child_id"],
            kind="final",
            payload=final_payload,
            based_on_context_revision=1,
            operation_id="op-final-after-checkpoint",
            expected_status_revision=4,
        )

        with self.assertRaises(self.module.ValidationError):
            self.module.review_handoff(
                self.project,
                child["child_id"],
                handoff_revision=checkpoint["handoff_revision"],
                decision="accepted",
                reason="Wrong revision",
                expected_status_revision=5,
            )

    def test_handoff_rejects_uncontracted_context_revision(self):
        child = self.create_child(operation_id="op-context-revision")
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-context",
            host_id="host-1",
            workspace_kind="worktree",
            expected_revision=1,
        )
        with self.assertRaises(self.module.ValidationError):
            self.module.submit_handoff(
                self.project,
                child["child_id"],
                kind="checkpoint",
                payload={
                    "summary": "Invalid context",
                    "criteria_results": [],
                    "changed_files": [],
                    "artifacts": [],
                    "tests": [],
                    "decisions_made": [],
                    "decision_proposals": [],
                    "risks": [],
                    "open_questions": [],
                    "next_steps": [],
                },
                based_on_context_revision=999,
                operation_id="op-invalid-context-handoff",
                expected_status_revision=2,
            )

    def test_concurrent_handoffs_do_not_overwrite_a_revision(self):
        child = self.create_child(operation_id="op-concurrent-handoff-child")
        self.module.bind_thread(
            self.project,
            child["child_id"],
            thread_id="child-thread-concurrent-handoff",
            host_id="host-1",
            workspace_kind="worktree",
            expected_revision=1,
        )
        payload = {
            "summary": "Concurrent checkpoint",
            "criteria_results": [],
            "changed_files": [],
            "artifacts": [],
            "tests": [],
            "decisions_made": [],
            "decision_proposals": [],
            "risks": [],
            "open_questions": [],
            "next_steps": [],
        }

        def submit(operation_id):
            try:
                result = self.module.submit_handoff(
                    self.project,
                    child["child_id"],
                    kind="checkpoint",
                    payload=payload,
                    based_on_context_revision=1,
                    operation_id=operation_id,
                    expected_status_revision=2,
                )
                return ("ok", result["handoff_revision"])
            except self.module.ConflictError:
                return ("conflict", None)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, ("op-concurrent-a", "op-concurrent-b")))

        self.assertEqual(sorted(result[0] for result in results), ["conflict", "ok"])
        handoffs = list(
            (self.project / ".codex-child-tasks" / "children" / child["child_id"] / "handoffs").glob("*.json")
        )
        self.assertEqual(len(handoffs), 1)

    def test_reconcile_reports_unbound_visible_task(self):
        child = self.create_child()

        issues = self.module.reconcile_project(self.project)

        self.assertIn(
            {"child_id": child["child_id"], "issue": "thread_not_bound"},
            issues,
        )

    def test_bootstrap_contains_contract_but_not_parent_transcript(self):
        child = self.create_child()

        bootstrap = self.module.render_bootstrap(self.project, child["child_id"])

        self.assertIn("Improve the refine quality gate", bootstrap)
        self.assertIn("ac-1", bootstrap)
        self.assertIn(str(self.project.resolve()), bootstrap)
        self.assertIn(".codex-child-tasks", bootstrap)
        self.assertIn("do not replace this with the child worktree root", bootstrap)
        self.assertNotIn("parent transcript", bootstrap.lower())
        self.assertNotIn("conversation history", bootstrap.lower())

    def test_context_revision_update_is_checked_and_reported(self):
        child = self.create_child()

        updated = self.module.update_parent_context_revision(
            self.project,
            expected_revision=1,
        )

        self.assertEqual(updated["parent_context_revision"], 2)
        with self.assertRaises(self.module.ConflictError):
            self.module.update_parent_context_revision(
                self.project,
                expected_revision=1,
            )
        self.assertIn(
            {"child_id": child["child_id"], "issue": "parent_context_stale"},
            self.module.reconcile_project(self.project),
        )


if __name__ == "__main__":
    unittest.main()
