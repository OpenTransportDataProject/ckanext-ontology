from logging import getLogger
import ckan.plugins as plugins
from ckan.lib.plugins import DefaultDatasetForm
import ckan.plugins.toolkit as toolkit
from ckanext.ontology.model import setup as model_setup
from ckanext.ontology.model import OntologyObject, NodeObject, DatasetOntologyRelation
from ckan.model.types import make_uuid

from rdflib import Graph
import logging
import urllib2

logging.basicConfig()

log = getLogger(__name__)
DATASET_TYPE_NAME = "ontology"


class OntologyPlugin(plugins.SingletonPlugin, DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    startup = False

    ## IPackageController
    def after_create(self, context, data_dict):
        if 'type' in data_dict and data_dict['type'] == DATASET_TYPE_NAME and not self.startup:
            # Create an actual Ontology object
            _create_ontology_object(context, data_dict)
            #add_ontology_to_tag_vocabulary(data_dict['name'])

        if 'type' in data_dict and data_dict['type'] == 'dataset' and not self.startup:
            extras = data_dict['extras']
            ontology_defined = False
            node_defined = False
            for e in extras:
                if e['key'] == 'ontologies':
                    ontology_defined = True
                elif e['key'] == 'nodes':
                    node_defined = True
            if ontology_defined and node_defined:
                _create_dataset_ontology_relation(context, data_dict)

    def before_index(self, pck_dict):
        del pck_dict['ontology']
        return pck_dict

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
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ontology')

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
        source.ontology = data_dict['ontology']
        g = getGraph(dataString=data_dict['ontology'])

        # Convert to graph to JSON and store in 'json_ontology' field
        source.json_ontology = getJSONFromGraph(g)

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

def _create_dataset_ontology_relation(context, data_dict):
    log.info('Creating a dataset-ontology relation: %r', data_dict)
    relation = DatasetOntologyRelation()
    relation.__setattr__('dataset_id', data_dict['id'])

    # Add ontology and node IDs to relation
    extras = data_dict['extras']

    for e in extras:
        # TODO Find a better  way to extract ontology_id and node_id
        if e['key'] == 'ontologies':
            relation.__setattr__('ontology_id', e['value'])
        elif e['key'] == 'nodes':
            relation.__setattr__('node_id', e['value'])

    relation.add()
    log.info('Created dataset-ontology relation: %r', data_dict)

    return relation

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

def ontologies():
    try:
        #package_list = toolkit.get_action('package_list')
        #ontologies = package_list(data_dict={'type': 'ontology'})

        return OntologyObject.get_all()
    except toolkit.ObjectNotFound:
        return None

def nodes():
    try:
        return NodeObject.get_all()
    except toolkit.ObjectNotFound:
        return None


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

class DatasetFormPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    def _modify_package_schema(self, schema):
        schema.update({
            'custom_text': [toolkit.get_validator('ignore_missing'),
                            toolkit.get_converter('convert_to_extras')]
        })
        schema.update({
            'ontologies': [
                toolkit.get_validator('ignore_missing'),
                toolkit.get_converter('convert_to_extras')
            ],
            'nodes': [
                toolkit.get_validator('ignore_missing'),
                toolkit.get_converter('convert_to_extras')
            ]
        })
        return schema

    def create_package_schema(self):
        schema = super(DatasetFormPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(DatasetFormPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(DatasetFormPlugin, self).show_package_schema()
        schema.update({
            'ontologies': [
                toolkit.get_converter('convert_from_extras'),
                toolkit.get_validator('ignore_missing')],
            'nodes': [
                toolkit.get_converter('convert_from_extras'),
                toolkit.get_validator('ignore_missing')]
        })

        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')

    def get_helpers(self):
        return {'ontologies': ontologies, 'nodes': nodes}

