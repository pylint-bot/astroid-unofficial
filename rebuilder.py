# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""this module contains utilities for rebuilding a compiler.ast or _ast tree in
order to get a single ASTNG representation

:author:    Sylvain Thenault
:copyright: 2008-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2008-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from logilab.astng import ASTNGBuildingException, InferenceError, NodeRemoved
from logilab.astng import nodes
from logilab.astng.utils import ASTVisitor, REDIRECT
from logilab.astng.infutils import YES, Instance


CONST_NAME_TRANSFORMS = {'None':  None,
                         'True':  True,
                         'False': False}


class RebuildVisitor(ASTVisitor):
    """Visitor to transform an AST to an ASTNG
    """
    def __init__(self, ast_mode):
        self.asscontext = None
        self._metaclass = None
        self._global_names = None
        self._delayed = dict((name, []) for name in ('class', 'function', 'assattr'))
        self.set_line_info = (ast_mode == '_ast')
        self._ast_mode = (ast_mode == '_ast')
        self._asscontext = None

    def visit(self, node, parent):
        if node is None: # some attributes of some nodes are just None
            print  "node with parent %s is None" % parent
            return None
        node.parent = parent # XXX it seems that we need it sometimes
        cls_name = node.__class__.__name__
        if not self._ast_mode: # compiler
            # TODO if cls_name in ('AssAttr', 'AssName', 'Slice', 'Subscript')
            self.check_missing_delstmt(node, childnode, cls_name)
        _method_suffix = REDIRECT.get(cls_name, cls_name).lower()
        _visit = getattr(self, "visit_%s" % _method_suffix )
        try:
            newnode = _visit(node)
        except NodeRemoved:
            return
        child = None
        if newnode is None:
            return
        for child in newnode.get_children():
            if child is not None:
                child.parent = newnode
            else:
                print "newnode %s has None as child" % newnode
        # newnode.set_line_info(child)
        _leave = getattr(self, "leave_%s" % _method_suffix, None )
        if _leave:
            _leave(newnode)
        return newnode


    # take node arguments to be usable as visit/leave methods
    def push_asscontext(self, node=None):
        self._asscontext = self.asscontext
        self.asscontext = None
        return True
    def pop_asscontext(self, node=None):
        self.asscontext = self._asscontext
        self._asscontext = None

    def walk(self, node):
        newnode = self.visit(node, None)
        for name, nodes in self._delayed.items():
            delay_method = getattr(self, 'delayed_' + name)
            for node in nodes:
                delay_method(node)
        return newnode

    # general visit_<node> methods ############################################

    def visit_arguments(self, node): # XXX  parent...
        if node.vararg:
            node.parent.set_local(node.vararg, node)
        if node.kwarg:
            node.parent.set_local(node.kwarg, node)

    def visit_assign(self, node):
        self.asscontext = "Ass"
        return self._visit_assign(node)
        self.asscontext = None
        # XXX call leave_assign  here ?

    def xxx_leave_assign(self, newnode): #XXX  parent...
        klass = newnode.parent.frame()
        if (isinstance(klass, nodes.Class)
            and isinstance(newnode.value, nodes.CallFunc)
            and isinstance(newnode.value.func, nodes.Name)):
            func_name = newnode.value.func.name
            for ass_node in newnode.targets:
                try:
                    meth = klass[ass_node.name]
                    if isinstance(meth, nodes.Function):
                        if func_name in ('classmethod', 'staticmethod'):
                            meth.type = func_name
                        try:
                            meth.extra_decorators.append(newnode.value)
                        except AttributeError:
                            meth.extra_decorators = [newnode.value]
                except (AttributeError, KeyError):
                    continue
        elif getattr(newnode.targets[0], 'name', None) == '__metaclass__':
            # XXX check more...
            self._metaclass[-1] = 'type' # XXX get the actual metaclass
        return newnode

    def visit_class(self, node): # TODO
        """visit an Class node to become astng"""
        newnode = self._visit_class(node)
        newnode.name = node.name
        self._metaclass.append(self._metaclass[-1])
        metaclass = self._metaclass.pop()
        if not newnode.bases:
            # no base classes, detect new / style old style according to
            # current scope
            node._newstyle = metaclass == 'type'
        return newnode

    def delayed_class(self, node):
        node.parent.frame().set_local(node.name, node)

    def visit_decorators(self, node): # TODO
        """visiting an Decorators node"""
        return self._visit_decorators(node)

    def leave_decorators(self, node): # XXX parent
        """python >= 2.4
        visit a Decorator node -> check for classmethod and staticmethod
        """
        for decorator_expr in node.nodes:
            if isinstance(decorator_expr, nodes.Name) and \
                   decorator_expr.name in ('classmethod', 'staticmethod'):
                node.parent.type = decorator_expr.name
        return newnode

    def visit_from(self, node): # TODO XXX root !
        """visit an From node to become astng"""
        # add names imported by the import to locals
        for (name, asname) in node.names:
            if name == '*':
                try:
                    imported = node.root().import_module(node.modname)
                except ASTNGBuildingException:
                    continue
                for name in imported.wildcard_import_names():
                    node.parent.set_local(name, node)
            else:
                node.parent.set_local(asname or name, node)

    def visit_function(self, node): # XXX parent
        """visit an Function node to become astng"""
        self._global_names.append({})
        newnode = self._visit_function(node)
        self._delayed['function'].append(newnode)
        newnode.name = node.name
        return newnode

    def leave_function(self, node): # TODO
        """leave a Function node -> pop the last item on the stack"""
        self._global_names.pop()

    def delayed_function(self, newnode):
        frame = newnode.parent.frame()
        if isinstance(frame, nodes.Class):
            if newnode.name == '__new__':
                newnode.type = 'classmethod'
            else:
                newnode.type = 'method'
        frame.set_local(newnode.name, newnode)

    def visit_assattr(self, node): # TODO
        """visit an Getattr node to become astng"""
        print self.indent + "visit_assattr" + "XXX"
        assc, self.asscontext = self.asscontext, None
        newnode = self._visit_assattr(node)
        self.asscontext = assc
        self._delayed['assattr'].append(newnode)
        return newnode

    def visit_delattr(self, node): # TODO
        """visit an Getattr node to become astng"""
        assc, self.asscontext = self.asscontext, None
        newnode = self._visit_delattr(node)
        self.asscontext = assc
        return newnode

    def visit_global(self, node):
        """visit an Global node to become astng"""
        newnode = nodes.Global(node.names)
        if self._global_names: # global at the module level, no effect
            for name in node.names:
                self._global_names[-1].setdefault(name, []).append(newnode)
        return newnode

    def visit_import(self, node): # XXX parent !
        """visit an Import node to become astng"""
        for (name, asname) in node.names:
            name = asname or name
            node.parent.set_local(name.split('.')[0], node)

    def visit_module(self, node):
        """visit an Module node to become astng"""
        self._metaclass = ['']
        self._global_names = []
        return self._visit_module(node)

    def visit_name(self, node):
        """visit an Name node to become astng"""
        newnode = self._visit_name(node)
        if newnode.name in CONST_NAME_TRANSFORMS:
            return nodes.Const(CONST_NAME_TRANSFORMS[newnode.name])
        return newnode

    def visit_assname(self, node): # XXX parent
        if self.asscontext is not None:
            if self._global_names and node.name in self._global_names[-1]:
                node.root().set_local(node.name, node)
            else:
                node.parent.set_local(node.name, node)
    visit_delname = visit_assname

    visit_subscript = push_asscontext
    leave_subscript = pop_asscontext
    
    def delayed_assattr(self, node):
        """visit a AssAttr node -> add name to locals, handle members
        definition
        """
        try:
            frame = node.frame()
            for infered in node.expr.infer():
                if infered is YES:
                    continue
                try:
                    if infered.__class__ is Instance:
                        infered = infered._proxied
                        iattrs = infered.instance_attrs
                    elif isinstance(infered, Instance):
                        # Const, Tuple, ... we may be wrong, may be not, but
                        # anyway we don't want to pollute builtin's namespace
                        continue
                    else:
                        iattrs = infered.locals
                except AttributeError:
                    # XXX log error
                    #import traceback
                    #traceback.print_exc()
                    continue
                values = iattrs.setdefault(node.attrname, [])
                if node in values:
                    continue
                # get assign in __init__ first XXX useful ?
                if frame.name == '__init__' and values and not \
                       values[0].frame().name == '__init__':
                    values.insert(0, node)
                else:
                    values.append(node)
        except InferenceError:
            pass

    # --- additional methods ----

    def _build_excepthandler(self, node, exctype, excobj, body):
        newnode = nodes.ExceptHandler()
        newnode.type = self.visit(exctype, node)
        self.asscontext = "Ass"
        newnode.name = self.visit(excobj, node)
        self.asscontext = None
        newnode.body = [self.visit(child, node) for child in body]
        return newnode

