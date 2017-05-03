import logging
from ckan.lib.base import BaseController
import json
import ckan.lib.helpers as h
from ckan.common import _, request, c, g
import cgi
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
from ckanext.ontology.model import OntologyObject, NodeObject, DatasetOntologyRelation
import ckan.lib.plugins
import ckan.plugins as p
import ckan.plugins.toolkit as t
import ckan.lib.render

#render = ckan.lib.base.render
#from home import CACHE_PARAMETERS

log = logging.getLogger(__name__)

render = base.render
abort = base.abort
redirect = base.redirect


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin


class OntologyController(BaseController):

    def edit_ontology(self, id):
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user or c.author,
            'for_view': True,
            'auth_user_obj': c.userobj,
            'use_cache': False
        }
        try:
            c.link = str("/dataset/ontology/add/" + id)
            c.ontologies = []
            relations = []
            c.nodes = NodeObject.get_all()
            for ontology in OntologyObject.get_all():
                ontology = ontology.as_simple_dict()
                ontology['nodes'] = []
                for node in c.nodes:
                    if ontology['id'] == node.as_dict()['ontology_id']:
                        ontology['nodes'].append(node.as_dict())
                c.ontologies.append(ontology)
            c.ontologiesJson = json.dumps(c.ontologies)
            c.pkg_dict = get_action('package_show')(context, {'id': id})
            c.pkg = context['package']

            relation_list = DatasetOntologyRelation.get_all()
            for relation in relation_list:
                if relation.dataset_id == c.pkg_dict['id']:
                    relations.append(json.dumps(relation.as_dict()))

            c.relations = relations
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read dataset %s') % id)

        return render("package/edit_ontology.html", extra_vars={'package_id': id})

    def show_ontology(self, id):
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user or c.author,
            'for_view': True,
            'auth_user_obj': c.userobj,
            'use_cache': False
        }

        try:
            c.pkg_dict = get_action('package_show')(context, {'id': id})
            ontologies = []
            relation_list = DatasetOntologyRelation.get_all()
            for relation in relation_list:
                if relation.dataset_id == c.pkg_dict['id']:
                    ontology = OntologyObject.get(relation.ontology_id)
                    node = NodeObject.get(relation.node_id)
                    ontologies.append({'ontology': ontology.as_simple_dict(), 'node': node.as_dict()})

            c.ontologies = ontologies
            dataset_type = c.pkg_dict['type'] or 'dataset'
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read dataset %s') % id)

        return render('package/ontology_display.html', {'dataset_type': dataset_type})

    def create_ontology(self, id):


        context = {
            'model': model,
            'session': model.Session,
            'user': c.user or c.author,
            'for_view': True,
            'auth_user_obj': c.userobj,
            'use_cache': False
        }
        dataset = get_action('package_show')(context, {'id': id})

        #log.info('to delete all items with dataset_id %s', dataset['id'])
        DatasetOntologyRelation.delete_all(key=dataset['id'], attr='dataset_id')

        relations = []
        ontology = None
        node = None
        for key, value in t.request.params.iteritems():
            if ontology and not node:
                node = value
            if not ontology and not node:
                ontology = value
            if ontology and node:
                relations.append({'ontology': ontology, 'node': node})
                ontology = None
                node = None

        for relationData in relations:
            relation = DatasetOntologyRelation()
            relation.__setattr__('dataset_id', dataset['id'])
            relation.__setattr__('ontology_id', relationData['ontology'])
            relation.__setattr__('node_id', relationData['node'])
            relation.save()

        return t.redirect_to(controller='package', action='read', id=id)
