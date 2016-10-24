from pylons import request
from ckan import logic
from ckan import model
import ckan.lib.helpers as h
import ckan.plugins as p

from ckanext.ontology.plugin import DATASET_TYPE_NAME

def package_list_for_ontology(source_id):
    '''
    Creates a dataset list with the ones belonging to a particular harvest
    source.
    It calls the package_list snippet and the pager.
    '''


    return h.snippet('snippets/package_list_empty.html')