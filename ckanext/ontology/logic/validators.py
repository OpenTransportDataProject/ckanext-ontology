import logging

from ckan.lib.navl.dictization_functions import Invalid
from ckan import model
from ckanext.ontology.plugin import DATASET_TYPE_NAME

log = logging.getLogger(__name__)



def ontology_validator(key, data, errors, context):
    '''
        Validate the ontology
        Check that the ontology is a valid rdf file.
    '''

    return data[key]


def dataset_type_exists(value):
    if value != DATASET_TYPE_NAME:
        value = DATASET_TYPE_NAME
    return value
