
import logging

import ckan

from ckan.plugins import toolkit

from ckanext.ontology.plugin import DATASET_TYPE_NAME
from ckanext.ontology.model import OntologyObject

log = logging.getLogger(__name__)

_validate = ckan.lib.navl.dictization_functions.validate
check_access = toolkit.check_access


class InactiveSource(Exception):
    pass


def ontology_create(context, data_dict):
    ''' Create a new ontology object
    :type guid: string (optional)
    :type content: string (optional)
    :type job_id: string
    :type source_id: string (optional)
    :type package_id: string (optional)
    :type extras: dict (optional)
    '''
    model = context['model']
    user = context['user']

    log.info('Creating ontology: %r', data_dict)

    data_dict['type'] = DATASET_TYPE_NAME

    ontology = toolkit.get_action('package_create')(context, data_dict)

    obj = OntologyObject(
        guid=ontology.get('guid'),
        ontology=ontology.get('ontology'),
    )

    obj.save()
    return ontology
