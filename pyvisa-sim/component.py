# -*- coding: utf-8 -*-
"""
    pyvisa-sim.component
    ~~~~~~~~~~~~~~~~~~~~

    Base classes for devices parts.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""
import logging
from typing import Dict, Tuple, List, Optional, Any, Union

import stringparser

logger = logging.getLogger(__name__)

ValueT = Union[float, int, str]
SpecsT = Dict[str, Any]

# Sentinel used for when there should not be a response to a query
NoResponse = object()


def to_bytes(val: Union[Any, str]) -> Union[Any, bytes]:
    """Takes a text message and return a tuple
    """
    if val is NoResponse:
        return val
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    return val.encode()


class Property:
    """A device property.
    """

    def __init__(self, name: str, value: ValueT, specs: SpecsT) -> None:
        """
        :param name: name of the property
        :param value: default value
        :param specs: specification dictionary
        """

        prop_type = specs.get('type', None)
        if prop_type:
            for _typestr, _type in (('float', float), ('int', int), ('str', str)):
                if prop_type == _typestr:
                    prop_type = specs['type'] = _type
                    break
            else:
                logger.debug(
                    'No type conversion requested for property {prop!r} '
                    'albeit explicit type specification {vtype!r} given.'.format(prop=name, vtype=prop_type))
        else:
            prop_type = specs['type'] = type(value)
            logger.info('No explicit type specification given for property {prop!r}. '
                        'Using default value\'s type {dtype!r} as fallback.'.format(prop=name, dtype=prop_type))

        for bound in ('min', 'max'):
            if bound in specs:
                specs[bound] = prop_type(specs[bound])

        if 'valid' in specs:
            if not isinstance(specs['valid'], dict):
                specs['valid'] = set([prop_type(val) for val in specs['valid']])

        self.name = name
        self.specs = specs
        # TODO Create a property `value`
        self.init_value(value)

    def init_value(self, value: ValueT):
        """Initialize the value hold by the Property.
        """
        self.set_value(value)

    def get_value(self) -> ValueT:
        """Return the value stored by the Property.
        """
        if 'valid' in self.specs and isinstance(self.specs['valid'], dict):
            return self.specs['valid'][self._value]

        return self._value

    def set_value(self, value: ValueT):
        """Set the value
        """
        self._value = self.validate_value(value)

    def validate_value(self, value: ValueT) -> ValueT:
        """Validate that a value match the Property specs.
        """
        specs = self.specs
        value_parsed = specs['type'](value) if 'type' in specs else value

        if 'min' in specs and value_parsed < specs['min']:
            raise ValueError
        if 'max' in specs and value_parsed > specs['max']:
            raise ValueError
        if 'valid' in specs:
            if isinstance(specs['valid'], dict):
                if value_parsed not in specs['valid']:
                    raise ValueError('Expected value to be one of {valid!r}; '
                                     'got instead: {value!r}'.format(valid=specs['valid'].keys(), value=value_parsed))
            else:
                if value_parsed not in specs['valid']:
                    raise ValueError('Expected value to be one of {valid!r}; '
                                     'got instead: {value!r}'.format(valid=specs['valid'], value=value_parsed))

        return value_parsed


class Component:
    """A component of a device.
    """

    def __init__(self):
        #: Stores the queries accepted by the device.
        #: query: response
        self._dialogues = {}  # type: Dict[bytes, bytes]

        #: Maps property names to value, type, validator
        self._properties = {}  # type: Dict[str, Property]

        #: Stores the getter queries accepted by the device.
        #: query: (property_name, response)
        self._getters = {}  # type: Dict[bytes, Tuple[str, str]]

        #: Stores the setters queries accepted by the device.
        #: (property_name, string parser query, response, error response)
        self._setters = []  # type: List[Tuple[str, stringparser.Parser, bytes, bytes]]

    def add_dialogue(self, query: str, response: str) -> None:
        """Add dialogue to device.

        :param query: query string
        :param response: response string
        """
        self._dialogues[to_bytes(query)] = to_bytes(response)

    def add_property(self, name: str, default_value, getter_pair, setter_triplet,
                     specs):
        """Add property to device

        :param name: property name
        :param default_value: default value as string
        :param getter_pair: (query, response)
        :param setter_triplet: (query, response, error)
        :param specs: specification of the Property
        """
        self._properties[name] = Property(name, default_value, specs)

        if getter_pair:
            query, response = getter_pair
            self._getters[to_bytes(query)] = name, response

        if setter_triplet:
            query, response, error = setter_triplet
            self._setters.append((name,
                                  stringparser.Parser(query),
                                  to_bytes(response),
                                  to_bytes(error)))

    def match(self, query: bytes):
        """Try to find a match for a query in the instrument commands.

        """
        raise NotImplementedError()

    def _match_dialog(self, query: bytes, dialogues: Optional[Dict[bytes, bytes]] = None) -> Optional[bytes]:
        """Tries to match in dialogues

        :param query: message tuple
        :return: response if found
        """
        if dialogues is None:
            dialogues = self._dialogues

        # Try to match in the queries
        if query in dialogues:
            response = dialogues[query]
            logger.debug('Found response in queries: %s' % repr(response))

            return response

        return None

    def _match_getters(self, query: bytes, getters: Optional[Dict[bytes, Tuple[str, str]]] = None) -> Optional[bytes]:
        """Tries to match in getters

        :param query: message
        :return: response if found
        """
        if getters is None:
            getters = self._getters

        if query in getters:
            name, response = getters[query]
            logger.debug('Found response in getter of %s' % name)
            response = response.format(self._properties[name].get_value())

            return response.encode('utf-8')

        return None

    def _match_setters(self, query: bytes) -> Optional[bytes]:
        """Tries to match in setters

        :param query: message
        :return: response if found
        """
        q = query.decode('utf-8')
        for name, parser, response, error_response in self._setters:
            try:
                value = parser(q)
                logger.debug('Found response in setter of %s' % name)
            except ValueError:
                continue

            try:
                self._properties[name].set_value(value)
                return response
            except ValueError:
                if isinstance(error_response, bytes):
                    return error_response

                return self.error_response('command_error')  # types: ignore

        return None
