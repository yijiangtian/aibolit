# The MIT License (MIT)
#
# Copyright (c) 2020 Aibolit
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from enum import Enum, auto
from cached_property import cached_property  # type: ignore
from collections import namedtuple
from itertools import islice, repeat, chain

import javalang.tree
from javalang.tree import Node
from typing import Union, Any, Set, Dict, Type, List, Iterator
from networkx import DiGraph, dfs_labeled_edges, dfs_preorder_nodes  # type: ignore


class ASTNodeType(Enum):
    ANNOTATION = auto()
    ANNOTATION_DECLARATION = auto()
    ANNOTATION_METHOD = auto()
    ARRAY_CREATOR = auto()
    ARRAY_INITIALIZER = auto()
    ARRAY_SELECTOR = auto()
    ASSERT_STATEMENT = auto()
    ASSIGNMENT = auto()
    BASIC_TYPE = auto()
    BINARY_OPERATION = auto()
    BLOCK_STATEMENT = auto()
    BREAK_STATEMENT = auto()
    CAST = auto()
    CATCH_CLAUSE = auto()
    CATCH_CLAUSE_PARAMETER = auto()
    CLASS_CREATOR = auto()
    CLASS_DECLARATION = auto()
    CLASS_REFERENCE = auto()
    COLLECTION = auto()  # Custom type, represent set (as a node) in AST
    COMPILATION_UNIT = auto()
    CONSTANT_DECLARATION = auto()
    CONSTRUCTOR_DECLARATION = auto()
    CONTINUE_STATEMENT = auto()
    CREATOR = auto()
    DECLARATION = auto()
    DO_STATEMENT = auto()
    DOCUMENTED = auto()
    ELEMENT_ARRAY_VALUE = auto()
    ELEMENT_VALUE_PAIR = auto()
    ENHANCED_FOR_CONTROL = auto()
    ENUM_BODY = auto()
    ENUM_CONSTANT_DECLARATION = auto()
    ENUM_DECLARATION = auto()
    EXPLICIT_CONSTRUCTOR_INVOCATION = auto()
    EXPRESSION = auto()
    FIELD_DECLARATION = auto()
    FOR_CONTROL = auto()
    FOR_STATEMENT = auto()
    FORMAL_PARAMETER = auto()
    IF_STATEMENT = auto()
    IMPORT = auto()
    INFERRED_FORMAL_PARAMETER = auto()
    INNER_CLASS_CREATOR = auto()
    INTERFACE_DECLARATION = auto()
    INVOCATION = auto()
    LAMBDA_EXPRESSION = auto()
    LITERAL = auto()
    LOCAL_VARIABLE_DECLARATION = auto()
    MEMBER = auto()
    MEMBER_REFERENCE = auto()
    METHOD_DECLARATION = auto()
    METHOD_INVOCATION = auto()
    METHOD_REFERENCE = auto()
    PACKAGE_DECLARATION = auto()
    PRIMARY = auto()
    REFERENCE_TYPE = auto()
    RETURN_STATEMENT = auto()
    STATEMENT = auto()
    STATEMENT_EXPRESSION = auto()
    STRING = auto()  # Custom type, represent just string in AST
    SUPER_CONSTRUCTOR_INVOCATION = auto()
    SUPER_MEMBER_REFERENCE = auto()
    SUPER_METHOD_INVOCATION = auto()
    SWITCH_STATEMENT = auto()
    SWITCH_STATEMENT_CASE = auto()
    SYNCHRONIZED_STATEMENT = auto()
    TERNARY_EXPRESSION = auto()
    THIS = auto()
    THROW_STATEMENT = auto()
    TRY_RESOURCE = auto()
    TRY_STATEMENT = auto()
    TYPE = auto()
    TYPE_ARGUMENT = auto()
    TYPE_DECLARATION = auto()
    TYPE_PARAMETER = auto()
    VARIABLE_DECLARATION = auto()
    VARIABLE_DECLARATOR = auto()
    VOID_CLASS_REFERENCE = auto()
    WHILE_STATEMENT = auto()


