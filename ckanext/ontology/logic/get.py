import logging
import json
import datetime
from ckan.plugins import toolkit
from ckanext.ontology.model import OntologyObject, NodeObject, DatasetOntologyRelation, SemanticSearchResults
from ckan.model import Package
from ckan.model.types import make_uuid

log = logging.getLogger(__name__)

# Return a list of all stored ontology objects
@toolkit.side_effect_free
def get_ontology_objects(context, data_dict=None):
    try:
        os = OntologyObject.get_all()
        os_list = []

        # If no search terms are specified, return all ontologies
        if data_dict == None:
            for o in os:
                o.jsonData = json.load(o.json)
                os_list.append(o.as_dict())
            return json.loads(os_list)

        # If one or more search terms are specified, make sure they are valid
        for key in data_dict.keys():
            if key not in ['id', 'name', 'description', 'active']:
                print(key + ' not a searchable key')
                return

        # Find all ontologies matching the search terms
        for o in os:
            found = True
            o_dict = o.as_dict()
            for key in data_dict.keys():
                if data_dict[key] != o_dict[key]:
                    found = False
            if found:
                json_data = json.loads(o_dict['json'].decode('unicode-escape').strip('"'))
                o_dict['json'] = json_data
                os_list.append(o_dict)

        return os_list
    except toolkit.ObjectNotFound:
        return None

# Get and ontology with nodes belonging to this ontology
@toolkit.side_effect_free
def get_ontology(context, data_dict=None):
    if 'id' not in data_dict:
        return None

    ontology = OntologyObject.get(key=data_dict['id'])
    if ontology is None:
        return None
    nodes = NodeObject.get_all(key=data_dict['id'], attr='ontology_id')
    nodes_as_dicts = []
    for node in nodes:
        nodes_as_dicts.append(node.as_dict())
    return {'ontology': ontology.as_simple_dict(), 'json': json.loads(ontology.json.decode('string-escape').strip('"')), 'nodes': nodes_as_dicts}

@toolkit.side_effect_free
def list_ontologies_json(context, data_dict=None):
    json_list = []
    ontologies = OntologyObject.get_all()

    for o in ontologies:
        json_list.append(json.load(o.json_ontology))

    return json_list

@toolkit.side_effect_free
def get_ontology_json(context, data_dict=None):
    if 'id' not in data_dict:
        return None

    ontology = OntologyObject.get(key=data_dict['id'])
    return json.loads(ontology.json_ontology)

@toolkit.side_effect_free
def dataset_node_relations(context, data_dict=None):
    if 'id' not in data_dict:
        return None

    dataset_relations = DatasetOntologyRelation.get_all()
    dict_list = []
    for rel in dataset_relations:
        if rel.dataset_id == data_dict['id']:
            relation = rel.as_dict()
            node = NodeObject.get(key=rel.node_id, attr='id').as_dict()
            dict_list.append( {'id': rel.id, 'dataset_id': rel.dataset_id, 'ontology_id': rel.ontology_id,
                               'node': node} )
    return dict_list

# Return a list of all NodeObjects, with possibility to filter by ontology id (with ?id=...)
@toolkit.side_effect_free
def get_node_objects(context, data_dict=None):
    node_list = []
    ns = NodeObject.get_all()
    if 'id' not in data_dict:
        for n in ns:
            node_list.append(n.as_dict())
    else:
        for n in ns:
            if n.ontology_id == data_dict['id']:
                node_list.append(n.as_dict())

    return node_list

# Return a specific node corresponding to the given id (with ?id=...)
@toolkit.side_effect_free
def get_node(context, data_dict):
    if 'id' not in data_dict:
        return ''

    node = NodeObject.get(key=data_dict['id'])
    if node is None:
        return None
    return node.as_dict()

