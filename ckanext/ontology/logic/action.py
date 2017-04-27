
import logging

import ckan

from ckan.plugins import toolkit

from ckanext.ontology.plugin import DATASET_TYPE_NAME
from ckanext.ontology.model import OntologyObject
from ckanext.ontology.model import OntologyObject, NodeObject, DatasetOntologyRelation, SemanticSearchResults


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

# Delete an ontology with nodes and annotations belonging to this ontology
@toolkit.side_effect_free
def ontology_delete(context, data_dict=None):
    #if ('id' not in data_dict) or ('name' not in data_dict):
    if 'id' not in data_dict:
        log.info('No ontology specified.')
        return {'result': 'No ontology specified.'}
    else:
        log.info('To delete ontology with id: %s', data_dict['id'])

    ontology = OntologyObject.get(key=data_dict['id'])
    if ontology is None:
        log.info('No ontology found with the id: %s', data_dict['id'])
        return {'result': 'No ontology found with id: ' + data_dict['id']}
    else:
        log.debug('Found an ontology with name: %s', ontology.as_simple_dict().get('name'))
        # remove datasets annotated with this ontology
        #relations = DatasetOntologyRelation.get_all(key=data_dict['id'], attr='ontology_id')
        #log.debug('The number of relations for this ontology is %r', len(relations))

        DatasetOntologyRelation.delete_all(key=data_dict['id'], attr='ontology_id')
        #relations = DatasetOntologyRelation.get_all(key=data_dict['id'], attr='ontology_id')
        #log.info('The number of relations for this ontology after delete is %r', len(relations))

        # remove all nodes for this ontology
        NodeObject.delete_all(key=data_dict['id'], attr='ontology_id')

        # remove the ontology itself - the dataset
        #toolkit.get_action('package_delete')(context, data_dict)
        toolkit.get_action('dataset_purge')(context, data_dict)

        # remove the ontology from table
        OntologyObject.delete(key=data_dict['id'])

        return {'result': 'successfully delete an ontology with annotations and nodes', 'name': ontology.as_simple_dict().get('name')}
