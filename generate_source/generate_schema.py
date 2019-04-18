import json
import re


sizes = ['xs', 'sm', 'md', 'lg', 'xl']

keywords = ['for']

boolean_prop = {
    'type': 'boolean',
    'allowNull': True,
    'default': None}

d_type_props = [(f'd_{d}', boolean_prop)
                for d in ['inline',
                          'block',
                          'contents',
                          'flex',
                          'grid',
                          'inline_block',
                          'inline_flex',
                          'inline_grid',
                          'inline_table',
                          'list_item',
                          'run_in',
                          'table',
                          'table_caption',
                          'table_column_group',
                          'table_header_group',
                          'table_footer_group',
                          'table_row_group',
                          'table_cell',
                          'table_column',
                          'table_row',
                          'none',
                          'initial',
                          'inherit']]

grid_list_props = [(f'grid_list_{s}', boolean_prop)
                   for s in sizes]

spacing_props = [(f'{type_}{direction}_{size}', boolean_prop)
                 for type_ in ['m', 'p']
                 for direction in ['t', 'b', 'l', 'r', 'x', 'y', 'a']
                 for size in ['auto'] + [str(s) for s in range(0, 6)]]


def identity(x):
    return x


def kebab_to_camel(name):
    return ''.join(
        map(
            lambda x: x.capitalize(),
            name.split('-')[1:]))


def property_to_snake_case(name):
    return re.sub('(?!^)([A-Z]+)', r'_\1', name).lower()


def make_grid_props(prefix, start, end):
    return [(f'{prefix}{s}{n}', boolean_prop)
            for s in sizes
            for n in range(start, end)]


def make_type(api_type):
    if type(api_type) is str:
        # Vuetify api schema contains casing errors
        api_type = api_type.casefold()

        if api_type == 'number':
            api_type = 'float'

    if api_type in ['boolean', 'string', 'object', 'any', 'float']:
        return {'type': api_type}

    # Type info of arrays is not included in the vuetify api json file, use any for now.
    # TODO: Retrieve type info for arrays
    if api_type == 'array':
        return {'type': 'array',
                'items': {
                    'type': 'any'}}

    if type(api_type) is list:
        return {'type': 'union',
                'oneOf': list(filter(identity, map(make_type, api_type)))}

    if api_type == 'function':
        # Not supported
        return None

    print(f'Unknown type: {api_type}')
    return None


def make_property(data):
    if 'type' not in data.keys():
        return None

    api_name = data['name']

    # compressed properties like: (size)(1-12) and d-{type} are handled on a higher level
    if '(' in api_name or '{' in api_name:
        return None

    schema_name = property_to_snake_case(api_name)

    if schema_name in keywords:
        schema_name += '_'

    schema_type = make_type(data['type'])

    if schema_type is None:
        return None

    schema_type['allowNull'] = True
    schema_type['default'] = None

    return schema_name, schema_type


def make_widget(data):
    name, attributes = data
    widget_name = kebab_to_camel(name)

    if 'props' not in attributes.keys():
        # Widgets without props are directives, internationalization or $vuetify
        return None

    properties = list(filter(identity, map(make_property, attributes['props'])))

    # compressed properties like: (size)(1-12) and d-{type}
    if widget_name == 'Container':
        properties += d_type_props + grid_list_props
    elif widget_name == 'Flex':
        properties += make_grid_props('', 1, 13) + make_grid_props('offset_', 0, 13) + make_grid_props('order_', 1, 13)
    elif widget_name == 'Layout':
        properties += d_type_props

    if widget_name in ['Container', 'Content', 'Flex', 'Layout']:
        properties += spacing_props

    return (widget_name, {
        'inherits': ['VuetifyWidget'],
        'properties': dict(properties)})


def generate_schema(vuetify_api_file_name, base_schema_file_name, schema_output_file_name):
    api_data = json.loads(open(vuetify_api_file_name).read())
    base = json.loads(open(base_schema_file_name).read())

    schema_tuples = filter(identity, map(make_widget, api_data.items()))

    base['widgets'] = {**base['widgets'], **dict(schema_tuples)}

    with open(schema_output_file_name, 'w') as outfile:
        json.dump(base, outfile)
