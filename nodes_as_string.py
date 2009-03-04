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
"""this module contains exceptions used in the astng library

:author:    Sylvain Thenault
:copyright: 2008-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2008-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

"""This module renders ASTNG nodes to string representation.
It will problably not work on compiler.ast or _ast trees.
"""


from logilab.astng.utils import ASTVisitor

INDENT = '    ' # 4 spaces ; keep indentation variable


def _import_string(names):
    """return a list of (name, asname) formatted as a string"""
    _names = []
    for name, asname in names:
        if asname is not None:
            _names.append('%s as %s' % (name, asname))
        else:
            _names.append(name)
    return  ', '.join(_names)


class AsStringVisitor(ASTVisitor):
    """Visitor to render an ASTNG node as string """

    def __call__(self, node):
        """Makes this visitor behave as a simple function"""
        return node.accept(self)
    
    def _stmt_list(self, stmts):
        """return a list of nodes to string"""
        stmts = '\n'.join([n.accept(self) for n in stmts])
        return INDENT + stmts.replace('\n', '\n'+INDENT)

    
    ## visit_<node> methods ###########################################
    def visit_assattr(self, node):
        """return an astng.AssAttr node as string"""
        return self.visit_getattr(node)

    def visit_assert(self, node):
        """return an astng.Assert node as string"""
        if node.fail:
            return 'assert %s, %s' % (node.test.accept(self),
                                        node.fail.accept(self))
        return 'assert %s' % node.test.accept(self)

    def visit_assname(self, node):
        """return an astng.AssName node as string"""
        return node.name

    def visit_assign(self, node):
        """return an astng.Assign node as string"""
        lhs = ' = '.join([n.accept(self) for n in node.targets])
        return '%s = %s' % (lhs, node.value.accept(self))
    
    def visit_augassign(self, node):
        """return an astng.AugAssign node as string"""
        return '%s %s %s' % (node.target.accept(self), node.op, node.value.accept(self))
    
    def visit_backquote(self, node):
        """return an astng.Backquote node as string"""
        return '`%s`' % node.value.accept(self)
    
    def visit_binop(self, node):
        """return an astng.BinOp node as string"""
        return '(%s) %s (%s)' % (node.left.accept(self), node.op, node.right.accept(self))

    def visit_boolop(self, node):
        """return an astng.BoolOp node as string"""
        return (' %s ' % node.op).join(['(%s)' % n.accept(self)
                                            for n in node.values])
    
    def visit_break(self, node):
        """return an astng.Break node as string"""
        return 'break'
    
    def visit_callfunc(self, node):
        """return an astng.CallFunc node as string"""
        expr_str = node.func.accept(self)
        args = ', '.join([arg.accept(self) for arg in node.args])
        if node.starargs:
            args += ', *%s' % node.starargs.accept(self)
        if node.kwargs:
            args += ', **%s' % node.kwargs.accept(self)
        return '%s(%s)' % (expr_str, args)
    
    def visit_class(self, node):
        """return an astng.Class node as string"""
        bases =  ', '.join([n.accept(self) for n in node.bases])
        bases = bases and '(%s)' % bases or ''
        docs = node.doc and '\n%s"""%s"""' % (INDENT, node.doc) or ''
        return 'class %s%s:%s\n%s\n' % (node.name, bases, docs,
                                            self._stmt_list( node.body))
    
    def visit_compare(self, node):
        """return an astng.Compare node as string"""
        rhs_str = ' '.join(['%s %s' % (op, expr.accept(self))
                            for op, expr in node.ops])
        return '%s %s' % (node.left.accept(self), rhs_str)

    def visit_comprehension(self, node):
        """return an astng.Comprehension node as string"""
        ifs = ''.join([ ' if %s' % n.accept(self) for n in node.ifs])
        return 'for %s in %s%s' % (node.target.accept(self),
                                    node.iter.accept(self), ifs )

    def visit_const(self, node):
        """return an astng.Const node as string"""
        return repr(node.value)
    
    def visit_continue(self, node):
        """return an astng.Continue node as string"""
        return 'continue'
    
    def visit_delete(self, node): # XXX check if correct
        """return an astng.Delete node as string"""
        return 'del %s' % ', '.join([child.accept(self) 
                                for child in node.targets])

    def visit_delattr(self, node):
        """return an astng.DelAttr node as string"""
        return self.visit_getattr(node)

    def visit_delname(self, node):
        """return an astng.DelName node as string"""
        return node.name

    def visit_decorators(self, node):
        """return an astng.Decorators node as string"""
        return '@%s\n' % '\n@'.join(item.accept(self) for item in node.items)

    def visit_dict(self, node):
        """return an astng.Dict node as string"""
        return '{%s}' % ', '.join(['%s: %s' % (key.accept(self), 
                            value.accept(self)) for key, value in node.items])
    
    def visit_discard(self, node):
        """return an astng.Discard node as string"""
        return node.value.accept(self)
    
    def visit_excepthandler(self, node):
        if node.type:
            if node.name:
                excs = 'except %s, %s' % (node.type.accept(self),
                                        node.name.accept(self))
            else:
                excs = 'except %s' % node.type.accept(self)
        else:
            excs = 'except'
        return '%s:\n%s' % (excs, self._stmt_list(node.body))
    
    def visit_ellipsis(self, node):
        """return an astng.Ellipsis node as string"""
        return '...'
    
    def visit_empty(self, node):
        """return an Empty node as string"""
        return ''
    
    def visit_exec(self, node):
        """return an astng.Exec node as string"""
        if node.globals:
            return 'exec %s in %s, %s' % (node.expr.accept(self),
                                        node.locals.accept(self),
                                        node.globals.accept(self))
        if node.locals:
            return 'exec %s in %s' % (node.expr.accept(self),
                                    node.locals.accept(self))
        return 'exec %s' % node.expr.accept(self)

    def visit_for(self, node):
        """return an astng.For node as string"""
        fors = 'for %s in %s:\n%s' % (node.target.accept(self),
                                    node.iter.accept(self),
                                    self._stmt_list( node.body))
        if node.orelse:
            fors = '%s\nelse:\n%s' % (fors, self._stmt_list(node.orelse))
        return fors
    
    def visit_from(self, node):
        """return an astng.From node as string"""
        # XXX level
        return 'from %s import %s' % (node.modname, _import_string(node.names))
    
    def visit_function(self, node):
        """return an astng.Function node as string"""
        fargs = node.format_args()
        decorate = node.decorators and node.decorators.accept(self)  or ''
        docs = node.doc and '\n%s"""%s"""' % (INDENT, node.doc) or ''
        return '%sdef %s(%s):%s\n%s' % (decorate, node.name, fargs, docs,
                                        self._stmt_list(node.body))
    
    def visit_genexpr(self, node):
        """return an astng.ListComp node as string"""
        return '(%s %s)' % (node.elt.accept(self), ' '.join([n.accept(self)
                                                    for n in node.generators]))
    
    def visit_getattr(self, node):
        """return an astng.Getattr node as string"""
        return '%s.%s' % (node.expr.accept(self), node.attrname)

    def visit_global(self, node):
        """return an astng.Global node as string"""
        return 'global %s' % ', '.join(node.names)
    
    def visit_if(self, node):
        """return an astng.If node as string"""
        cond, body = node.tests[0]
        ifs = ['if %s:\n%s' % (cond.accept(self), self._stmt_list(body))]
        for cond, body in node.tests[1:]:
            ifs.append('elif %s:\n%s' % (cond.accept(self), 
                                         self._stmt_list(body)))
        if node.orelse:
            ifs.append('else:\n%s' % self._stmt_list(node.orelse) )
        return '\n'.join(ifs)
    
    def visit_import(self, node):
        """return an astng.Import node as string"""
        return 'import %s' % _import_string(node.names)
    
    def visit_keyword(self, node):
        """return an astng.Keyword node as string"""
        return '%s=%s' % (node.arg, node.value.accept(self))
    
    def visit_lambda(self, node):
        """return an astng.Lambda node as string"""
        return 'lambda %s: %s' % (node.format_args(), node.body.accept(self))
    
    def visit_list(self, node):
        """return an astng.List node as string"""
        return '[%s]' % ', '.join([child.accept(self) for child in node.elts])
    
    def visit_listcomp(self, node):
        """return an astng.ListComp node as string"""
        return '[%s %s]' % (node.elt.accept(self), ' '.join([n.accept(self)
                                                for n in node.generators]))

    def visit_module(self, node):
        """return an astng.Module node as string"""
        docs = node.doc and '"""%s"""\n' % node.doc or ''
        stmts = '\n'.join([n.accept(self) for n in node.body])
        return docs + '\n'.join([n.accept(self) for n in node.body])
    
    def visit_name(self, node):
        """return an astng.Name node as string"""
        return node.name
    
    def visit_pass(self, node):
        """return an astng.Pass node as string"""
        return 'pass'
    
    def visit_print(self, node):
        """return an astng.Print node as string"""
        nodes = ', '.join([n.accept(self) for n in node.values])
        if not node.nl:
            nodes = '%s,' % nodes
        if node.dest:
            return 'print >> %s, %s' % (node.dest.accept(self), nodes)
        return 'print %s' % nodes
    
    def visit_raise(self, node):
        """return an astng.Raise node as string"""
        if node.type:
            if node.inst:
                if node.tback:
                    return 'raise %s, %s, %s' % (node.type.accept(self),
                                                node.inst.accept(self),
                                                node.tback.accept(self))
                return 'raise %s, %s' % (node.type.accept(self),
                                        node.inst.accept(self))
            return 'raise %s' % node.type.accept(self)
        return 'raise'

    def visit_return(self, node):
        """return an astng.Return node as string"""
        if node.value:
            return 'return %s' % node.value.accept(self)
        else:
            return 'return'
    
    def visit_subscript(self, node):
        """return an astng.Subscript node as string"""
        if node.sliceflag == 'index':
            index = ','.join([n.accept(self) for n in node.subs])
        else: # sliceflag == 'slice':
            slist = [sub and sub.accept(self) or '' for sub in node.subs]
            index = ':'.join(slist)
        return '%s[%s]' % (node.expr.accept(self), index)
    
    def visit_tryexcept(self, node):
        """return an astng.TryExcept node as string"""
        trys = ['try:\n%s' % self._stmt_list( node.body)]
        for handler in node.handlers:
            trys.append(handler.accept(self))
        if node.orelse:
            trys.append('else:\n%s' % self._stmt_list(node.orelse))
        return '\n'.join(trys)
    
    def visit_tryfinally(self, node):
        """return an astng.TryFinally node as string"""
        return 'try:\n%s\nfinally:\n%s' % (self._stmt_list( node.body),
                                        self._stmt_list(node.finalbody))
    
    def visit_tuple(self, node):
        """return an astng.Tuple node as string"""
        return '(%s)' % ', '.join([child.accept(self) for child in node.elts])
    
    def visit_unaryop(self, node):
        """return an astng.UnaryOp node as string"""
        return '%s%s' % (node.op, node.operand.accept(self))
    
    def visit_while(self, node):
        """return an astng.While node as string"""
        whiles = 'while %s:\n%s' % (node.test.accept(self),
                                    self._stmt_list(node.body))
        if node.orelse:
            whiles = '%s\nelse:\n%s' % (whiles, self._stmt_list(node.orelse))
        return whiles
    
    def visit_with(self, node): # XXX 'with' without 'as' is possible
        """return an astng.With node as string"""
        withs = 'with (%s) as (%s):\n%s' % (node.context_expr.accept(self),
                                        node.optional_vars.accept(self),
                                        self._stmt_list( node.body))
        return withs
    
    def visit_yield(self, node):
        """yield an ast.Yield node as string"""
        return 'yield %s' % node.value.accept(self)

    # XXX compat methods

    #visit_attribute = visit_getattr
    #visit_call = visit_callfunc
    #visit_classdef = visit_class
    #visit_expr = visit_discard
    #visit_functiondef = visit_function
    #visit_generatorexp = visit_genexpr
    #visit_importfrom = visit_from
    #visit_repr = visit_backquote

    # special ASTNG NoneType and Bool nodes
    def visit_nonetype(self, node):
        """return None for ans ASTNG NoneType node"""
        return 'None'

    def visit_bool(self, node):
        return str(node.value)

# this visitor is stateless, thus it can be reused
as_string = AsStringVisitor()

