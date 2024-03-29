import argparse
import copy
from collections import namedtuple, Counter
import itertools
import os
from pathlib import Path
import json


"""
TODO:
    EitherType
"""


Param = namedtuple("Param", ["name", "type", "optional"])


def longclsname_to_haxeclass(jstype):
    splited_type = jstype.split(".")
    return ".".join([n.lower() for n in splited_type[:-1]]) + "." + splited_type[-1]


def jstype_to_haxe(jstype, void_allowed=False):
    if jstype.lower() in ["object", "*", "dynamic", "any", "function()"]:
        return "Dynamic"
    elif jstype.lower() in ["null"]:
        if void_allowed:
            return "Void"
        else:
            return "Dynamic"
    elif jstype.lower() in ["string"]:
        return "String"
    elif jstype == "(string|symbol)":
        return "String"
    elif jstype.lower() in ["float", "number"]:
        return "Float"
    elif jstype.lower() in ["integer"]:
        return "Int"
    elif jstype.lower() in ["bool", "boolean"]:
        return "Bool"
    elif jstype.lower() in ["function"]:
        return "Dynamic"
    elif jstype.lower() in ["array"]:
        return "Array<Dynamic>"
    elif "array." in jstype.lower():
        # Enlève le array.< et le >
        return "Array<" + jstype_to_haxe(jstype[7:-1]) + ">"
    elif jstype == "RegExp":
        return "EReg"

    elif jstype == "Element":
        return "js.html.Element"
    elif jstype == "XMLDocument":
        return "js.html.XMLDocument"
    elif jstype == "HTMLElement":
        return "js.html.HtmlElement"
    elif jstype == "HTMLDivElement":
        return "js.html.DivElement"
    elif jstype == "HTMLImageElement":
        return "js.html.ImageElement"
    elif jstype == "HTMLCanvasElement":
        return "js.html.CanvasElement"
    elif jstype == "CanvasPattern":
        return "js.html.CanvasPattern"
    elif jstype == "CanvasRenderingContext2D":
        return "js.html.CanvasRenderingContext2D"
    elif jstype == "Image":
        return "js.html.Image"
    elif jstype == "ImageData":
        return "js.html.ImageData"
    elif jstype == "HTMLVideoElement":
        return "js.html.VideoElement"
    elif jstype == "WebGLTexture":
        return "js.html.webgl.Texture"
    elif jstype == "WebGLRenderingContext":
        return "js.html.webgl.RenderingContext"
    elif jstype == "WebGLBuffer":
        return "js.html.webgl.Buffer"
    elif jstype == "WebGLProgram":
        return "js.html.webgl.Program"
    elif jstype == "WebGLFramebuffer":
        return "js.html.webgl.Framebuffer"
    elif jstype == "WebGLUniformLocation":
        return "js.html.webgl.UniformLocation"
    elif jstype == "ANGLE_instanced_arrays":
        return "js.html.webgl.extension.ANGLEInstancedArrays"
    elif jstype == "OES_vertex_array_object":
        return "js.html.webgl.extension.OESVertexArrayObject"
    elif jstype == "XMLHttpRequestResponseType":
        return "js.html.XMLHttpRequestResponseType"
    elif jstype == "XMLHttpRequest":
        return "js.html.XMLHttpRequest"
    elif jstype == "ProgressEvent":
        return "js.html.ProgressEvent"
    elif jstype == "Blob":
        return "js.html.Blob"
    elif jstype == "TouchEvent":
        return "js.html.TouchEvent"
    elif jstype == "MouseEvent":
        return "js.html.MouseEvent"
    elif jstype == "KeyboardEvent":
        return "js.html.KeyboardEvent"
    elif jstype == "GamepadEvent":
        return "Dynamic"
    elif jstype == "GamepadButton":
        return "js.html.GamepadButton"
    elif jstype == "CSSStyleRule":
        return "js.html.CSSStyleRule"
    elif jstype == "ArrayBuffer":
        return "js.lib.ArrayBuffer"
    elif jstype == "AudioContext":
        return "js.html.audio.AudioContext"
    elif jstype == "GLenum":
        return "Dynamic"
    elif jstype.endswith("Array"):
        return "js.lib." + jstype
    elif "<" in jstype and ">" in jstype:
        return "Dynamic"
    elif jstype == "FrameRequestCallback":
        return "Dynamic"
    elif jstype == "GamepadHapticActuator":
        return "Dynamic"

    ## Hacks
    if jstype == "ScaleManagerConfig":
        return "Dynamic"

    elif "." in jstype:
        if jstype in Class_.classes_index or jstype in TypeDef.typedef_indexes:
            return longclsname_to_haxeclass(jstype)
        else:
            # splited_type = jstype.split(".")
            # return ".".join([n.lower() for n in splited_type[:-2]]) + "." + ".".join(splited_type[-2:])
            return "Dynamic"

    # print("blablabl", jstype)
    return jstype


