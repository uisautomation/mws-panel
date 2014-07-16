# --------------------------------------------------------------------------
# Copyright (c) 2012, University of Cambridge Computing Service
#
# This file is part of the Lookup/Ibis client library.
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Dean Rasheed (dev-group@ucs.cam.ac.uk)
# --------------------------------------------------------------------------

"""
DTO classes for transferring data from the server to client in the web
service API.

All web service API methods return an instance or a list of one of these
DTO classes, or a primitive type such as a bool, int or string.

In the case of an error, an IbisException will be raised which will
contain an instance of an IbisError DTO.
"""

import base64
from datetime import date
from xml.parsers import expat

import sys
if sys.hexversion < 0x02040000:
    from sets import Set as set

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

class IbisDto(object):
    """
    Base class for all DTO classes. This defines a couple of methods used
    when unmarshalling DTOs from XML.
    """
    # All properties
    __slots__ = []

    # Properties marked as @XmlAttribte in the JAXB class
    xml_attrs = set()

    # Properties marked as @XmlElement in the JAXB class
    xml_elems = set()

    # Properties marked as @XmlElementWrapper in the JAXB class
    xml_arrays = set()

    def __init__(self, attrs={}):
        """
        Create an IbisDto from the attributes of an XML node. This just
        sets the properties marked as @XmlAttribute in the JAXB class.
        """
        for attr in self.__class__.__slots__:
            setattr(self, attr, None)
        for attr in self.__class__.xml_attrs:
            setattr(self, attr, attrs.get(attr))

    def start_child_element(self, tagname):
        """
        Start element callback invoked during XML parsing when the opening
        tag of a child element is encountered. This creates and returns any
        properties marked as @XmlElementWrapper in the JAXB class, so that
        child collections can be populated.
        """
        if tagname in self.__class__.xml_arrays:
            if getattr(self, tagname) == None: setattr(self, tagname, [])
            return getattr(self, tagname)
        return None

    def end_child_element(self, tagname, data):
        """
        End element callback invoked during XML parsing when the end tag of
        a child element is encountered, and the tag's data is available. This
        sets the value of any properties marked as @XmlElement in the JAXB
        class.
        """
        if tagname in self.__class__.xml_elems:
            setattr(self, tagname, data)

# --------------------------------------------------------------------------
# IbisPerson: see uk.ac.cam.ucs.ibis.dto.IbisPerson.java
# --------------------------------------------------------------------------
class IbisPerson(IbisDto):
    """
    Class representing a person returned by the web services API. Note that
    the identifier is the person's primary identifier (typically their CRSid),
    regardless of which identifier was used to query for the person.
    """
    __slots__ = ["cancelled", "identifier", "displayName", "registeredName",
                 "surname", "visibleName", "misAffiliation", "identifiers",
                 "attributes", "institutions", "groups", "directGroups",
                 "id", "ref", "unflattened"]

    xml_attrs = set(["cancelled", "id", "ref"])

    xml_elems = set(["identifier", "displayName", "registeredName",
                     "surname", "visibleName", "misAffiliation"])

    xml_arrays = set(["identifiers", "attributes", "institutions",
                      "groups", "directGroups"])

    def __init__(self, attrs={}):
        """ Create an IbisPerson from the attributes of an XML node. """
        IbisDto.__init__(self, attrs)
        if self.cancelled != None:
            self.cancelled = self.cancelled.lower() == "true"
        self.unflattened = False

    def is_staff(self):
        """
        Returns true if the person is a member of staff.

        Note that this tests for an misAffiliation of "", "staff" or
        "staff,student" since some members of staff will have a blank
        misAffiliation.
        """
        return self.misAffiliation == None or\
               self.misAffiliation != "student";

    def is_student(self):
        """
        Returns true if the person is a student.

        This tests for an misAffiliation of "student" or "staff,student".
        """
        return self.misAffiliation != None and\
               self.misAffiliation.find("student") != -1;

    def unflatten(self, em):
        """ Unflatten a single IbisPerson. """
        if self.ref:
            person = em.get_person(self.ref)
            if not person.unflattened:
                person.unflattened = True
                unflatten_insts(em, person.institutions)
                unflatten_groups(em, person.groups)
                unflatten_groups(em, person.directGroups)
            return person
        return self

def unflatten_people(em, people):
    """ Unflatten a list of IbisPerson objects (done in place). """
    if people:
        for idx, person in enumerate(people):
            people[idx] = person.unflatten(em)

