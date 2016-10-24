from ckan.plugins import toolkit as pt
from ckanext.ontology import model as ontology_model

def user_is_sysadmin(context):
    """
        Checks if the user defined in the context is a sysadmin
        rtype: boolean
    """
    model = context['model']
    user = context['user']
    user_obj = model.User.get(user)
    if not user_obj:
        raise pt.Objectpt.ObjectNotFound('User {0} not found').format(user)

    return user_obj.sysadmin

def _get_object(context, data_dict, name, class_name):
    """
        return the named item if in the data_dict, or get it from
        model.class_name
    """
    if not name in context:
        id = data_dict.get('id', None)
        obj = getattr(ontology_model, class_name).get(id)
        if not obj:
            raise pt.ObjectNotFound
    else:
        obj = context[name]
    return obj

def get_ontology_object(context, data_dict = {}):
    return _get_object(context, data_dict, 'ontology', 'Ontology')

def ontology_create(context, data_dict):
    """
        Authorization check for ontology creation
        It forwards the checks to package_create, which will check for
        organization membership, whether if sysadmin, etc according to the
        instance configuration.
    """
    user = context.get('user')
    try:
        pt.check_access('package_create', context, data_dict)
        return {'success': True}
    except pt.NotAuthorized:
        return {'success': False,
                'msg': pt._('User {0} not authorized to create a ontology').format(user)}