def good_name(name):
    if name == "switch":
        return "@:native('switch') ", "switch_"
    elif name == "default":
        return "@:native('default') ", "default_"
    elif name == "extern":
        return "@:native('extern') ", "extern_"
    elif name == "override":
        return "@:native('override') ", "override_"
    elif name == "enum":
        return "@:native('enum') ", "enum_"
    return "", name


def format_comment(comment, indent=1):
    if comment == "":
        return ""

    comment_lines = comment.split("\n")
    ret_comment = comment_lines[0] + "\n"
    for line in comment_lines[1:]:
        line = line.strip()
        ret_comment += " "*4*indent + " " + line + "\n"

    ret_comment += " "*4*indent
    return ret_comment


def format_class_name(name):
    return name.split("<")[0]


class Element:
    def __init__(self, element):
        self.name = element["name"]
        self.name = self.name.replace(";", "")
        self.comment = element["comment"]
        self.element = element


TypeDefProperty = namedtuple("TypeDefProperty", ["prefix", "name", "optional", "type_"])


class TypeDef(Element):
    typedef_indexes = {}

    def __init__(self, element):
        super().__init__(element)
        self.name = format_class_name(self.name)
        self.type_ = element["type"]["names"][0].lower()

        self.properties = []

        self.longname = format_class_name(element["longname"])
        TypeDef.typedef_indexes[self.longname] = self

    def __repr__(self):
        return self.name + ": " + self.type_

    def parse_properties(self):
        self.properties = []
        if "properties" not in self.element:
            return

        for prop in self.element["properties"]:
            if len(prop) == 0:
                continue
            if "." in prop["name"]:
                continue

            prefix, name = good_name(prop["name"])
            optional = False
            if "optional" in prop and prop["optional"]:
                optional = True

            type_ = "Dynamic"
            if len(prop["type"]["names"]) > 1:
                type_ = "Dynamic" # TODO EITHERTYPE
            else:
                type_ = jstype_to_haxe(prop["type"]["names"][0])

            # HACKS
            if self.name == "GameConfig" and name == "type":
                type_ = "Int"

            self.properties.append(TypeDefProperty(
                prefix=prefix,
                name=name,
                optional=optional,
                type_=type_
            ))

    def get_properties(self):
        doubles = set()
        self.parse_properties()
        properties = self.properties

        if "augments" not in self.element:
            return properties

        for prop in properties:
            doubles.add(prop.name)

        for augment in self.element["augments"]:
            if augment not in TypeDef.typedef_indexes:
                print("WARNING: augment not found : ", augment)
                continue
            typedef = TypeDef.typedef_indexes[augment]
            typedef_props = typedef.get_properties()

            for prop in typedef_props:
                if prop.name not in doubles:
                    doubles.add(prop.name)
                    properties.append(prop)

        return properties


    def gen_haxe(self):
        properties = self.get_properties()

        ret = ""
        if self.comment != "":
            ret = format_comment(self.comment, 0)

        ret += "typedef " + self.name + " = "

        if self.type_ == "object":
            if len(self.element["properties"]) == 0:
                ret += "Dynamic\n;"
                return

            ret += "{\n"
            for prop in properties:
                prop_name = prop.name
                if prop_name.isdigit():
                    prop_name = "_" + prop_name
                if prop.optional:
                    ret += "    @:optional "
                ret += prop.prefix + "var " + prop_name + ":"
                ret += prop.type_ + ";\n"
            ret += "}"

        elif self.type_ == "function":
            ret += "Dynamic"
        else:
            ret += jstype_to_haxe(self.type_)

        ret += ";\n"
        return ret


