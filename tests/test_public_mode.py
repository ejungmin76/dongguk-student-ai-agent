from django.test import SimpleTestCase

from agent.public_mode import PUBLIC_CAPABILITIES, assert_public_plan
from agent.schemas import Capability, ExecutionPlan, ExecutionStep


class PublicModeTests(SimpleTestCase):
    def test_public_mode_excludes_every_personal_academic_capability(self):
        self.assertNotIn(Capability.STUDENT_PROFILE, PUBLIC_CAPABILITIES)
        self.assertNotIn(Capability.ACADEMIC_RECORDS, PUBLIC_CAPABILITIES)
        self.assertNotIn(Capability.CURRENT_SCHEDULE, PUBLIC_CAPABILITIES)

    def test_public_mode_rejects_plan_with_personal_tool(self):
        plan = ExecutionPlan(steps=[ExecutionStep(step_id="profile", capability=Capability.STUDENT_PROFILE, purpose="개인 프로필 조회")], rationale="개인 정보가 필요하다.")
        with self.assertRaises(PermissionError):
            assert_public_plan(plan)
