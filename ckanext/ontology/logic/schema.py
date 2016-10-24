from ckan.logic.schema import default_extras_schema
from ckan.logic.validators import package_id_exists, name_validator, package_name_validator, boolean_validator
from ckan.logic.converters import convert_to_extras, convert_from_extras
from ckan.lib.navl.validators import ignore_missing, not_empty, ignore
from ckanext.ontology.logic.validators import ontology_validator, dataset_type_exists


def ontology_schema():

    schema = {
        'id': [ignore_missing, unicode, package_id_exists],
        'type': [dataset_type_exists, unicode],
        'name': [not_empty, unicode, name_validator, package_name_validator],
        'description': [ignore_missing, unicode],
        'active': [ignore_missing, boolean_validator],
        'ontology': [ignore_missing, ontology_validator, convert_to_extras],
        'extras': default_extras_schema()
    }

    extras_schema = default_extras_schema()
    extras_schema['__extras'] = [ignore]
    schema['extras'] = extras_schema

    return schema


def ontology_create_package_schema():

    schema = ontology_schema()
    schema['save'] = [ignore]
    schema.pop("id")

    return schema


def ontology_update_package_schema():

    schema = ontology_create_package_schema()
    return schema


def ontology_show_package_schema():

    schema = ontology_schema()
    schema.update({
        'type': [convert_from_extras, ignore_missing],
        'active': [],
        'name': [],
        'description': [],
        'ontology': [],
        'revision_timestamp': [ignore_missing],
        'tracking_summary': [ignore_missing],
    })

    return schema