# --------------------------------------------------------------------------
# IbisInstitution: see uk.ac.cam.ucs.ibis.dto.IbisInstitution.java
# --------------------------------------------------------------------------
class IbisInstitution(IbisDto):
    """
    Class representing an institution returned by the web services API.
    """
    __slots__ = ["cancelled", "instid", "name", "acronym",
                 "attributes", "contactRows", "members", "parentInsts",
                 "childInsts", "groups", "membersGroups", "managedByGroups",
                 "id", "ref", "unflattened"]

    xml_attrs = set(["cancelled", "instid", "id", "ref"])

    xml_elems = set(["name", "acronym"])

    xml_arrays = set(["attributes", "contactRows", "members",
                      "parentInsts", "childInsts", "groups",
                      "membersGroups", "managedByGroups"])

    def __init__(self, attrs={}):
        """ Create an IbisInstitution from the attributes of an XML node. """
        IbisDto.__init__(self, attrs)
        if self.cancelled != None:
            self.cancelled = self.cancelled.lower() == "true"
        self.unflattened = False

    def unflatten(self, em):
        """ Unflatten a single IbisInstitution. """
        if self.ref:
            inst = em.get_institution(self.ref)
            if not inst.unflattened:
                inst.unflattened = True
                unflatten_contact_rows(em, inst.contactRows)
                unflatten_people(em, inst.members)
                unflatten_insts(em, inst.parentInsts)
                unflatten_insts(em, inst.childInsts)
                unflatten_groups(em, inst.groups)
                unflatten_groups(em, inst.membersGroups)
                unflatten_groups(em, inst.managedByGroups)
            return inst
        return self

def unflatten_insts(em, insts):
    """ Unflatten a list of IbisInstitution objects (done in place). """
    if insts:
        for idx, inst in enumerate(insts):
            insts[idx] = inst.unflatten(em)

# --------------------------------------------------------------------------
# IbisGroup: see uk.ac.cam.ucs.ibis.dto.IbisGroup.java
# --------------------------------------------------------------------------
class IbisGroup(IbisDto):
    """
    Class representing a group returned by the web services API.
    """
    __slots__ = ["cancelled", "groupid", "name", "title", "description",
                 "email", "membersOfInst", "members", "directMembers",
                 "owningInsts", "managesInsts", "managesGroups",
                 "managedByGroups", "readsGroups", "readByGroups",
                 "includesGroups", "includedByGroups",
                 "id", "ref", "unflattened"]

    xml_attrs = set(["cancelled", "groupid", "id", "ref"])

    xml_elems = set(["name", "title", "description", "emails",
                     "membersOfInst"])

    xml_arrays = set(["members", "directMembers",
                      "owningInsts", "managesInsts",
                      "managesGroups", "managedByGroups",
                      "readsGroups", "readByGroups",
                      "includesGroups", "includedByGroups"])

    def __init__(self, attrs={}):
        """ Create an IbisGroup from the attributes of an XML node. """
        IbisDto.__init__(self, attrs)
        if self.cancelled != None:
            self.cancelled = self.cancelled.lower() == "true"
        self.unflattened = False

    def unflatten(self, em):
        """ Unflatten a single IbisGroup. """
        if self.ref:
            group = em.get_group(self.ref)
            if not group.unflattened:
                group.unflattened = True
                if group.membersOfInst:
                    group.membersOfInst = group.membersOfInst.unflatten(em)
                unflatten_people(em, group.members)
                unflatten_people(em, group.directMembers)
                unflatten_insts(em, group.owningInsts)
                unflatten_insts(em, group.managesInsts)
                unflatten_groups(em, group.managesGroups)
                unflatten_groups(em, group.managedByGroups)
                unflatten_groups(em, group.readsGroups)
                unflatten_groups(em, group.readByGroups)
                unflatten_groups(em, group.includesGroups)
                unflatten_groups(em, group.includedByGroups)
            return group
        return self

def unflatten_groups(em, groups):
    """ Unflatten a list of IbisGroup objects (done in place). """
    if groups:
        for idx, group in enumerate(groups):
            groups[idx] = group.unflatten(em)

# --------------------------------------------------------------------------
# IbisIdentifier: see uk.ac.cam.ucs.ibis.dto.IbisIdentifier.java
# --------------------------------------------------------------------------
class IbisIdentifier(IbisDto):
    """
    Class representing a person's identifier, for use by the web services
    API.
    """
    __slots__ = ["scheme", "value"]

    xml_attrs = set(["scheme"])

