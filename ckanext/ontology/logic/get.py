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

# Return the list of nodes that a dataset annotated to (has relations to)
# The dataset_id is specified in data_dict
@toolkit.side_effect_free
def dataset_node_relations(context, data_dict=None):
    if 'id' not in data_dict:
        return None

    dataset_relations = DatasetOntologyRelation.get_all()
    dict_list = []
    for rel in dataset_relations:
        if rel.dataset_id == data_dict['id']:
            relation = rel.as_dict()
            log.debug("The relation is %s", relation)
            node = NodeObject.get(key=rel.node_id, attr='id').as_dict()
            log.debug("The node object is %s", node)
            dict_list.append( {'id': rel.id, 'dataset_id': rel.dataset_id, 'ontology_id': rel.ontology_id,
                               'node': node} )
    return dict_list

# Return the list of datasets that are annotated with a node object
# The node_id is specified in data_dict
@toolkit.side_effect_free
def get_datasets_annotatedto_node(context, data_dict=None):
    if 'id' not in data_dict:
        return None

    node_relations = DatasetOntologyRelation.get_all()
    dict_list = []
    for rel in node_relations:
        if rel.node_id == data_dict['id']:
            relation = rel.as_dict()
            dataset = relation.get(key=rel.dataset_id, attr='id').as_dict()
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
                #log.debug('found in node: %s', NodeObject.get(d.node_id).name)

        # find children (subClassOf) of 'node'. Add to 'nodes[]'.
        # for s, p, o...: s subclass of o
        subnode_uris = []
        for s, p, o in ontology:
            #log.debug('check in subtree %s, %s, %s', s, unicode_value(p), o)
            node_uri_name = node.URI+"#"+node.name
            #log.debug('uri name of node: %r, o: %r', node_uri_name, unicode_value(o))
            #if unicode_value('#subClassOf') in unicode_value(p) and unicode_value(node.URI) == unicode_value(o):
            if unicode_value('#subClassOf') in unicode_value(p) and unicode_value(node_uri_name) in unicode_value(o):
                subnode_uris.append(unicode_value(s))

        #log.debug('subnode_uris before is: %s', subnode_uris)
        for n in NodeObject.get_all():
            string = unicode_value(n.URI+"#"+n.name)
            #log.debug('n.URI: %r', string)
            #if string in subnode_uris:
            for s_uri in subnode_uris:
                if string in unicode_value(s_uri):
                    nodes.append(n)
                    # there is only one node object for each node in the ontology??
                    break

    return datasets

# Return all datasets in a node and all its sub-nodes
@toolkit.side_effect_free
def search_from_node(context, data_dict):
    if 'id' not in data_dict:
        return None

    return _search_from_node(data_dict['id'])

@toolkit.side_effect_free
def semantic_search(context, data_dict=None):

    """
        Semantic search for a list of terms
        The terms are either separated by "*" or by " "
        "*" for AND relation
        " " for OR relation
    """

    datasets = []

    if 'term' not in data_dict:
        return None

    s_term = data_dict['term']

    # handle the terms with OR relation (separated by space)
    log.debug('The search term is %s', s_term)
    if ' ' in s_term:
        log.debug('This is OR relation: %s', s_term)
        datasets = _search_for_OR_relation(s_term)
    else:
        if '*' in s_term:
            log.debug('This is AND relation: %s', s_term)
            datasets = _search_for_AND_relation(s_term)
        else:
            log.debug('This is a single term: %s', s_term)
            datasets = _search_for_OR_relation(s_term)




    # write the results (datasets) to the SemanticSearchResults Table
    _create_semantic_search_result_object(datasets, s_term)

    return datasets

    # Find datasets belonging the each node and their subtrees. Avoid duplicates!!!

    #return datasets

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
    return result

def _search_for_OR_relation(s_term):
    # semantic search for terms with OR relations
    terms = s_term.split(' ')
    log.debug('The terms are: %s', ','.join(terms))

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
        log.debug('result datasets: %r', found)
        for f in found:
            if not datasets:  # empty datasets means f is the first dataset
                datasets.append(f)
            else:
                # avoid duplicated datasets
                new_dataset = True
                for d in datasets:
                    if f['id']==d['id']:
                        new_dataset = False
                        # add the new matching node (term)
                        d['found_in_node']['name'] = d['found_in_node'].get('name')+':'+f['found_in_node'].get('name')
                        break
                if new_dataset:
                    datasets.append(f)

    return datasets


def _search_for_AND_relation(s_term):
    #semantic search for teresm with AND relations
    terms = s_term.split('*')
    log.debug('The terms are: %s', ','.join(terms))

    # 'new_results' holds all the datasets to be returned
    new_results = []
    # 'results' holds the temporary results for the terms inspected
    results = []
    for term in terms:
        # 'datasets' holds the datasets for this term
        datasets = []
        #'origin' holds all the nodes matching the search term
        origin = []
        # Find nodes with names containing the search term
        found = _find_nodes_from_term(term)
        for f in found:
            if f.id not in origin:
                origin.append(f.id)

        for node in origin:
            found = _search_from_node(node)
            for f in found:
                new_dataset = True
                for d in datasets:
                    if f['id'] == d['id']:
                        new_dataset = False
                        break

                if new_dataset:
                    datasets.append(f)

        if not datasets: # test if datasets is empty
            # No datasets for one term, the results will be empty
            return []
        # keep only the datasets that appear in both terms
        if not new_results: # This is the first AND term
            results = list(datasets)
            new_results = list (datasets)
        else:
            # keep datasets that appear in both sets (only identified by 'id' as 'found_in_node' may be different even for the same dataset )
            new_results = []
            for rd in results:
                for d in datasets:
                    if d['id'] == rd['id']:
                        rd['found_in_node']['name'] = rd['found_in_node'].get('name')+'*'+d['found_in_node'].get('name')
                        new_results.append(rd)
                        break
            results = list(new_results)

    return new_results
