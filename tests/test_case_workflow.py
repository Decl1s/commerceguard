"""Я проверяю identity команды и границы текста до входа в транзакцию."""
import unittest
from uuid import uuid4
from commerceguard.case_workflow import command
from commerceguard.workbench_store import WorkbenchError

class WorkflowTests(unittest.TestCase):
    def call(self,**changes):
        return command(**{'key':'a'*64,'action':'comment','request_id':str(uuid4()),'expected_version':0,'expected_revision':1,'expected_run_id':str(uuid4()),'value':'Разбор синтетического случая',**changes})
    def test_value_changes_identity(self):
        rid=str(uuid4());run=str(uuid4())
        self.assertNotEqual(self.call(request_id=rid,expected_run_id=run,value='one')[2],self.call(request_id=rid,expected_run_id=run,value='two')[2])
    def test_empty_comment(self):
        for value in ['  ','a'*2001,'x\x00y']:
            with self.assertRaises(WorkbenchError):self.call(value=value)
    def test_boolean_version_rejected(self):
        with self.assertRaises(WorkbenchError):self.call(expected_version=True)
    def test_unsafe_assignee(self):
        with self.assertRaises(WorkbenchError):self.call(action='assign',value='<script>')
    def test_bad_uuid(self):
        with self.assertRaises(WorkbenchError):self.call(request_id='not-uuid')

    def test_decision_requires_reason(self):
        with self.assertRaisesRegex(WorkbenchError,'REASON_REQUIRED'):self.call(action='close')
    def test_decision_reason_context(self):
        with self.assertRaisesRegex(WorkbenchError,'REASON_CONTEXT'):self.call(reason_code='new_evidence')
    def test_reason_is_part_of_identity(self):
        rid=str(uuid4());run=str(uuid4())
        a=self.call(action='close',reason_code='source_corrected',request_id=rid,expected_run_id=run)
        b=self.call(action='close',reason_code='accepted_difference',request_id=rid,expected_run_id=run)
        self.assertNotEqual(a[2],b[2])
    def test_reopen_rejects_close_reason(self):
        with self.assertRaises(WorkbenchError):self.call(action='reopen',reason_code='source_corrected')