def _search_from_node(id):
    # The datasets to be returned
    datasets = []
    # The nodes to be processed (find datasets and sub-nodes)
    nodes = []

    node = NodeObject.get(key=id)
    if node is None:
        return None
    nodes.append(node)

    ontology = _get_ontology_graph(node.ontology_id)

    # Main processing loop
    while nodes:
        node = nodes[0]
        del nodes[0]

        # find datasets in 'node'. Add to 'datasets[]'.
        ds = DatasetOntologyRelation.get_all()  # (key=data_dict['id'], attr='node_id')
        for d in ds:
            if (d.node_id == node.id):
                package_dict = _package_as_dict(Package.get(d.dataset_id))
                package_dict['found_in_ontology_id'] = d.ontology_id
                package_dict['found_in_node'] = NodeObject.get(d.node_id).as_dict()
                datasets.append(package_dict)
        # find children of 'node'. Add to 'nodes[]'.
        # for s, p, o...: s subclass of o
        subnode_uris = []
        for s, p, o in ontology:
            if unicode_value('#subClassOf') in unicode_value(p) and unicode_value(node.URI) == unicode_value(o):
                subnode_uris.append(unicode_value(s))

        for n in NodeObject.get_all():
            string = unicode_value(n.URI)
            if string in subnode_uris:
                nodes.append(n)

    return datasets

# Return all datasets in a node and all its sub-nodes
@toolkit.side_effect_free
def search_from_node(context, data_dict):
    if 'id' not in data_dict:
        return None

    return _search_from_node(data_dict['id'])

@toolkit.side_effect_free
def semantic_search(context, data_dict=None):
    datasets = []

    if 'term' not in data_dict:
        return None

    terms = data_dict['term'].split(' ')

    # 'datasets' holds all the datasets to be returned
    datasets = []
    #'origin' holds all the nodes matching the search term
    origin = []
    # Find nodes with names containing the search term
    for term in terms:
        found = _find_nodes_from_term(term)
        for f in found:
            if f.id not in origin:
                origin.append(f.id)

    for node in origin:
        found = _search_from_node(node)
        for f in found:
            if f not in datasets:
                datasets.append(f)

    # write the results (datasets) to the SemanticSearchResults Table
    _create_semantic_search_result_object(datasets, data_dict['term'])

    return datasets

    # Find datasets belonging the each node and their subtrees. Avoid duplicates!!!

    return datasets

def _get_ontology_graph(id):
    import ckanext.ontology.plugin as p
    ontology = OntologyObject.get(key=id)
    return p.getGraph(dataString=ontology.ontology)

def _package_as_dict(pkg):
    from datetime import datetime
    return {'id': pkg.id, 'name': pkg.name, 'title': pkg.title, 'version': pkg.version, 'url': pkg.url,
            'notes': pkg.notes, 'license_id': pkg.license_id, 'revision_id': pkg.revision_id,
            'author': pkg.author, 'author_email': pkg.author_email, 'maintainer': pkg.maintainer,
            'maintainer_email': pkg.maintainer_email, 'state': pkg.state, 'type': pkg.type,
            'owner_org': pkg.owner_org, 'private': pkg.private,
            'metadata_modified': _datetime_converter(pkg.metadata_modified),
            'creator_user_id': pkg.creator_user_id,
            'metadata_created': _datetime_converter(pkg.metadata_created)}

# Convert datetime format to a JSON-serializable format
def _datetime_converter(dt):
    from datetime import datetime
    if isinstance(dt, datetime):
        return dt.isoformat()
    return TypeError("_datetime_converter(dt) only accepts datetime type.")

# Return a list of ids of all nodes with names containing 'term'
def _find_nodes_from_term(term):
    nodes = []
    for node in NodeObject.get_all():
        # 'in' for partial match, '==' for exact match:
        if term.lower() in node.name.lower():
            nodes.append(node)

    return nodes


def unicode_value(value):
    try:
        return unicode(value, 'utf-8')
    except TypeError:
        return value

def _create_semantic_search_result_object(datasets, terms):
    # convert result datasets to results_str
    results = []
    for dataset in datasets:
        r_id = dataset.get("id")
        #ont_id = dataset.get("found_in_ontology_id")
        node_name = dataset.get("found_in_node").get("name")
        results.append(r_id + ":" + node_name)

    results_str = ";".join(results)

    # add the semantic search result to database table
    result = SemanticSearchResults()
    result.id = make_uuid()
    result.timestamp = datetime.datetime.utcnow()
    result.terms = terms
    result.results = results_str
    log.debug('The semanticSearchResultObject is: %s', result.__str__())
    result.save()
    log.debug('SemanticSearchResult object is added to the table' )
    return result
