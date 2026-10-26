"""Я проверяю границы оркестрации без сервера Prefect и без подключения к БД."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from commerceguard.file_contracts import FileInputError
from commerceguard.ingest_journal import PublicationFailure, Rejection
from commerceguard.pipeline import (PipelineError, choose_cutoff, execute_step, freeze_packages,
                                    launch_pipeline, local_environment, prepare_step, publish_step)
from commerceguard.pipeline_dbt import connection_profile
from commerceguard.run_execution import RunExecutionError
from commerceguard.sample_data import generate_inputs


class Pipeline(unittest.TestCase):
    def config(self, inputs):
        return dict(merchant='M01', **{source+'_'+kind: str(inputs/(source+suffix))
                                     for source in ('oms','psp')
                                     for kind,suffix in (('manifest','.manifest.json'),('data','.csv' if source=='oms' else '.jsonl'))})

    def test_retry_snapshots_do_not_follow_changed_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); generate_inputs(root/'input'); (root/'job').mkdir()
            config=self.config(root/'input'); saved=freeze_packages(config,root/'job')
            before=Path(saved['psp_data']).read_bytes()
            Path(config['psp_data']).write_bytes(b'changed')
            self.assertEqual(Path(saved['psp_data']).read_bytes(),before)
            self.assertNotEqual(saved['psp_data'],config['psp_data'])

    def test_preflight_rejects_cross_merchant_and_corruption(self):
        for scenario in ('merchant','bytes'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); generate_inputs(root/'input'); (root/'job').mkdir()
                config=self.config(root/'input')
                if scenario=='merchant': config['merchant']='OTHER'
                else: Path(config['psp_data']).write_bytes(b'bad')
                with self.assertRaises((PipelineError,FileInputError)):
                    freeze_packages(config,root/'job')

    def test_only_known_ingest_locks_are_retryable(self):
        for code in ('MERCHANT_BUSY','SCHEMA_BUSY','PSP_CONFLICT','DATABASE_UNCONFIRMED','UNEXPECTED_ERROR'):
            with self.subTest(code=code):
                failure=PublicationFailure(UUID(int=1),Rejection('failed','infrastructure',code),'recorded')
                with patch('commerceguard.pipeline.publish_input',side_effect=failure):
                    with self.assertRaises(PipelineError) as found:
                        publish_step('oms',dict(oms_manifest='m',oms_data='d',raw_root='r',dsn_env='D'))
                self.assertEqual(found.exception.retryable,code in ('MERCHANT_BUSY','SCHEMA_BUSY'))

    def test_execute_only_run_busy_retries(self):
        for code in ('RUN_BUSY','EXECUTION_UNCONFIRMED','MANIFEST_OR_ENGINE_MISMATCH'):
            with patch('commerceguard.pipeline.execute_run',side_effect=RunExecutionError(code)):
                with self.assertRaises(PipelineError) as found:
                    execute_step(str(UUID(int=1)),'D')
            self.assertEqual(found.exception.retryable,code=='RUN_BUSY')

    def test_opaque_exception_never_reaches_pipeline_error(self):
        with patch('commerceguard.pipeline.execute_run',side_effect=ValueError('private credential')):
            with self.assertRaises(PipelineError) as found:
                execute_step(str(UUID(int=1)),'D')
        self.assertNotIn('private',str(found.exception))
        self.assertFalse(found.exception.retryable)

    def test_explicit_cutoff_is_not_replaced_with_clock(self):
        self.assertEqual(choose_cutoff({'as_of':'2026-10-26T12:00:00Z'}),'2026-10-26T12:00:00Z')

    def test_cloud_environment_is_not_inherited(self):
        with patch.dict(os.environ,{'PREFECT_API_URL':'https://invalid.example','PREFECT_API_KEY':'private',
                                    'PREFECT_PROFILES_PATH':'outside','MY_PIPELINE_DSN':'local'}):
            value=local_environment(Path('/tmp/job'))
        self.assertNotIn('PREFECT_API_URL',value)
        self.assertNotIn('PREFECT_API_KEY',value)
        self.assertEqual(value['MY_PIPELINE_DSN'],'local')
        self.assertEqual(value['PREFECT_PROFILES_PATH'],'/tmp/job/profiles.toml')
        self.assertEqual(value['PREFECT_SERVER_ANALYTICS_ENABLED'],'false')

    def test_prepare_cannot_silently_select_other_inputs(self):
        prepared=SimpleNamespace(run_id=str(UUID(int=1)),as_of='2026-10-26T12:00:00Z',duplicate_manifest=True)
        with patch('commerceguard.pipeline.prepare_run',return_value=prepared), \
             patch('commerceguard.run_plans.show_run',return_value={'manifest':{'inputs':[{'batch_id':'A'}]}}):
            self.assertEqual(prepare_step({'merchant':'M01','dsn_env':'D'},prepared.as_of,[{'batch_id':'A'}])['run_id'],prepared.run_id)
            with self.assertRaisesRegex(PipelineError,'PIPELINE_INPUT_NOT_SELECTED'):
                prepare_step({'merchant':'M01','dsn_env':'D'},prepared.as_of,[{'batch_id':'B'}])

    def test_dbt_uses_same_explicit_connection_without_password_in_profile(self):
        with patch.dict(os.environ,{},clear=False):
            profile=connection_profile('host=/tmp/cg user=example dbname=commerceguard password=private port=55432')
            output=profile['commerceguard_analytics']['outputs']['local']
            self.assertEqual((output['host'],output['port'],output['dbname']),('/tmp/cg',55432,'commerceguard'))
            self.assertNotIn('private',json.dumps(profile))
            self.assertEqual(os.environ['DBT_ENV_SECRET_CG_PIPELINE_PASSWORD'],'private')

    def test_dbt_refuses_ambiguous_or_different_database(self):
        for dsn in ('service=opaque','host=a,b user=u dbname=commerceguard','host=a user=u dbname=other',
                    'host=a user=u dbname=commerceguard options=unsafe','host=a user=u dbname=commerceguard port=0'):
            with self.subTest(dsn=dsn),self.assertRaises(ValueError): connection_profile(dsn)

    def test_error_and_resume_arguments_are_bounded(self):
        with self.assertRaises(ValueError): PipelineError('fake','bad message')
        with patch.dict(os.environ,{'PIPELINE_TEST_DSN':'unused'}):
            with self.assertRaisesRegex(PipelineError,'PIPELINE_RUN_ID'):
                launch_pipeline(mode='resume',analytics_python=Path(os.sys.executable),dsn_env='PIPELINE_TEST_DSN',run_id='bad')