MethodInvocationParams = namedtuple('MethodInvocationParams', ['object_name', 'method_name'])

MemberReferenceParams = namedtuple('MemberReferenceParams', ('object_name', 'member_name', 'unary_operator'))


class AST:
    _NODE_SKIPED = -1

    def __init__(self, networkx_tree: DiGraph, root: int):
        self.tree = networkx_tree
        self.root = root

    @staticmethod
    def build_from_javalang(javalang_ast_root: Node) -> 'AST':
        tree = DiGraph()
        root = AST._build_from_javalang(tree, javalang_ast_root)
        return AST(tree, root)

    def __str__(self) -> str:
        printed_graph = ''
        depth = 0
        print_step = 4
        for _, destination, edge_type in dfs_labeled_edges(self.tree, self.root):
            if edge_type == 'forward':
                if depth > 0:
                    printed_graph += ' ' * depth + '|---'
                node_type = self.get_type(destination)
                printed_graph += str(node_type)
                if node_type == ASTNodeType.STRING:
                    printed_graph += ': ' + self.get_attr(destination, 'string')
                printed_graph += '\n'
                depth += print_step
            elif edge_type == 'reverse':
                depth -= print_step
        return printed_graph

    def subtrees_with_root_type(self, root_type: ASTNodeType) -> Iterator[List[int]]:
        '''
        Yields subtrees with given type of the root.
        If such subtrees are one including the other, only the larger one is
        going to be in resulted sequence.
        '''
        is_inside_subtree = False
        current_subtree_root = -1  # all node indexes are positive
        subtree: List[int] = []
        for _, destination, edge_type in dfs_labeled_edges(self.tree, self.root):
            if edge_type == 'forward':
                if is_inside_subtree:
                    subtree.append(destination)
                elif self.tree.nodes[destination]['type'] == root_type:
                    subtree.append(destination)
                    is_inside_subtree = True
                    current_subtree_root = destination
            elif edge_type == 'reverse' and destination == current_subtree_root:
                is_inside_subtree = False
                yield subtree
                subtree = []

    def children_with_type(self, node: int, child_type: ASTNodeType) -> Iterator[int]:
        '''
        Yields children of node with given type.
        '''
        for child in self.tree.succ[node]:
            if self.tree.nodes[child]['type'] == child_type:
                yield child

    def all_children_with_type(self, node: int, child_type: ASTNodeType) -> Iterator[int]:
        '''
        Yields all children of node with given type.
        '''
        for child in self.tree.succ[node]:
            if self.tree.nodes[child]['type'] == child_type:
                yield child
                self.all_children_with_type(child, child_type)

    def get_first_n_children_with_type(self, node: int, child_type: ASTNodeType, quantity: int) -> List[int]:
        '''
        Returns first quantity of children of node with type child_type.
        Resulted list is padded with None to length quantity.
        '''
        children_with_type = (child for child in self.tree.succ[node] if self.get_type(child) == child_type)
        children_with_type_padded = chain(children_with_type, repeat(None))
        return list(islice(children_with_type_padded, 0, quantity))

    def get_binary_operation_name(self, node: int) -> str:
        assert(self.get_type(node) == ASTNodeType.BINARY_OPERATION)
        name_node, = islice(self.children_with_type(node, ASTNodeType.STRING), 1)
        return self.get_attr(name_node, 'string')

    def get_line_number_from_children(self, node: int) -> int:
        for child in self.tree.succ[node]:
            cur_line = self.get_attr(child, 'source_code_line', -1)
            if cur_line >= 0:
                return cur_line
        return 0

    @cached_property
    def node_types(self) -> List[ASTNodeType]:
        '''
        Yields types of nodes in preorder tree traversal.
        '''
        return [self.tree.nodes[node]['type'] for node in dfs_preorder_nodes(self.tree, self.root)]

    def nodes_by_type(self, type: ASTNodeType) -> Iterator[int]:
        return (node for node in self.tree.nodes if self.tree.nodes[node]['type'] == type)

    def get_attr(self, node: int, attr_name: str, default_value: Any = None) -> Any:
        return self.tree.nodes[node].get(attr_name, default_value)

    def get_type(self, node: int) -> ASTNodeType:
        return self.get_attr(node, 'type')

    def get_method_invocation_params(self, invocation_node: int) -> MethodInvocationParams:
        assert(self.get_type(invocation_node) == ASTNodeType.METHOD_INVOCATION)
        # first two STRING nodes represent object and method names
        children = list(self.children_with_type(invocation_node, ASTNodeType.STRING))
        if len(children) == 1:
            return MethodInvocationParams('', self.get_attr(children[0], 'string'))

        return MethodInvocationParams(self.get_attr(children[0], 'string'),
                                      self.get_attr(children[1], 'string'))

    def get_member_reference_params(self, member_reference_node: int) -> MemberReferenceParams:
        assert(self.get_type(member_reference_node) == ASTNodeType.MEMBER_REFERENCE)
        params = [self.get_attr(child, 'string') for child in
                  self.children_with_type(member_reference_node, ASTNodeType.STRING)]

        member_reference_params: MemberReferenceParams
        if len(params) == 1:
            member_reference_params = MemberReferenceParams(object_name='', member_name=params[0],
                                                            unary_operator='')
        elif len(params) == 2:
            member_reference_params = MemberReferenceParams(object_name=params[0], member_name=params[1],
                                                            unary_operator='')
        elif len(params) == 3:
            member_reference_params = MemberReferenceParams(unary_operator=params[0], object_name=params[1],
                                                            member_name=params[2])
        else:
            raise ValueError('Node has 0 or more then 3 children with type "STRING": ' + str(params))

        return member_reference_params

    @staticmethod
    def _build_from_javalang(tree: DiGraph, javalang_node: Node) -> int:
        node_index = len(tree) + 1
        tree.add_node(node_index)
        AST._extract_javalang_node_attributes(tree, javalang_node, node_index)
        AST._iterate_over_children_list(tree, javalang_node.children, node_index)
        return node_index

    @staticmethod
    def _iterate_over_children_list(tree: DiGraph, children_list: List[Any], parent_index: int) -> None:
        for child in children_list:
            if isinstance(child, list):
                AST._iterate_over_children_list(tree, child, parent_index)
            else:
                child_index = AST._handle_javalang_ast_node(tree, child)
                if child_index != AST._NODE_SKIPED:
                    tree.add_edge(parent_index, child_index)

    @staticmethod
    def _extract_javalang_node_attributes(tree: DiGraph, javalang_node: Node, node_index: int) -> None:
        tree.add_node(node_index, type=AST._javalang_types_map[type(javalang_node)])

        if hasattr(javalang_node.position, 'line'):
            tree.add_node(node_index, source_code_line=javalang_node.position.line)

    @staticmethod
    def _handle_javalang_ast_node(tree: DiGraph, javalang_node: Union[Node, Set[Any], str]) -> int:
        if isinstance(javalang_node, Node):
            return AST._build_from_javalang(tree, javalang_node)
        elif isinstance(javalang_node, set):
            return AST._handle_javalang_collection_node(tree, javalang_node)
        elif isinstance(javalang_node, str):
            return AST._handle_javalang_string_node(tree, javalang_node)

        return AST._NODE_SKIPED

    @staticmethod
    def _handle_javalang_string_node(tree: DiGraph, string_node: str) -> int:
        node_index = len(tree) + 1
        tree.add_node(node_index, type=ASTNodeType.STRING, string=string_node)
        return node_index

    @staticmethod
    def _handle_javalang_collection_node(tree: DiGraph, collection_node: Set[Any]) -> int:
        node_index = len(tree) + 1
        tree.add_node(node_index, type=ASTNodeType.COLLECTION)
        for item in collection_node:
            if type(item) == str:
                string_node_index = AST._handle_javalang_string_node(tree, item)
                tree.add_edge(node_index, string_node_index)
            elif item is not None:
                raise RuntimeError('Unexpected javalang AST node type {} inside \
                                    "COLLECTION" node'.format(type(item)))
        return node_index

    _javalang_types_map: Dict[Type, ASTNodeType] = {
        javalang.tree.Annotation: ASTNodeType.ANNOTATION,
        javalang.tree.AnnotationDeclaration: ASTNodeType.ANNOTATION_DECLARATION,
        javalang.tree.AnnotationMethod: ASTNodeType.ANNOTATION_METHOD,
        javalang.tree.ArrayCreator: ASTNodeType.ARRAY_CREATOR,
        javalang.tree.ArrayInitializer: ASTNodeType.ARRAY_INITIALIZER,
        javalang.tree.ArraySelector: ASTNodeType.ARRAY_SELECTOR,
        javalang.tree.AssertStatement: ASTNodeType.ASSERT_STATEMENT,
        javalang.tree.Assignment: ASTNodeType.ASSIGNMENT,
        javalang.tree.BasicType: ASTNodeType.BASIC_TYPE,
        javalang.tree.BinaryOperation: ASTNodeType.BINARY_OPERATION,
        javalang.tree.BlockStatement: ASTNodeType.BLOCK_STATEMENT,
        javalang.tree.BreakStatement: ASTNodeType.BREAK_STATEMENT,
        javalang.tree.Cast: ASTNodeType.CAST,
        javalang.tree.CatchClause: ASTNodeType.CATCH_CLAUSE,
        javalang.tree.CatchClauseParameter: ASTNodeType.CATCH_CLAUSE_PARAMETER,
        javalang.tree.ClassCreator: ASTNodeType.CLASS_CREATOR,
        javalang.tree.ClassDeclaration: ASTNodeType.CLASS_DECLARATION,
        javalang.tree.ClassReference: ASTNodeType.CLASS_REFERENCE,
        javalang.tree.CompilationUnit: ASTNodeType.COMPILATION_UNIT,
        javalang.tree.ConstantDeclaration: ASTNodeType.CONSTANT_DECLARATION,
        javalang.tree.ConstructorDeclaration: ASTNodeType.CONSTRUCTOR_DECLARATION,
        javalang.tree.ContinueStatement: ASTNodeType.CONTINUE_STATEMENT,
        javalang.tree.Creator: ASTNodeType.CREATOR,
        javalang.tree.Declaration: ASTNodeType.DECLARATION,
        javalang.tree.Documented: ASTNodeType.DOCUMENTED,
        javalang.tree.DoStatement: ASTNodeType.DO_STATEMENT,
        javalang.tree.ElementArrayValue: ASTNodeType.ELEMENT_ARRAY_VALUE,
        javalang.tree.ElementValuePair: ASTNodeType.ELEMENT_VALUE_PAIR,
        javalang.tree.EnhancedForControl: ASTNodeType.ENHANCED_FOR_CONTROL,
        javalang.tree.EnumBody: ASTNodeType.ENUM_BODY,
        javalang.tree.EnumConstantDeclaration: ASTNodeType.ENUM_CONSTANT_DECLARATION,
        javalang.tree.EnumDeclaration: ASTNodeType.ENUM_DECLARATION,
        javalang.tree.ExplicitConstructorInvocation: ASTNodeType.EXPLICIT_CONSTRUCTOR_INVOCATION,
        javalang.tree.Expression: ASTNodeType.EXPRESSION,
        javalang.tree.FieldDeclaration: ASTNodeType.FIELD_DECLARATION,
        javalang.tree.ForControl: ASTNodeType.FOR_CONTROL,
        javalang.tree.FormalParameter: ASTNodeType.FORMAL_PARAMETER,
        javalang.tree.ForStatement: ASTNodeType.FOR_STATEMENT,
        javalang.tree.IfStatement: ASTNodeType.IF_STATEMENT,
        javalang.tree.Import: ASTNodeType.IMPORT,
        javalang.tree.InferredFormalParameter: ASTNodeType.INFERRED_FORMAL_PARAMETER,
        javalang.tree.InnerClassCreator: ASTNodeType.INNER_CLASS_CREATOR,
        javalang.tree.InterfaceDeclaration: ASTNodeType.INTERFACE_DECLARATION,
        javalang.tree.Invocation: ASTNodeType.INVOCATION,
        javalang.tree.LambdaExpression: ASTNodeType.LAMBDA_EXPRESSION,
        javalang.tree.Literal: ASTNodeType.LITERAL,
        javalang.tree.LocalVariableDeclaration: ASTNodeType.LOCAL_VARIABLE_DECLARATION,
        javalang.tree.Member: ASTNodeType.MEMBER,
        javalang.tree.MemberReference: ASTNodeType.MEMBER_REFERENCE,
        javalang.tree.MethodDeclaration: ASTNodeType.METHOD_DECLARATION,
        javalang.tree.MethodInvocation: ASTNodeType.METHOD_INVOCATION,
        javalang.tree.MethodReference: ASTNodeType.METHOD_REFERENCE,
        javalang.tree.PackageDeclaration: ASTNodeType.PACKAGE_DECLARATION,
        javalang.tree.Primary: ASTNodeType.PRIMARY,
        javalang.tree.ReferenceType: ASTNodeType.REFERENCE_TYPE,
        javalang.tree.ReturnStatement: ASTNodeType.RETURN_STATEMENT,
        javalang.tree.Statement: ASTNodeType.STATEMENT,
        javalang.tree.StatementExpression: ASTNodeType.STATEMENT_EXPRESSION,
        javalang.tree.SuperConstructorInvocation: ASTNodeType.SUPER_CONSTRUCTOR_INVOCATION,
        javalang.tree.SuperMemberReference: ASTNodeType.SUPER_MEMBER_REFERENCE,
        javalang.tree.SuperMethodInvocation: ASTNodeType.SUPER_METHOD_INVOCATION,
        javalang.tree.SwitchStatement: ASTNodeType.SWITCH_STATEMENT,
        javalang.tree.SwitchStatementCase: ASTNodeType.SWITCH_STATEMENT_CASE,
        javalang.tree.SynchronizedStatement: ASTNodeType.SYNCHRONIZED_STATEMENT,
        javalang.tree.TernaryExpression: ASTNodeType.TERNARY_EXPRESSION,
        javalang.tree.This: ASTNodeType.THIS,
        javalang.tree.ThrowStatement: ASTNodeType.THROW_STATEMENT,
        javalang.tree.TryResource: ASTNodeType.TRY_RESOURCE,
        javalang.tree.TryStatement: ASTNodeType.TRY_STATEMENT,
        javalang.tree.Type: ASTNodeType.TYPE,
        javalang.tree.TypeArgument: ASTNodeType.TYPE_ARGUMENT,
        javalang.tree.TypeDeclaration: ASTNodeType.TYPE_DECLARATION,
        javalang.tree.TypeParameter: ASTNodeType.TYPE_PARAMETER,
        javalang.tree.VariableDeclaration: ASTNodeType.VARIABLE_DECLARATION,
        javalang.tree.VariableDeclarator: ASTNodeType.VARIABLE_DECLARATOR,
        javalang.tree.VoidClassReference: ASTNodeType.VOID_CLASS_REFERENCE,
        javalang.tree.WhileStatement: ASTNodeType.WHILE_STATEMENT,
    }