class Class_(Element):
    classes_index = {}

    def __init__(self, element):
        super().__init__(element)
        self.name = format_class_name(self.name)
        self.longname = format_class_name(element["longname"])
        Class_.classes_index[self.longname] = self
        self.members = []
        self.members_names = set()
        self.extends = None
        self.augments = []
        self.parse_augments()
        self.ctor = Function(element)

    def __repr__(self):
        return self.name + ": " + self.longname

    def add_member(self, member):
        self.members.append(member)

    def parse_augments(self):
        if "augments" not in self.element:
            return

        self.extends = self.element["augments"][0]
        if len(self.element["augments"]) > 1:
            self.augments = self.element["augments"][1:]

    def get_all_members(self):
        all_members = copy.copy(self.members)

        all_members_names = set()
        for member in self.members:
            all_members_names.add(member.name)
        if self.extends is not None and "<" not in self.extends:
            if self.extends in Class_.classes_index:
                for member in Class_.classes_index[self.extends].get_all_members():
                    all_members_names.add(member.name)

        for augment_class in self.augments:
            if "<" in augment_class and ">" in augment_class:
                print(augment_class)
                continue
            try:
                cls_ = Class_.classes_index[augment_class]
            except KeyError:
                print("NOT FOUND:", augment_class)
                continue
            for member in cls_.members:
                if member.name not in all_members_names:
                    all_members.append(member)
                    all_members_names.add(member.name)

        return all_members

    def gen_haxe(self):
        ret = ""
        if self.comment != "":
            ret = format_comment(self.comment, 0)

        ret += '@:native("' + self.longname + '")\n'
        ret += "extern class " + self.name
        if self.extends is not None and jstype_to_haxe(self.extends) != "Dynamic":
            ret += " extends " + jstype_to_haxe(self.extends)
        ret += " {\n"
        ret += "    public function new" + self.ctor.gen_parenthesis() + ";\n"

        function_overloading = {}
        names = [m.name for m in self.get_all_members()]
        names_counter = Counter(names)

        for member in self.get_all_members():
            # if "inherited" in element and element["inherited"]:
                # print("INHER", element["inherits"], self.longname)

            if names_counter[member.name] > 1:
                function_overloading.setdefault(member.name, [])
                function_overloading[member.name].append(member)
                continue

            ret += "    " + member.gen_haxe() + ";\n"

        for name, funcs in function_overloading.items():
            for func in funcs:
                if func.membertype == "attribute":
                    print(self.longname, func.membertype, func.name)
                    continue
                ret += "    @:overload(function" + func.gen_parenthesis() + ":" + jstype_to_haxe(func.returns) + "{})"
            ret += "    public function " + name + "():Void;\n"



        if len(names) != len(set(names)):
            print(self.name, names)


        ret += "}\n"

        # if "Sprite" in self.name:
        #     print(ret)
        return ret


class Member(Element):
    def __init__(self, element):
        super().__init__(element)
        try:
            self.memberof = element["memberof"]
        except:
            # print("No memberof:", element["meta"]["path"], element["name"])
            self.memberof = ""

        self.is_static = False
        if "scope" in element and element["scope"] == "static":
            self.is_static = True

    def __repr__(self):
        return self.name


class Attribute(Member):
    def __init__(self, element):
        self.membertype = "attribute"
        super().__init__(element)
        self.type_ = "Dynamic"
        self.parse_type()

    def parse_type(self):
        if "type" in self.element:
            self.type_ = self.element["type"]["names"][0]
            if len(self.element["type"]["names"]) > 1:
                self.type_ = "Dynamic" # TODO: EITHERTYPE
                # print("KIKOO", self.element)

    def gen_haxe(self, comment=True):
        prefix, name = good_name(self.name)
        type_ = jstype_to_haxe(self.type_)

        # Hacks
        if self.memberof == "Phaser.Tilemaps.ObjectLayer":
            if self.name == "objects":
                type_ = "Array<Dynamic>"

        ret = ""
        if comment and self.comment != "":
            ret = format_comment(self.comment, 1)

        ret += prefix + "public var " + name + ":" + type_

        return ret


class Function(Member):
    def __init__(self, element):
        self.membertype = "method"
        super().__init__(element)
        self.params = []
        self.parse_params()
        self.returns = "Void"
        if "returns" in element:
            if "type" not in element["returns"][0]:
                self.returns = "Dynamic"
            else:
                self.returns = element["returns"][0]["type"]["names"][0]

    def parse_params(self):
        if "params" not in self.element:
            return

        for param in self.element["params"]:
            if "name" not in param:
                continue
            if "." in param["name"]:
                continue
            if "type" in param:
                if len(param["type"]["names"]) > 1:
                    type_ = "Dynamic"
                    #TODO: Eithertype
                else:
                    type_ = param["type"]["names"][0]
            else:
                type_ = "Dynamic"
            optional = False
            if "optional" in param and param["optional"]:
                optional = True
            if "defaultvalue" in param:
                optional = True

            # Hacks
            if param["name"] == "xhrSettings":
                optional = True # Yurk
            if "description" in param and "it will\ndefault to the layer" in param["description"]:
                optional = True
            if self.memberof == "Phaser.GameObjects.GameObjectCreator" and type_ == "TileSprite":
                type_ = "Dynamic"

            self.params.append(Param(param["name"], type_, optional))

    def gen_parenthesis(self):
        return "(" + ", ".join([self.repr_param(p) for p in self.params]) + ")"

    def repr_param(self, param):
        prefix = "?" if param.optional else ""
        return prefix + param.name + ":" + jstype_to_haxe(param.type)

    def gen_haxe(self):
        prefix, name = good_name(self.name)

        if self.returns == "this":
            #TODO: retourne le type de la classe
            return_type = "Dynamic"
        else:
            return_type = jstype_to_haxe(self.returns)

        ret = ""
        if self.comment != "":
            ret = format_comment(self.comment, 1)
        ret += prefix

        if "scope" in self.element and self.element["scope"] == "static":
            ret += "static "

        ret += "public function " + name + self.gen_parenthesis() + ":" + return_type

        return ret


