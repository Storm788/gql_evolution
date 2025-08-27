def explain_graphql_query(schema_ast, query):
    from graphql import parse, build_ast_schema, print_ast, GraphQLSchema
    from graphql.language.ast import (
        DocumentNode, FieldNode, SelectionSetNode, OperationDefinitionNode,
        FragmentDefinitionNode, FragmentSpreadNode, InlineFragmentNode,
    )
    from graphql.type import (
        GraphQLObjectType, GraphQLInterfaceType, GraphQLUnionType,
        GraphQLNonNull, GraphQLList, GraphQLInputObjectType,
    )

    schema: GraphQLSchema = build_ast_schema(schema_ast, assume_valid=True)

    # ---- metadata z AST: popisy fieldů na ObjectType i InterfaceType
    field_meta: dict[tuple[str, str], str | None] = {}
    from graphql.language.ast import ObjectTypeDefinitionNode, InterfaceTypeDefinitionNode
    for defn in schema_ast.definitions:
        if isinstance(defn, (ObjectTypeDefinitionNode, InterfaceTypeDefinitionNode)):
            parent = defn.name.value
            for fld in defn.fields or []:
                desc = fld.description.value if fld.description else None
                field_meta[(parent, fld.name.value)] = desc

    # ---- parse dotazu
    query_ast: DocumentNode = parse(query)

    # ---- seber definice fragmentů jménem
    fragments: dict[str, FragmentDefinitionNode] = {
        d.name.value: d
        for d in query_ast.definitions
        if isinstance(d, FragmentDefinitionNode)
    }

    # ---- utility
    def unwrap_type(gtype):
        while isinstance(gtype, (GraphQLNonNull, GraphQLList)):
            gtype = gtype.of_type
        return gtype

    def type_node_to_str(type_node) -> str:
        k = getattr(type_node, "kind", None) or type_node.kind  # graphql-core používá lower-case
        if k in ("NamedType", "named_type"):
            return type_node.name.value
        if k in ("NonNullType", "non_null_type"):
            return f"{type_node_to_str(type_node.type)}!"
        if k in ("ListType", "list_type"):
            return f"[{type_node_to_str(type_node.type)}]"
        raise ValueError(f"Unknown kind {k}")

    # ---- @param (stejné jako u tebe; drobná oprava defn.operation)
    var_lines: list[str] = []
    for defn in query_ast.definitions:
        if isinstance(defn, OperationDefinitionNode) and defn.variable_definitions:
            op = defn.operation.value if hasattr(defn.operation, "value") else defn.operation  # 'query'/'mutation'/'subscription'
            root_map = {
                "query": schema.query_type,
                "mutation": schema.mutation_type,
                "subscription": schema.subscription_type,
            }
            root_type = root_map.get(op)
            if not root_type:
                continue

            # vezmeme 1. root field jen kvůli lookupu inputů (jako v tvém kódu)
            root_sel = next((s for s in defn.selection_set.selections if isinstance(s, FieldNode)), None)
            if not root_sel:
                continue
            root_field_def = root_type.fields.get(root_sel.name.value) if isinstance(root_type, GraphQLObjectType) else None
            first_arg_type = None
            if root_field_def and root_field_def.args:
                first_arg = root_field_def.args[next(iter(root_field_def.args))]
                first_arg_type = unwrap_type(first_arg.type)

            for var_def in defn.variable_definitions:
                name = var_def.variable.name.value
                type_str = type_node_to_str(var_def.type)
                desc = None
                if isinstance(first_arg_type, GraphQLInputObjectType):
                    input_fields = first_arg_type.fields
                    if name in input_fields:
                        desc = input_fields[name].description
                desc = " ".join(desc.split()) if desc else "missing description"
                var_lines.append(f"# @param {{{type_str}}} {name} - {desc}")

    # ---- @property (s podporou fragmentů)
    out_lines: list[str] = []
    seen: set[tuple[str, str]] = set()  # (path, base_type_name) pro deduplikaci

    def print_field(parent_type, fname: str, path: str):
        """Vytiskni jeden field (když existuje na parent_type) do out_lines."""
        if isinstance(parent_type, (GraphQLObjectType, GraphQLInterfaceType)):
            fld_def = parent_type.fields.get(fname)
        else:
            fld_def = None

        if not fld_def:
            return

        base_type = unwrap_type(fld_def.type)
        base_name = getattr(base_type, "name", "Object")
        desc = field_meta.get((parent_type.name, fname))
        if desc:
            desc = " ".join(desc.split())
        else:
            desc = ""
        key = (path, base_name)
        if key in seen:
            return
        seen.add(key)
        out_lines.append(f'# @property {{{base_name}}} {path} - {desc}'.rstrip())

    def walk(sel_set: SelectionSetNode, parent_type, prefix: str):
        """Rekurzivní průchod selection setem s podporou Field/FragmentSpread/InlineFragment."""
        if not sel_set:
            return
        for sel in sel_set.selections:
            # 1) Pole
            if isinstance(sel, FieldNode):
                fname = sel.name.value
                path = f"{prefix}.{fname}" if prefix else fname
                # Union nemá vlastní fields -> pole na unionu jdou jen přes inline fragment s typeCondition
                if isinstance(parent_type, GraphQLUnionType):
                    # pokud někdo zapsal field přímo na union bez inline fragmentu, přeskoč
                    continue
                print_field(parent_type, fname, path)

                # rekurze do podvýběru
                if sel.selection_set:
                    # po unwrappingu může být child typ Object/Interface/Union
                    child_type = unwrap_type(
                        (parent_type.fields.get(fname).type if isinstance(parent_type, (GraphQLObjectType, GraphQLInterfaceType)) else None)
                    )
                    if child_type:
                        walk(sel.selection_set, child_type, path)

            # 2) Named fragment: ...Frag
            elif isinstance(sel, FragmentSpreadNode):
                frag = fragments.get(sel.name.value)
                if not frag:
                    continue
                # typeCondition může změnit parent typ
                new_parent = parent_type
                if frag.type_condition:
                    tname = frag.type_condition.name.value
                    new_parent = schema.get_type(tname) or parent_type
                walk(frag.selection_set, new_parent, prefix)

            # 3) Inline fragment: ... on Type { ... } (nebo bez typeCondition = stejné jako parent)
            elif isinstance(sel, InlineFragmentNode):
                new_parent = parent_type
                if sel.type_condition:
                    tname = sel.type_condition.name.value
                    new_parent = schema.get_type(tname) or parent_type
                walk(sel.selection_set, new_parent, prefix)

    # spustit walk od kořene u každé operace
    for defn in query_ast.definitions:
        if isinstance(defn, OperationDefinitionNode):
            op = defn.operation.value if hasattr(defn.operation, "value") else defn.operation
            root_map = {
                "query": schema.query_type,
                "mutation": schema.mutation_type,
                "subscription": schema.subscription_type,
            }
            root = root_map.get(op)
            if root:
                walk(defn.selection_set, root, prefix="")

    # ---- hlavička + dotaz
    header = []
    if var_lines:
        header.append("# ")
        header.extend(var_lines)
    header.append("# @returns {Object}")
    if out_lines:
        header.append("# ")
        header.extend(out_lines)

    return "\n".join(header + ["", print_ast(query_ast)])
