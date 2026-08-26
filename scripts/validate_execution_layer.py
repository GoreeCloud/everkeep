#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / 'scripts' / 'execution_layer.py'
    spec = importlib.util.spec_from_file_location('execution_layer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path):
    return json.loads(path.read_text())


def assert_schema(path, required):
    data = load_json(path)
    assert data['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert data['type'] == 'object'
    assert set(required).issubset(set(data.get('required', [])))


def main():
    contracts = ROOT / 'contracts'
    assert_schema(contracts / 'everkeep.resource-registration.schema.json', {'schemaVersion','registrationId','resourceId','sourceApplication','resourceClass','owner','preservationTier','registeredAt'})
    assert_schema(contracts / 'everkeep.effective-policy.schema.json', {'schemaVersion','resourceId','resolvedAt','policyId','resolutionPath','objectives','retention','verification'})
    assert_schema(contracts / 'everkeep.retention-decision.schema.json', {'schemaVersion','resourceId','evaluatedAt','decision','authority','reasons'})
    assert_schema(contracts / 'everkeep.recovery-center.query.schema.json', {'schemaVersion','queryId','requestedAt','filters'})

    m = load_module()
    registry = {}
    resource = {
        'schemaVersion':'1.0.0','registrationId':'reg-1','resourceId':'doc-1','sourceApplication':'goreecloud-documents',
        'resourceClass':'document','owner':'user-1','preservationTier':'protected','registeredAt':'2026-08-26T18:00:00Z'
    }
    m.register_resource(resource, registry)
    try:
        m.register_resource(resource, registry)
        raise AssertionError('duplicate registration must fail')
    except ValueError:
        pass

    policies = [
        {
            'schemaVersion':'1.0.0','policyId':'default-protected','name':'Protected default','enabled':True,
            'scope':{'preservationTiers':['protected']},
            'objectives':{'rpoSeconds':3600,'rtoSeconds':7200,'minimumCopies':2,'minimumFailureDomains':2},
            'retention':{'mode':'rolling','minimumSeconds':86400,'privacyDeletionOverrides':True},
            'verification':{'integrityIntervalSeconds':3600,'restoreTestIntervalSeconds':86400}
        },
        {
            'schemaVersion':'1.0.0','policyId':'documents-specific','name':'Documents','enabled':True,
            'scope':{'applications':['goreecloud-documents']},
            'objectives':{'rpoSeconds':900,'rtoSeconds':3600,'minimumCopies':3,'minimumFailureDomains':2},
            'retention':{'mode':'rolling','minimumSeconds':172800,'privacyDeletionOverrides':True},
            'verification':{'integrityIntervalSeconds':1800,'restoreTestIntervalSeconds':43200}
        }
    ]
    effective = m.resolve_policy(resource, policies, resolved_at='2026-08-26T18:10:00Z')
    assert effective['policyId'] == 'documents-specific'

    retain = m.evaluate_retention('doc-1', effective, evaluated_at='2026-08-26T18:20:00Z')
    assert retain['decision'] == 'retain'
    delete = m.evaluate_retention('doc-1', effective, privacy={'deleteRequired': True}, evaluated_at='2026-08-26T18:21:00Z')
    assert delete['decision'] == 'delete' and delete['authority'] == 'privacy_shield'
    conflict = m.evaluate_retention('doc-1', effective, privacy={'deleteRequired': True}, hold={'active': True}, evaluated_at='2026-08-26T18:22:00Z')
    assert conflict['decision'] == 'conflict'

    recovery_points = {}
    rp = {
        'schemaVersion':'1.0.0','recoveryPointId':'rp-1','resourceId':'doc-1','createdAt':'2026-08-26T18:30:00Z',
        'type':'snapshot','status':'available','copies':[],'integrity':{'status':'verified'},'recoveryEligibility':'eligible'
    }
    m.ingest_recovery_point(rp, recovery_points)
    try:
        m.ingest_recovery_point(rp, recovery_points)
        raise AssertionError('duplicate recovery point must fail')
    except ValueError:
        pass

    projection = m.project_recovery_center(registry, {'doc-1':effective}, recovery_points, {'doc-1':{'state':'recovery_ready','score':100,'checks':{},'blockers':[],'warnings':[]}})
    assert projection['count'] == 1
    item = projection['items'][0]
    assert item['protected'] is True
    assert item['policyId'] == 'documents-specific'
    assert item['latestRecoveryPointId'] == 'rp-1'
    assert item['readiness']['state'] == 'recovery_ready'

    print('Everkeep execution layer validation passed')


if __name__ == '__main__':
    main()
