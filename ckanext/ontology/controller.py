import logging
from ckan.lib.base import BaseController
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
            # TODO ADD ONTOLOGIES TO SELECT
            # Add ontologies like this to use them
            # c.ontologies = [{'ontology': 'test', 'nodes': []},{'ontology': 'test', 'nodes': []}]
            c.link = str("/dataset/ontology/add/" + id)
            c.ontologies = []
            c.nodes = NodeObject.get_all()
            for ontology in OntologyObject.get_all():
                ontology.nodes = []
                for node in c.nodes:
                    if ontology.as_dict()['id'] == node.as_dict()['ontology_id']:
                        ontology.nodes.append(node)
                c.ontologies.append(ontology)

            print c.ontologies
            c.pkg_dict = get_action('package_show')(context, {'id': id})
            c.pkg = context['package']
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

        data_dict = {'id': id}

        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            # TODO ADD ONTOLOGIES FOR A DATASET
            # Add ontologies like this to display them !!!
            #c.ontologies = [{'ontology': 'test', 'node': 'example'},{'ontology': 'test', 'node': 'example'},{'ontology': 'test', 'node': 'example'}]
            dataset_type = c.pkg_dict['type'] or 'dataset'
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read dataset %s') % id)

        return render('package/ontology_display.html', {'dataset_type': dataset_type})

    def create_ontology(self, id, data=None):
        print "CREATE"
        print data
        print id
        return self.show_ontology(id)