import logging
import datetime

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import types
from sqlalchemy import Index
from sqlalchemy.engine.reflection import Inspector


from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

log = logging.getLogger(__name__)

__all__ = [
    'OntologyObject', 'ontology_table',
    'NodeObject', 'node_table',
    'DatasetOntologyRelation', 'dataset_ontology_relation_table'
]
#Ontology = 'ontology_table'
ontology_table = None
node_table = None
dataset_ontology_relation_table = None


def setup():
    if ontology_table is None:
        define_ontology_tables()
        log.debug('Ontology tables defined in memory')

    if not model.package_table.exists():
        log.debug('Ontology table creation deferred')
        return

    if not ontology_table.exists():

        # Create each table individually rather than
        # using metadata.create_all()
        ontology_table.create()
        node_table.create()
        dataset_ontology_relation_table.create()
        log.debug('Ontology tables created')
    else:
        log.debug('Ontology tables already exist')


class OntologyError(Exception):
    pass


class OntologyDomainObject(DomainObject):
    """
        Convenience methods for searching objects
    """
    key_attr = 'id'

    @classmethod
    def get(cls, key, default=None, attr=None):
        """
            Finds a single entity in the register.
        """

        if attr == None:
            attr = cls.key_attr
        kwds = {attr: key}
        o = cls.filter(**kwds).first()
        if o:
            return o
        else:
            return default

    @classmethod
    def filter(cls, **kwds):
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kwds)

    @classmethod
    def get_all(cls, key=None, attr=None):
        query = Session.query(cls).autoflush(False)
        return query.all()


class OntologyObject(OntologyDomainObject):
    """
        A Harvest Object is created every time an element is fetched from a
        harvest source. Its contents can be processed and imported to ckan
        packages, RDF graphs, etc.
    """

    def as_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description,
                'ontology':self.ontology, 'json_ontology':self.json_ontology, 'active': self.active}

    def as_simple_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description, 'active': self.active}

    def __repr__(self):
        return '<OntologyObject id=%s name=%s description=%s json_ontology=%s active=%r>' % \
               (self.id, self.name, self.description, self.json_ontology, self.active)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')

class NodeObject(OntologyDomainObject):
    def __repr__(self):
        return '<DatasetOntologyRelation id=%s URI=%s ontology_id=%s name=%r>' % \
               (self.id, self.URI, self.ontology_id, self.name)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')


class DatasetOntologyRelation(OntologyDomainObject):
    '''Keep the relations between a dataset and an ontology.'''

    def __repr__(self):
        return '<DatasetOntologyRelation id=%s dataset_id=%s ontology_id=%s node_id=%r>' % \
               (self.id, self.dataset_id, self.ontology_id, self.node_id)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')

def define_ontology_tables():
    global ontology_table
    global node_table
    global dataset_ontology_relation_table

    ontology_table = Table('ontology', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.UnicodeText, default=u''),
        Column('description', types.UnicodeText, default=u''),
        Column('ontology', types.UnicodeText, default=u''),
        Column('json_ontology', types.UnicodeText, default=u''),
        Column('created', types.DateTime, default=datetime.datetime.utcnow),
        Column('type', types.UnicodeText, nullable=False),
        Column('active', types.Boolean, default=True),
        Column('user_id', types.UnicodeText, default=u'')
    )

    dataset_ontology_relation_table = Table('dataset_ontology_relation', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('dataset_id', types.UnicodeText, primary_key=True, default=u''),
        Column('ontology_id', types.UnicodeText, primary_key=True, default=u''),
        Column('node_id', types.UnicodeText, primary_key=True, default=u'')
    )

    node_table = Table('node', metadata,
       Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
       Column('URI', types.UnicodeText, primary_key=True, default=u''),
       Column('name', types.UnicodeText, primary_key=True, default=u''),
       Column('ontology_id', types.UnicodeText, primary_key=True, default=u'')
    )

    mapper(
        OntologyObject,
        ontology_table
    )

    mapper(
        NodeObject,
        node_table
    )

    mapper(
        DatasetOntologyRelation,
        dataset_ontology_relation_table,
    )