class Namespace(Element):
    namespaces_index = {}

    def __init__(self, element):
        super().__init__(element)
        self.longname = element["longname"]
        Namespace.namespaces_index[self.longname] = self
        self.members = []

    def add_member(self, member):
        for m in self.members:
            # CAN BE BETTER
            if m.name == member.name:
                return
        self.members.append(member)

    def gen_haxe(self):
        ret = ""
        if self.comment != "":
            ret = format_comment(self.comment, 0)

        ret += '@:native("' + self.longname + '")\n'

        # Hack
        if self.name == "Phaser":
            ret = ''

        ret += "class " + self.name + " {\n"
        for member in self.members:
            if member.comment != "":
                ret += "    " + format_comment(member.comment)
                ret += "static " + member.gen_haxe(comment=False) + ";\n"
            else:
                ret += "    static " + member.gen_haxe(comment=False) + ";\n"

        ret += "}\n"
        return ret


def main(jsdoc_json_path, output_path):
    phaser_json = json.load(open(jsdoc_json_path))

    all_kinds = set()
    all_scopes = set()
    typedefs = []
    classes = []
    attributes = []
    functions = []
    namespaces = []

    for element in phaser_json:
        if "scope" in element:
            all_scopes.add(element["scope"])
            if element["scope"] == "inner":
                continue
        else:
            ...
            # print("NOSCOP", element)
        if "access" in element and element["access"] == "private":
            continue

        all_kinds.add(element["kind"])
        if element["kind"] == "typedef":
            typedefs.append(TypeDef(element))

        elif element["kind"] == "class" or (element["kind"] == "namespace" and ("Component" in element["longname"] or "Color" in element["longname"])):
            if element["longname"] in Class_.classes_index:
                # Class_.classes_index.merge(element)
                ...
            else:
                classes.append(Class_(element))

        elif element["kind"] == "member":
            if "inherited" in element and element["inherited"]:
                continue
            if "overrides" in element:
                continue
            if "scope" in element and element["scope"] == "static":
                if element["memberof"] == "module.exports" or element["longname"] == "module.exports":
                    continue
                if "~" in element["memberof"]:
                    continue
                if "Phaser" not in element["longname"]:
                    continue

                if element["longname"] not in Class_.classes_index and "type" not in element:
                    if "undocumented" in element and element["undocumented"]:
                        continue
                    classes.append(Class_(element))
                    continue

            attributes.append(Attribute(element))

        elif element["kind"] == "function":
            if "inherited" in element and element["inherited"]:
                continue
            if "overrides" in element:
                continue

            functions.append(Function(element))

        elif element["kind"] == "namespace":
            namespaces.append(Namespace(element))

    all_errors_membersof = []

    for member in attributes:
        if member.memberof == "":
            continue
        if member.memberof in Class_.classes_index:
            Class_.classes_index[member.memberof].add_member(member)
        elif member.memberof in Namespace.namespaces_index:
            Namespace.namespaces_index[member.memberof].add_member(member)
        else:
            all_errors_membersof.append(member.element)

    for member in functions:
        if member.memberof == "":
            continue
        try:
            Class_.classes_index[member.memberof].add_member(member)
        except Exception as e:
            # print("bug", e)
            all_errors_membersof.append(member.element)


    # import pprint
    # pprint.pprint(all_errors_membersof)

    ## Write code

    for class_ in itertools.chain(classes, typedefs, namespaces):
        if class_.name in ["Class", "Math"]:
            continue #TODO

        if "." in class_.longname:
            path_class = longclsname_to_haxeclass(class_.longname).replace(".", "/")
        else:
            path_class = "phaser/" + class_.longname

        path = Path(path_class + ".hx")
        os.makedirs(str(output_path / path.parent), exist_ok=True)

        with open(str(output_path / path), "w") as f:
            package_line = "package "
            if "." in class_.longname:
                package_line += ".".join(longclsname_to_haxeclass(class_.longname).split(".")[:-1])
            else:
                package_line += "phaser"
            f.write(package_line + ";\n\n")
            f.write(class_.gen_haxe())


arg_parser = argparse.ArgumentParser(description="Generate haxe bindings for Phaser.")
arg_parser.add_argument('json_jsdoc', help="The jsdoc output (JSON format)")
arg_parser.add_argument('output_dir', help="The output dir")

args = arg_parser.parse_args()

main(args.json_jsdoc, Path(args.output_dir))