# --------------------------------------------------------------------------
# IbisAttribute: see uk.ac.cam.ucs.ibis.dto.IbisAttribute.java
# --------------------------------------------------------------------------
class IbisAttribute(IbisDto):
    """
    Class representing an attribute of a person or institution returned by
    the web services API. Note that for institution attributes, the instid,
    visibility and owningGroupid fields will be null.
    """
    __slots__ = ["attrid", "scheme", "value", "binaryData", "comment",
                 "instid", "visibility", "effectiveFrom", "effectiveTo",
                 "owningGroupid"]

    xml_attrs = set(["attrid", "scheme", "instid", "visibility",
                     "effectiveFrom", "effectiveTo", "owningGroupid"])

    xml_elems = set(["value", "binaryData", "comment"])

    def __init__(self, attrs={}):
        """ Create an IbisAttribute from the attributes of an XML node. """
        IbisDto.__init__(self, attrs)
        if self.attrid != None:
            self.attrid = long(self.attrid)
        if self.effectiveFrom != None:
            self.effectiveFrom = parse_date(self.effectiveFrom)
        if self.effectiveTo != None:
            self.effectiveTo = parse_date(self.effectiveTo)

    def end_child_element(self, tagname, data):
        """
        Overridden end element callback to decode binary data.
        """
        IbisDto.end_child_element(self, tagname, data)
        if tagname == "binaryData" and self.binaryData != None:
            self.binaryData = base64.b64decode(self.binaryData)

    def encoded_string(self):
        """
        Encode this attribute as an ASCII string suitable for passing as a
        parameter to a web service API method. This string is compatible with
        {@link #valueOf(java.lang.String)} on the corresponding Java class,
        used on the server to decode the attribute parameter.

        NOTE: This requires that the attribute's {@link #scheme} field be
        set, and typically the {@link #value} or {@link #binaryData} should
        also be set.
        """
        if not self.scheme:
            raise ValueError("Attribute scheme must be set")

        result = "scheme:%s" % base64.b64encode(self.scheme)
        if self.attrid != None:
            result = "%s,attrid:%d" % (result, self.attrid)
        if self.value != None:
            result = "%s,value:%s" % (result, base64.b64encode(self.value))
        if self.binaryData != None:
            result = "%s,binaryData:%s" %\
                     (result, base64.b64encode(self.binaryData))
        if self.comment != None:
            result = "%s,comment:%s" %\
                     (result, base64.b64encode(self.comment))
        if self.instid != None:
            result = "%s,instid:%s" %\
                     (result, base64.b64encode(self.instid))
        if self.visibility != None:
            result = "%s,visibility:%s" %\
                     (result, base64.b64encode(self.visibility))
        if self.effectiveFrom != None:
            result = "%s,effectiveFrom:%02d %s %d" %\
                     (result,
                      self.effectiveFrom.day,
                      _MONTHS[self.effectiveFrom.month-1],
                      self.effectiveFrom.year)
        if self.effectiveTo != None:
            result = "%s,effectiveTo:%02d %s %d" %\
                     (result,
                      self.effectiveTo.day,
                      _MONTHS[self.effectiveTo.month-1],
                      self.effectiveTo.year)
        if self.owningGroupid != None:
            result = "%s,owningGroupid:%s" %\
                     (result, base64.b64encode(self.owningGroupid))
        return result

def parse_date(s):
    """ Parse a date string from XML. """
    s = s.strip()
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))

# --------------------------------------------------------------------------
# IbisError: see uk.ac.cam.ucs.ibis.dto.IbisError.java
# --------------------------------------------------------------------------
class IbisError(IbisDto):
    """
    Class representing an error returned by the web services API.
    """
    __slots__ = ["status", "code", "message", "details"]

    xml_attrs = set(["status"])

    xml_elems = set(["code", "message", "details"])

    def __init__(self, attrs={}):
        """ Create an IbisError from the attributes of an XML node. """
        IbisDto.__init__(self, attrs)
        if self.status != None:
            self.status = int(self.status)

