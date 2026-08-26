#!/usr/bin/env python3
from copy import deepcopy
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def register_resource(registration, registry):
    resource_id = registration['resourceId']
    if resource_id in registry:
        raise ValueError(f'resource already registered: {resource_id}')
    record = deepcopy(registration)
    record['status'] = 'registered'
    registry[resource_id] = record
    return record


def _matches(policy, resource):
    if not policy.get('enabled', False):
        return False
    scope = policy.get('scope', {})
    tests = []
    if scope.get('resourceIds'):
        tests.append(resource['resourceId'] in scope['resourceIds'])
    if scope.get('resourceClasses'):
        tests.append(resource['resourceClass'] in scope['resourceClasses'])
    if scope.get('applications'):
        tests.append(resource['sourceApplication'] in scope['applications'])
    if scope.get('preservationTiers'):
        tests.append(resource['preservationTier'] in scope['preservationTiers'])
    return all(tests) if tests else True


def resolve_policy(resource, policies, parent_resources=None, resolved_at=None):
    resolved_at = resolved_at or _now()
    by_id = {p['policyId']: p for p in policies}
    path = []

    explicit = resource.get('explicitPolicyId')
    if explicit:
        policy = by_id.get(explicit)
        if not policy or not policy.get('enabled', False):
            raise ValueError(f'explicit policy unavailable: {explicit}')
        path.append(f'explicit:{explicit}')
    else:
        policy = None
        if resource.get('parentResourceId') and parent_resources:
            parent = parent_resources.get(resource['parentResourceId'])
            if parent and parent.get('effectivePolicyId') in by_id:
                candidate = by_id[parent['effectivePolicyId']]
                if candidate.get('enabled', False):
                    policy = candidate
                    path.append(f'parent:{parent["resourceId"]}:{candidate["policyId"]}')
        if policy is None:
            candidates = [p for p in policies if _matches(p, resource)]
            if not candidates:
                raise ValueError('no applicable protection policy')
            # Deterministic precedence: resource ID scope > class > application > tier > default, then policyId.
            def rank(p):
                s = p.get('scope', {})
                specificity = (
                    4 if resource['resourceId'] in s.get('resourceIds', []) else
                    3 if resource['resourceClass'] in s.get('resourceClasses', []) else
                    2 if resource['sourceApplication'] in s.get('applications', []) else
                    1 if resource['preservationTier'] in s.get('preservationTiers', []) else 0
                )
                return (-specificity, p['policyId'])
            policy = sorted(candidates, key=rank)[0]
            path.append(f'scope:{policy["policyId"]}')

    result = {
        'schemaVersion': '1.0.0',
        'resourceId': resource['resourceId'],
        'resolvedAt': resolved_at,
        'policyId': policy['policyId'],
        'resolutionPath': path,
        'objectives': deepcopy(policy['objectives']),
        'retention': deepcopy(policy['retention']),
        'verification': deepcopy(policy['verification']),
        'placement': deepcopy(policy.get('placement', {})),
        'authorization': deepcopy(policy.get('authorization', {})),
        'overridesApplied': [],
    }
    return result


def evaluate_retention(resource_id, effective_policy, privacy=None, hold=None, evaluated_at=None):
    evaluated_at = evaluated_at or _now()
    privacy = privacy or {}
    hold = hold or {}
    reasons, conflicts = [], []

    if hold.get('active'):
        reasons.append('legal or operational hold is active')
        if privacy.get('deleteRequired'):
            conflicts.append('privacy deletion conflicts with active hold')
            decision, authority = 'conflict', 'combined'
        else:
            decision, authority = 'hold', 'legal_or_operational_hold'
    elif privacy.get('deleteRequired'):
        if effective_policy['retention'].get('privacyDeletionOverrides', True):
            decision, authority = 'delete', 'privacy_shield'
            reasons.append('Privacy Shield deletion requirement overrides ordinary retention')
        else:
            decision, authority = 'conflict', 'combined'
            conflicts.append('privacy deletion blocked by policy override setting')
            reasons.append('retention authority conflict requires resolution')
    elif effective_policy['retention']['mode'] == 'ephemeral':
        decision, authority = 'expire', 'everkeep_policy'
        reasons.append('effective policy is ephemeral')
    else:
        decision, authority = 'retain', 'everkeep_policy'
        reasons.append('effective Everkeep retention policy permits retention')

    return {
        'schemaVersion': '1.0.0',
        'resourceId': resource_id,
        'evaluatedAt': evaluated_at,
        'decision': decision,
        'authority': authority,
        'effectiveUntil': None,
        'reasons': reasons,
        'conflicts': conflicts,
    }


def ingest_recovery_point(recovery_point, store):
    rp_id = recovery_point['recoveryPointId']
    if rp_id in store:
        raise ValueError(f'recovery point already exists: {rp_id}')
    resource_id = recovery_point['resourceId']
    store[rp_id] = deepcopy(recovery_point)
    return store[rp_id]


def project_recovery_center(resources, effective_policies, recovery_points, readiness_by_resource):
    points_by_resource = {}
    for rp in recovery_points.values():
        points_by_resource.setdefault(rp['resourceId'], []).append(rp)

    items = []
    for resource_id in sorted(resources):
        resource = resources[resource_id]
        policy = effective_policies.get(resource_id)
        points = sorted(points_by_resource.get(resource_id, []), key=lambda x: x.get('createdAt', ''), reverse=True)
        latest = points[0] if points else None
        readiness = readiness_by_resource.get(resource_id, {'state': 'unknown', 'score': 0, 'checks': {}, 'blockers': ['readiness evidence unavailable'], 'warnings': []})
        items.append({
            'resourceId': resource_id,
            'sourceApplication': resource['sourceApplication'],
            'resourceClass': resource['resourceClass'],
            'preservationTier': resource['preservationTier'],
            'protected': bool(policy and latest),
            'policyId': policy['policyId'] if policy else None,
            'readiness': readiness,
            'latestRecoveryPointId': latest['recoveryPointId'] if latest else None,
            'latestRecoveryPointCreatedAt': latest.get('createdAt') if latest else None,
            'recoveryPointCount': len(points),
        })
    return {'schemaVersion': '1.0.0', 'generatedAt': _now(), 'items': items, 'count': len(items)}
