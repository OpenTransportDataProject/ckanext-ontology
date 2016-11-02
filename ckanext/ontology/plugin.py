from logging import getLogger
import ckan.plugins as plugins
from ckan.lib.plugins import DefaultDatasetForm
import ckan.plugins.toolkit as toolkit
from ckanext.ontology.model import setup as model_setup
from ckanext.ontology.model import OntologyObject, NodeObject
from ckan.model.types import make_uuid

from rdflib import Graph
import logging
import urllib2

logging.basicConfig()
log = getLogger(__name__)
DATASET_TYPE_NAME = "ontology"


class OntologyPlugin(plugins.SingletonPlugin, DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes,inherit=True)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    startup = False

    ## IRoutes
    def before_map(self, map):
        map.connect('create_ontology',
            '/dataset/ontology/add/{id}',
    		controller='ckanext.ontology.controller:OntologyController',
    		action='create_ontology'
        )
    	map.connect('dataset_edit_ontology',
            '/dataset/ontology/edit/{id}',
    		controller='ckanext.ontology.controller:OntologyController',
            action='edit_ontology',
            ckan_icon='edit'
        )
    	map.connect('dataset_ontology',
            '/dataset/ontology/{id}',
        	controller='ckanext.ontology.controller:OntologyController',
            action='show_ontology',
            ckan_icon='info-sign'
        )

        return map

    def after_map(self, map):
        map.connect('create_ontology',
            '/dataset/ontology/add/{id}',
            controller='ckanext.ontology.controller:OntologyController',
            action='create_ontology'
        )
        map.connect('dataset_edit_ontology',
            '/dataset/ontology/edit/{id}',
            controller='ckanext.ontology.controller:OntologyController',
            action='edit_ontology',
            ckan_icon='edit'
        )
        map.connect('dataset_ontology',
            '/dataset/ontology/{id}',
            controller='ckanext.ontology.controller:OntologyController',
            action='show_ontology',
            ckan_icon='info-sign'
        )

        return map

    ## IPackageController
    def after_create(self, context, data_dict):
        if 'type' in data_dict and data_dict['type'] == DATASET_TYPE_NAME and not self.startup:
            # Create an actual Ontology object
            _create_ontology_object(context, data_dict)

    ## IActions
    def get_actions(self):
        from ckanext.ontology.logic import get as ontology_get
        return {
            'list_ontologies': ontology_get.get_ontology_objects,
            'get_ontology': ontology_get.get_ontology,
            'list_json_ontologies': ontology_get.list_ontologies_json,
            'get_json_ontology': ontology_get.get_ontology_json,
            'dataset_ontologies': ontology_get.dataset_node_relations,
            'list_nodes': ontology_get.get_node_objects,
            'get_node': ontology_get.get_node,
            'search_from_node': ontology_get.search_from_node,
            'semantic_search': ontology_get.semantic_search
        }

    # IAuthFunctions

    def get_auth_functions(self):
        from ckanext.ontology.logic import auth as ontology_auth
        return {
            'ontology_create': ontology_auth.ontology_create
        }

    # ITemplateHelpers
    def get_helpers(self):
        from ckanext.ontology.logic import helpers as ontology_helpers
        return {
            'package_list_for_ontology': ontology_helpers.package_list_for_ontology
        }

    # IDatasetForm

    def is_fallback(self):
        return False

    def package_types(self):
        return [DATASET_TYPE_NAME]

    def package_form(self):
        return 'ontology/new_ontology_form.html'

    def search_template(self):
        return 'ontology/search.html'

    def read_template(self):
        return 'ontology/read.html'

    def new_template(self):
        return 'ontology/new.html'

    def edit_template(self):
        return 'ontology/edit.html'

    def setup_template_variables(self, context, data_dict):
        plugins.toolkit.c.ontology = plugins.toolkit.c.pkg_dict
        plugins.toolkit.c.dataset_type = DATASET_TYPE_NAME

    def create_package_schema(self):
        """
        Returns the schema for mapping package data from a form to a format
        suitable for the database.
        """
        from ckanext.ontology.logic.schema import ontology_create_package_schema
        schema = ontology_create_package_schema()
        if self.startup:
            schema['id'] = [unicode]

        return schema

    def update_package_schema(self):
        """
        Returns the schema for mapping package data from a form to a format
        suitable for the database.
        """
        from ckanext.ontology.logic.schema import ontology_update_package_schema
        schema = ontology_update_package_schema()

        return schema

    def show_package_schema(self):
        """
        Returns the schema for mapping package data from the database into a
        format suitable for the form
        """
        from ckanext.ontology.logic.schema import ontology_show_package_schema

        return ontology_show_package_schema()

    def configure(self, config):
        self.startup = True

        # Setup harvest model
        model_setup()

        self.startup = False

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_resource('public', 'ontology')