# --------------------------------------------------------------------------
# IbisAttributeScheme: see uk.ac.cam.ucs.ibis.dto.IbisAttributeScheme.java
# --------------------------------------------------------------------------
class IbisAttributeScheme(IbisDto):
    """
    Class representing an attribute scheme. This may apply to attributes of
    people or institutions.
    """
    __slots__ = ["schemeid", "precedence", "ldapName", "displayName",
                 "dataType", "multiValued", "multiLined", "searchable",
                 "regexp"]

    xml_attrs = set(["schemeid", "precedence", "multiValued", "multiLined",
                     "searchable"])

    xml_elems = set(["ldapName", "displayName", "dataType", "regexp"])

    def __init__(self, attrs={}):
        """
        Create an IbisAttributeScheme from the attributes of an XML node.
        """
        IbisDto.__init__(self, attrs)
        if self.precedence != None:
            self.precedence = int(self.precedence)
        if self.multiValued != None:
            self.multiValued = self.multiValued.lower() == "true"
        if self.multiLined != None:
            self.multiLined = self.multiLined.lower() == "true"
        if self.searchable != None:
            self.searchable = self.searchable.lower() == "true"

# --------------------------------------------------------------------------
# IbisContactRow: see uk.ac.cam.ucs.ibis.dto.IbisContactRow.java
# --------------------------------------------------------------------------
class IbisContactRow(IbisDto):
    """
    Class representing an institution contact row, for use by the web
    services API.
    """
    __slots__ = ["description", "bold", "italic", "addresses", "emails",
                 "people", "phoneNumbers", "webPages", "unflattened"]

    xml_attrs = set(["bold", "italic"])

    xml_elems = set(["description"])

    xml_arrays = set(["addresses", "emails", "people", "phoneNumbers",
                      "webPages"])

    def __init__(self, attrs={}):
        """ Create an IbisContactRow from the attributes of an XML node. """
        IbisDto.__init__(self, attrs)
        if self.bold != None:
            self.bold = self.bold.lower() == "true"
        if self.italic != None:
            self.italic = self.italic.lower() == "true"
        self.unflattened = False

    def unflatten(self, em):
        """ Unflatten a single IbisContactRow. """
        if not self.unflattened:
            self.unflattened = True
            unflatten_people(em, self.people)
        return self

def unflatten_contact_rows(em, contact_rows):
    """ Unflatten a list of IbisContactRow objects (done in place). """
    if contact_rows:
        for idx, contact_row in enumerate(contact_rows):
            contact_rows[idx] = contact_row.unflatten(em)

# --------------------------------------------------------------------------
# IbisContactPhoneNumber:
#     see uk.ac.cam.ucs.ibis.dto.IbisContactPhoneNumber.java
# --------------------------------------------------------------------------
class IbisContactPhoneNumber(IbisDto):
    """
    Class representing a phone number held on an institution contact row, for
    use by the web services API.
    """
    __slots__ = ["phoneType", "number", "comment"]

    xml_attrs = set(["phoneType"])

    xml_elems = set(["number", "comment"])

# --------------------------------------------------------------------------
# IbisContactWebPage: see uk.ac.cam.ucs.ibis.dto.IbisContactWebPage.java
# --------------------------------------------------------------------------
class IbisContactWebPage(IbisDto):
    """
    Class representing a web page referred to by an institution contact row,
    for use by the web services API.
    """
    __slots__ = ["url", "label"]

    xml_elems = set(["url", "label"])

