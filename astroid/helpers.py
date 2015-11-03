# copyright 2003-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.

"""
Various helper utilities.
"""

import six

from astroid import bases
from astroid import context as contextmod
from astroid import exceptions
from astroid import manager
from astroid import nodes
from astroid import raw_building
from astroid import scoped_nodes
from astroid import util


def _object_type(node, context=None):
    context = context or contextmod.InferenceContext()

    for inferred in node.infer(context=context):
        if isinstance(inferred, scoped_nodes.ClassDef):
            if inferred.newstyle:
                metaclass = inferred.metaclass()
                if metaclass:
                    yield metaclass
                    continue
            yield raw_building.astroid_builtins.getattr('type')[0]
        elif isinstance(inferred, (scoped_nodes.Lambda, bases.UnboundMethod)):
            if isinstance(inferred, scoped_nodes.Lambda):
                if inferred.root() is raw_building.astroid_builtins:
                    yield raw_building.astroid_builtins['BuiltinFunctionType']
                else:
                    yield raw_building.astroid_builtins['FunctionType']
            elif isinstance(inferred, bases.BoundMethod):
                yield raw_building.astroid_builtins['MethodType']
            elif isinstance(inferred, bases.UnboundMethod):
                if six.PY2:
                    yield raw_building.astroid_builtins['MethodType']
                else:
                    yield raw_building.astroid_builtins['FunctionType']
            else:
                raise InferenceError('Function {func!r} inferred from {node!r} '
                                     'has no identifiable type.',
                                     node=node, func=inferred, contex=context)
        elif isinstance(inferred, scoped_nodes.Module):
            yield raw_building.astroid_builtins['ModuleType']
        else:
            yield inferred._proxied


def object_type(node, context=None):
    """Obtain the type of the given node

    The node will be inferred first, so this function can support all
    sorts of objects, as long as they support inference. It will try to
    retrieve the Python type, as returned by the builtin `type`.
    """

    try:
        types = set(_object_type(node, context))
    except exceptions.InferenceError:
        return util.YES
    if len(types) > 1 or not types:
        return util.YES
    return list(types)[0]


def safe_infer(node, context=None):
    """Return the inferred value for the given node.

    Return None if inference failed or if there is some ambiguity (more than
    one node has been inferred).
    """
    try:
        inferit = node.infer(context=context)
        value = next(inferit)
    except exceptions.InferenceError:
        return
    try:
        next(inferit)
        return # None if there is ambiguity on the inferred node
    except exceptions.InferenceError:
        return # there is some kind of ambiguity
    except StopIteration:
        return value


def has_known_bases(klass, context=None):
    """Return true if all base classes of a class could be inferred."""
    try:
        return klass._all_bases_known
    except AttributeError:
        pass
    for base in klass.bases:
        result = safe_infer(base, context=context)
        # TODO: check for A->B->A->B pattern in class structure too?
        if (not isinstance(result, scoped_nodes.ClassDef) or
                result is klass or
                not has_known_bases(result, context=context)):
            klass._all_bases_known = False
            return False
    klass._all_bases_known = True
    return True


def _type_check(type1, type2):
    if not all(map(has_known_bases, (type1, type2))):
        return util.YES

    if not all([type1.newstyle, type2.newstyle]):
        return False
    try:
        return type1 in type2.mro()[:-1]
    except exceptions.MroError:
        # The MRO is invalid.
        return util.YES


def is_subtype(type1, type2):
    """Check if *type1* is a subtype of *typ2*."""
    return _type_check(type2, type1)


def is_supertype(type1, type2):
    """Check if *type2* is a supertype of *type1*."""
    return _type_check(type1, type2)


def class_instance_as_index(node):
    """Get the value as an index for the given instance.

    If an instance provides an __index__ method, then it can
    be used in some scenarios where an integer is expected,
    for instance when multiplying or subscripting a list.
    """
    context = contextmod.InferenceContext()
    context.callcontext = contextmod.CallContext(args=[node])

    try:
        for inferred in node.igetattr('__index__', context=context):
            if not isinstance(inferred, bases.BoundMethod):
                continue

            for result in inferred.infer_call_result(node, context=context):
                if (isinstance(result, nodes.Const)
                        and isinstance(result.value, int)):
                    return result
    except exceptions.InferenceError:
        pass