def _create_ontology_object(context, data_dict):
    '''
        Creates an actual HarvestSource object with the data dict
        of the harvest_source dataset. All validation and authorization
        checks should be used by now, so this function is not to be used
        directly to create harvest sources. The created harvest source will
        have the same id as the dataset.
        :param data_dict: A standard package data_dict
        :returns: The created HarvestSource object
        :rtype: HarvestSource object
    '''

    source = OntologyObject()

    source.id = data_dict['id']
    #source.url = data_dict['url'].strip()

    # Avoids clashes with the dataset type
    #source.type = data_dict['source_type']

    # Convert and store ontology in JSON format, and create NodeObjects for each node in the ontology
    if 'ontology' in data_dict and data_dict['ontology'] is not None:
        g = getGraph(dataString=data_dict['ontology'])
        source.json = getJSONFromGraph(g)

        ns = getNodesFromGraph(g)
        for n in ns:
            uri = ''
            name = ''
            if n[1] is '':
                if len(n[0].split('#')) > 1:
                    split = n[0].split('#')
                    uri = split[0]
                    name = split[-1]
                elif len(n[0].split('/')) > 1:
                    split = n[0].split('/')
                    uri = split[0]
                    name = split[-1]
                else:
                    uri = split[0]
                    name = split[-1]
            else:
                uri = n[0]
                name = n[1]

            node_dict = {'id': make_uuid(), 'URI': uri, 'name': name, 'ontology_id':source.id}
            _create_node_object(context, node_dict)

    opt = ['name', 'description', 'created', 'type',
           'active', 'user_id']
    for o in opt:
        if o in data_dict and data_dict[o] is not None:
            source.__setattr__(o, data_dict[o])

    #source.active = not data_dict.get('state', None) == 'deleted'

    # Don't commit yet, let package_create do it
    source.add()
    #log.info('Ontology source created: %s', source.id)

    return source

def _create_node_object(context, data_dict):
    log.info('Creating a dataset-ontology relation: %r', data_dict)
    node = NodeObject()
    if data_dict['id'] is not None:
        node.id = data_dict['id']


    opt = ['URI', 'name', 'ontology_id']
    for o in opt:
        if o in data_dict and data_dict[o] is not None:
            node.__setattr__(o, data_dict[o])

    node.add()
    log.info('Node object created: %r', node.id)

    return node


def getGraph(url=None, directoryLocation=None, dataString=None):
    """
       Returns a JSON element. Use either url, directoryLocation, or DataString. DataString is a pure rdfxml string.
    """

    parsingString = ""

    if url is not None:
        f = urllib2.urlopen(url)
        parsingString = f.read()
    elif directoryLocation is not None:
        reader = open(directoryLocation, "r")
        parsingString = reader.read()
    elif dataString is not None:
        parsingString = dataString

    return Graph().parse(data=parsingString, format="application/rdf+xml")

def getJSONFromGraph(graph):
    return graph.serialize(format='json-ld', indent=4)

def getNodesFromGraph(graph):
    n = []
    for s, p, o in graph:
        if '#Class' in o:
            n.append((s, graph.label(s)))
    return n

def ontology_list(context, data_dict):
    model = context["model"]
    api = context.get("api_version", 1)