# --------------------------------------------------------------------------
# IbisResult: see uk.ac.cam.ucs.ibis.dto.IbisResult.java
# --------------------------------------------------------------------------
class IbisResult(IbisDto):
    """
    Class representing the top-level container for all results.

    This may be just a simple textual value or it may contain more complex
    entities such as people, institutions, groups, attributes, etc.
    """
    __slots__ = ["version", "value", "person", "institution", "group",
                 "identifier", "attribute", "error", "people",
                 "institutions", "groups", "attributes", "attributeSchemes",
                 "entities"]

    xml_attrs = set(["version"])

    xml_elems = set(["value", "person", "institution", "group",
                     "identifier", "attribute", "error", "entities"])

    xml_arrays = set(["people", "institutions", "groups",
                      "attributes", "attributeSchemes"])

    class Entities(IbisDto):
        """
        Nested class to hold the full details of all the entities returned
        in a result. This is used only in the flattened result representation,
        where each of these entities will have a unique textual ID, and be
        referred to from the top-level objects returned (and by each other).

        In the hierarchical representation, this is not used, since all
        entities returned will be at the top-level, or directly contained in
        those top-level entities.
        """
        __slots__ = ["people", "institutions", "groups"]

        xml_arrays = set(["people", "institutions", "groups"])

    class EntityMap:
        """
        Nested class to assist during the unflattening process, maintaining
        efficient maps from IDs to entities (people, institutions and groups).
        """
        def __init__(self, result):
            """
            Construct an entity map from a flattened IbisResult.
            """
            self.people_by_id = {}
            self.insts_by_id = {}
            self.groups_by_id = {}

            if result.entities.people:
                for person in result.entities.people:
                    self.people_by_id[person.id] = person
            if result.entities.institutions:
                for inst in result.entities.institutions:
                    self.insts_by_id[inst.id] = inst
            if result.entities.groups:
                for group in result.entities.groups:
                    self.groups_by_id[group.id] = group

        def get_person(self, id):
            return self.people_by_id.get(id)

        def get_institution(self, id):
            return self.insts_by_id.get(id)

        def get_group(self, id):
            return self.groups_by_id.get(id)

    def unflatten(self):
        """
        Unflatten this IbisResult object, resolving any internal ID refs
        to build a fully fledged object tree.

        This is necessary if the IbisResult was constructed from XML/JSON in
        its flattened representation (with the "flatten" parameter set to
        true).

        On entry, the IbisResult object may have people, institutions or
        groups in it with "ref" fields referring to objects held in the
        "entities" lists. After unflattening, all such references will have
        been replaced by actual object references, giving an object tree that
        can be traversed normally.

        Returns this IbisResult object, with its internals unflattened.
        """
        if self.entities:
            em = IbisResult.EntityMap(self)

            if self.person:
                self.person = self.person.unflatten(em)
            if self.institution:
                self.institution = self.institution.unflatten(em)
            if self.group:
                self.group = self.group.unflatten(em)

            unflatten_people(em, self.people)
            unflatten_insts(em, self.institutions)
            unflatten_groups(em, self.groups)

        return self

# --------------------------------------------------------------------------
# IbisResultParser: unmarshaller for IbisResult objects
# --------------------------------------------------------------------------
class IbisResultParser:
    """
    Class to parse the XML from the server and produce an IbisResult.
    """
    def __init__(self):
        self.result = None
        self.node_stack = []
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.char_data

    def start_element(self, tagname, attrs):
        element = None
        if self.node_stack:
            if tagname == "person":
                element = IbisPerson(attrs)
            elif tagname == "institution":
                element = IbisInstitution(attrs)
            elif tagname == "group":
                element = IbisGroup(attrs)
            elif tagname == "identifier":
                element = IbisIdentifier(attrs)
            elif tagname == "attribute":
                element = IbisAttribute(attrs)
            elif tagname == "error":
                element = IbisError(attrs)
            elif tagname == "attributeScheme":
                element = IbisAttributeScheme(attrs)
            elif tagname == "contactRow":
                element = IbisContactRow(attrs)
            elif tagname == "phoneNumber":
                element = IbisContactPhoneNumber(attrs)
            elif tagname == "webPage":
                element = IbisContactWebPage(attrs)
            elif tagname == "entities":
                element = IbisResult.Entities(attrs)
            else:
                parent = self.node_stack[-1]
                if (not isinstance(parent, list)) and\
                   (not isinstance(parent, dict)):
                    element = parent.start_child_element(tagname)
            if element == None:
                element = {"tagname": tagname}
        elif tagname != "result":
            raise Exception("Invalid root element: '%s'" % tagname)
        else:
            element = IbisResult(attrs)
            self.result = element
        self.node_stack.append(element)

    def end_element(self, tagname):
        if self.node_stack:
            element = self.node_stack[-1]
            self.node_stack.pop()
            if self.node_stack:
                parent = self.node_stack[-1]
                if isinstance(parent, list):
                    if isinstance(element, dict):
                        parent.append(element.get("data"))
                    else:
                        parent.append(element)
                elif not isinstance(parent, dict):
                    if isinstance(element, dict):
                        data = element.get("data")
                    else:
                        data = element
                    parent.end_child_element(tagname, data)
        else:
            raise Exception("Unexpected closing tag: '%s'" % tagname)

    def char_data(self, data):
        if self.node_stack:
            element = self.node_stack[-1]
            if isinstance(element, IbisIdentifier):
                if element.value != None: element.value += data
                else: element.value = data
            elif isinstance(element, dict):
                if element.has_key("data"): element["data"] += data
                else: element["data"] = data

    def parse_xml(self, data):
        """
        Parse XML data from the specified string and return an IbisResult.
        """
        self.parser.Parse(data)
        return self.result.unflatten()

    def parse_xml_file(self, file):
        """
        Parse XML data from the specified file and return an IbisResult.
        """
        self.parser.ParseFile(file)
        return self.result.unflatten()
