# -*- coding: utf-8 -*-
# Started by François-Xavier Bourlet <fx@dotcloud.com>, Oct 2011.

import copy
import re
import yaml

from StringIO import StringIO
from yaml.nodes import ScalarNode, SequenceNode, MappingNode
from yaml.constructor import SafeConstructor


class SchemaError(Exception):
    pass


class _node_validator(object):

    def __init__(self, _type, subnode=None, optional=False, default=None,
            allowed=None, checks=None):
        self._type = _type
        self._optional = optional
        self._subnode = subnode
        self._default = default
        self._allowed = allowed
        self._checks = checks if checks is not None else []

    @property
    def optional(self):
        return self._optional

    @property
    def subnode(self):
        return self._subnode

    @property
    def default(self):
        return self._default

    @property
    def allowed(self):
        return self._allowed

    @allowed.setter
    def allowed(self, value):
        self._allowed = value

    @property
    def checks(self):
        return self._checks

    def python_type(self, ast_node):
        if type(ast_node) is ScalarNode:
            return type(SafeConstructor().construct_object(ast_node))
        if type(ast_node) is SequenceNode:
            return list
        if type(ast_node) is MappingNode:
            return dict
        raise RuntimeError('Unable to map ast_node type ({0})'.format(type(ast_node)))

    def pretty_type(self, _type):
        if _type is unicode or _type is str:
            return 'string'
        if _type is dict:
            return 'dictionary'
        return _type.__name__

    def raise_error(self, err_msg, ast_node):
        mark = ast_node.start_mark
        msg = "%s in \"%s\", line %d, column %d"   \
            % (err_msg, mark.name, mark.line+1, mark.column+1)
        snippet = mark.get_snippet()
        if snippet is not None:
            msg += ":\n"+snippet
        raise SchemaError(msg)

    def validate(self, ast_node, parent_key=None):
        ast_node_type = self.python_type(ast_node)
        if self._type is str:
            wrong_type = type(ast_node) is not ScalarNode
            ast_node.tag = 'tag:yaml.org,2002:str'  # enforce string type.
        else:
            wrong_type = ast_node_type is not self._type
        if wrong_type:
            if (self.python_type(ast_node) is type(None)):
                msg = 'Expected a type {0} but got nothing'.format(
                        self.pretty_type(self._type))
            else:
                msg = 'Expected a type {0} but got {1} type {2}'.format(
                        self.pretty_type(self._type),
                        'a' if bool(ast_node.value) else 'an empty',
                        self.pretty_type(self.python_type(ast_node)))
            self.raise_error(msg, ast_node)

        if len(self._checks) > 0:
            if ast_node_type is dict:
                value = parent_key
            else:
                value = SafeConstructor().construct_object(ast_node)
            for desc, check in self._checks:
                if not check(value):
                    self.raise_error('Invalid {0} "{1}"'.format(desc,
                        value), ast_node)

        if self._allowed is not None:
            value = SafeConstructor().construct_object(ast_node)
            (desc, allowed_set) = self._allowed
            if value not in allowed_set:
                self.raise_error('Unrecognized {0} "{1}"'.format(desc,
                    value), ast_node)

        if self._subnode is None:
            return

        if self.python_type(ast_node) is dict:
            required_nodes = set(k for k, v in self._subnode.items() if not
                    v.optional)
            for subnode_key, ast_subnode in ast_node.value:
                subnode_key = subnode_key.value
                if '*' in self._subnode:
                    self._subnode['*'].validate(ast_subnode,
                            parent_key=subnode_key)
                    if '*' in required_nodes:
                        required_nodes.remove('*')
                elif subnode_key in self._subnode:  # ignore everything else
                    self._subnode[subnode_key].validate(ast_subnode,
                            parent_key=subnode_key)
                    if subnode_key in required_nodes:
                        required_nodes.remove(subnode_key)
            if len(required_nodes):
                if '*' in required_nodes:
                    msg = '{0} cannot be empty'.format(parent_key)
                else:
                    msg = 'Missing mandatory {0}: "{1}"'.format(
                            'entry' if len(required_nodes) == 1 else 'entries',
                            ', '.join(required_nodes)
                            )
                self.raise_error(msg, ast_node)


def _require(_type, subnode=None, allowed=None, checks=None):
    return _node_validator(_type, subnode, optional=False,
            allowed=allowed, checks=checks)


def _optional(_type, subnode=None, default=None, allowed=None, checks=None):
    return _node_validator(_type, subnode, optional=True, default=default,
            allowed=allowed, checks=checks)


_schema = _require(
    dict,
    {
        '*': _require(
            dict,
            {
                'type': _require(str),
                'approot': _optional(str, default='.'),
                'requirements': _optional(list, default=[]),
                'systempackages': _optional(list, default=[]),
                'environment': _optional(dict, default={}),
                'postinstall': _optional(str, default=''),
                'config': _optional(dict, default={}),
                'instances': _optional(int, default=1),
                'process': _optional(str, default=''),
                'processes': _optional(dict, default={}),
                'ports': _optional(dict, {
                    '*': _optional(str, allowed=('port', set(('http', 'tcp', 'udp'))))
                }),
                'buildscript': _optional(str),
                'prebuild': _optional(str),
                'postbuild': _optional(str),
                'ruby_version': _optional(str),
            },
            checks=[
                ('service name (must be <= 16 characters)', lambda n: len(n) <= 16),
                ('characters (lowercase alphanum only) for service', lambda n: re.match('^[a-z0-9_]+$', n)),
            ]
        )
    }
)


def validate_ast_schema(ast, valid_services):
    if ast is None:
        raise ValueError('Empty ast!')
    schema = copy.deepcopy(_schema)
    schema.subnode['*'].subnode['type'].allowed = ('service', set(valid_services))
    schema.validate(ast, 'service(s) dict')


def load_build_file(build_file_content, valid_services=["python", "python-worker", "custom"]):
    """ Load and parse the build description contained in the build file """
    stream = StringIO(build_file_content)
    stream.name = 'dotcloud.yml'  # yaml load will use this property
    # to generate proper error marks.

    yaml_loader = yaml.SafeLoader(stream)

    # Check yaml syntax and load ast
    ast = yaml_loader.get_single_node()

    if ast is None:
        raise ValueError('"dotcloud.yml" is empty!')

    # Validate ast against dotcloud.yml schema.
    validate_ast_schema(ast, valid_services)

    # Now construct python object...
    desc = yaml_loader.construct_document(ast)

    # Force service name to be of type str
    desc = dict((str(k), v) for k, v in desc.iteritems())

    # for each services description
    for service_name, service_desc in desc.iteritems():
        # Check for conflicting options
        if service_desc.get('process') and service_desc.get('processes'):
            raise ValueError(
                'You can\'t have both "process" and "processes" at '
                'the same time in service "{0}"'.format(service_name)
            )

        # Inject defaults values if necessary
        for def_name, def_node in _schema.subnode['*'].subnode.items():
            if def_node.default is None:
                continue
            if def_name not in service_desc:
                service_desc[def_name] = def_node.default

    return desc
