"""Preimplementation behavioral-validation harness. NOT a production Apollo/AI loader."""
from dataclasses import dataclass
from typing import Callable

class SwitchRejected(Exception):
    pass

@dataclass(frozen=True)
class Session:
    product_id: str
    version: str
    brain_id: str
    ui_schema_id: str
    context: tuple = ()

class SwitchController:
    def __init__(self, registry: dict, fetch_exact: Callable, validate: Callable):
        self.registry = registry
        self.fetch_exact = fetch_exact
        self.validate = validate
        self.active = None

    def switch(self, product_id: str):
        # Pending selection never mutates the active session.
        entries = [p for p in self.registry['products'] if p['product_id'] == product_id]
        if len(entries) != 1:
            raise SwitchRejected('UNKNOWN_OR_DUPLICATE_PRODUCT')
        p = entries[0]
        if not (p.get('approved') is True and p.get('activation_enabled') is True):
            raise SwitchRejected('NOT_APPROVED')
        if not p.get('version') or not p.get('apollo_spec_document_id'):
            raise SwitchRejected('INCOMPLETE_REGISTRY_ENTRY')
        artifact = self.fetch_exact(p['apollo_spec_document_id'])
        if artifact['product_id'] != product_id or artifact['version'] != p['version']:
            raise SwitchRejected('ARTIFACT_IDENTITY_MISMATCH')
        if not self.validate(artifact):
            raise SwitchRejected('INVALID_ARTIFACT')
        candidate = Session(product_id, p['version'], artifact['brain_id'], artifact['ui_schema_id'])
        self.active = candidate  # Atomic activation only after all validation succeeds.
        return candidate


def run_tests():
    registry = {'products': [
        {'product_id': 'hippocrates_labs', 'version': '1.0.0', 'approved': True, 'activation_enabled': True, 'apollo_spec_document_id': 'doc-h'},
        {'product_id': 'calculator', 'version': '1.0.0', 'approved': True, 'activation_enabled': True, 'apollo_spec_document_id': 'doc-c'}]}
    fixtures = {
        'doc-h': {'product_id': 'hippocrates_labs', 'version': '1.0.0', 'brain_id': 'brain-h', 'ui_schema_id': 'ui-h'},
        'doc-c': {'product_id': 'calculator', 'version': '1.0.0', 'brain_id': 'brain-c', 'ui_schema_id': 'ui-c'}}
    controller = SwitchController(registry, fixtures.__getitem__, lambda x: bool(x.get('brain_id') and x.get('ui_schema_id')))
    assert controller.switch('hippocrates_labs').brain_id == 'brain-h'
    assert controller.switch('calculator').brain_id == 'brain-c'
    assert controller.active.context == ()
    previous = controller.active
    for bad in ('unknown', 'calculator_typo'):
        try: controller.switch(bad); assert False
        except SwitchRejected: assert controller.active is previous
    registry['products'][1]['approved'] = False
    try: controller.switch('calculator'); assert False
    except SwitchRejected: assert controller.active is previous
    registry['products'][1]['approved'] = True
    fixtures['doc-h']['version'] = '2.0.0'
    try: controller.switch('hippocrates_labs'); assert False
    except SwitchRejected: assert controller.active is previous
    fixtures['doc-h']['version'] = '1.0.0'
    fixtures['doc-h']['brain_id'] = ''
    try: controller.switch('hippocrates_labs'); assert False
    except SwitchRejected: assert controller.active is previous
    print('PASS: successful A->F, isolated context, unknown ID, unapproved, version mismatch, invalid brain; failed switches preserve active session')

if __name__ == '__main__':
    run_tests()
