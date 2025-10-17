import re
from maya import cmds

def connect_attr(src: list, dest: list, debug_print=False) -> None:
    """
    ノードのアトリビュートを接続する関数。
    """

    for s, d in zip(src, dest):
        if s is None:
            continue

        if isinstance(s, str): # 文字列型
            if "." in s: # アトリビュート接続
                if "!" == s[-1]: # 値の転写
                    s = s[:-1]
                    cmds.connectAttr(s, d, f=True)
                    cmds.disconnectAttr(s, d)
                    continue

                else:
                    cmds.connectAttr(s, d, f=True)
                    continue

            else:
                cmds.setAttr(d, s, type="string")
                continue

        elif isinstance(s, list) or isinstance(s, tuple): # リスト型、もしくはタプル型 => matrix型
            if "matrix" == cmds.getAttr(d, type=True):
                cmds.setAttr(d, s, type="matrix")

            else:
                node_name = d.split(".")[0]
                attr_path = d.split(".")[1]
                base_attr_name = re.sub(r"\[\d+\]$", "", attr_path)
                child_names = cmds.attributeQuery(base_attr_name, node=node_name, listChildren=True)
                for s_, d_ in zip(s, child_names):
                    if s_ is None:
                        continue

                    d_ = f"{node_name}.{attr_path}.{d_}"

                    if isinstance(s_, str):
                        if "." in s_:
                            if "!" == s_[-1]:
                                s_ = s_[:-1]
                                cmds.connectAttr(s_, d_, f=True)
                                cmds.disconnectAttr(s_, d_)
                                continue

                            else:
                                cmds.connectAttr(s_, d_, f=True)
                                continue

                        else:
                            cmds.setAttr(d_, s_, type="string")
                            continue

                    else:
                        cmds.setAttr(d_, s_)
                        continue

            continue

        else:
            cmds.setAttr(d, s)
            continue


def sort_out_attr(name :str, data: dict, debug_print=False):
    src = []
    dest = []

    if debug_print:
        print("---- input data ----\n")
        for d in data:
            value = data[d]["value"]
            if not value:
                if value is None or isinstance(value, list):
                    continue

            print(data[d])
        print("\n--------------------")

    for d in data:
        key = d[:]
        d = data[d]
        value = d["value"]
        attr = f'{name}.{d["attr"]}'
        _type = d["type"]
        inout = d["inout"]
        childern = d["childern"]

        if not value:
            if value is None or isinstance(value, list):
                continue

        if inout == "input":
            if _type == "other" or _type == "matrix":
                src += [value]
                dest += [attr]
                continue

            if _type == "multi":
                for i, v in enumerate(value):
                    src += [v]
                    dest += [f"{attr}[{i}]"]
                continue

            if _type == "compound":
                if isinstance(value, str):
                    src += [value]
                    dest += [attr]
                    continue

                if isinstance(value, list) or isinstance(value, tuple):
                    for c, v in zip(childern, value):
                        src += [v]
                        dest += [f"{name}.{c}"]
                    continue

        elif inout == "output":
            if _type == "other" or _type == "matrix":
                for v in value:
                    src += [attr]
                    dest += [v]
                continue

            if _type == "compound":
                if isinstance(value, str):
                    value = [value]

                for v in value:
                    if ":" in v:
                        for s_, v_ in zip(childern, v.split(":")[1:]):
                            src += [f"{name}.{s_}"]
                            dest += [f'{v.split(":")[0]}{v_}']

                    else:
                        src += [attr]
                        dest += [v]
                continue

        cmds.error(f"{key}アトリビュートの引数が正しく処理されませんでした。 attr:{attr}")

    if debug_print:
        print("---- sort data ----\n")
        for s, d in zip(src, dest):
            print(f"{s} -> {d}")

        print("\n-------------------")

    return src, dest



def generate_func():
    """
    選択したノードの、作成、接続、設定を行う関数を生成する関数。  
    ノードに対応した関数がprintされます。
    """

    node = cmds.ls(sl=True)[0]
    node_type = cmds.nodeType(node)
    long_attrs = cmds.listAttr(node)
    short_attrs = cmds.listAttr(node, sn=True)

    func = f'\n# ↓ function\n\ndef {node_type}(node_name :str="", debug_print :bool=False'

    comment = "        node_name (str): ノードの名前を設定します。\n"
    comment = "        debug_print (bool): デバッグプリントを表示します。\n"
    tags = []
    keys = []

    for la, sa in zip(long_attrs, short_attrs):
        try:
            if cmds.attributeQuery(la, node=node, writable=True):
                if len(la.split('.', 1)) != 1:
                    pass

                elif "matrix" == cmds.getAttr(f"{node}.{la}", type=True):
                    func += f', {sa}=None'
                    comment += f'        {sa} (any): {la} を設定します type="matrix"\n'
                    tags += [[sa, la, "matrix", "input", None]]
                    keys += [sa]

                elif cmds.attributeQuery(la, node=node, multi=True):
                    func += f', {sa} :list=[]'
                    comment += f'        {sa} (list[any]): {la} を設定します。type="multi"\n'
                    tags += [[sa, la, "multi", "input", None]]
                    keys += [sa]

                elif cmds.attributeQuery(la, node=node, listChildren=True):
                    func += f', {sa}=None'
                    comment += f'        {sa} (any): {la} を設定します。type="compound"\n'
                    tags += [[sa, la, "compound", "input", cmds.attributeQuery(la, node=node, listChildren=True)]]
                    keys += [sa]

                else:
                    func += f', {sa}=None'
                    comment += f'        {sa} (any): {la} を設定します。type="other"\n'
                    tags += [[sa, la, "other", "input", None]]
                    keys += [sa]

        except RuntimeError:
            continue

    for la, sa in zip(long_attrs, short_attrs):
        try:
            if cmds.attributeQuery(la, node=node, readable=True):
                if len(la.split('.', 1)) != 1:
                    pass

                elif cmds.attributeQuery(la, node=node, multi=True):
                    pass

                elif cmds.attributeQuery(la, node=node, listChildren=True):
                    func += f', {sa}_dest :list[str]=[]'
                    comment += f'        {sa}_dest (list): {la} の目的側のアトリビュートを設定します。type="compound"\n'
                    tags += [[f"{sa}_dest", la, "compound", "output", cmds.attributeQuery(la, node=node, listChildren=True)]]
                    keys += [f"{sa}_dest"]

                elif "matrix" == cmds.getAttr(f"{node}.{la}", type=True):
                    func += f', {sa}_dest :list[str]=[]'
                    comment += f'        {sa}_dest (list): {la} の目的側のアトリビュートを設定します。type="matrix"\n'
                    tags += [[f"{sa}_dest", la, "other", "output", None]]
                    keys += [f"{sa}_dest"]

                else:
                    func += f', {sa}_dest :list[str]=[]'
                    comment += f'        {sa}_dest (list): {la} の目的側のアトリビュートを設定します。type="other"\n'
                    tags += [[f"{sa}_dest", la, "other", "output", None]]
                    keys += [f"{sa}_dest"]

        except RuntimeError:
            continue

    func += ') -> str:\n    """\n'
    func += f'    {node_type}ノードを作成、接続、設定します。  \n'
    func += '    アトリビュートのショートネームが各フラグ名と対応しています。  \n'
    func += '    \n'
    func += '    "src.attr"の形で記述すると、そのアトリビュートと接続します。値を与えることで直接設定することもできます。  \n'
    func += f'    └ attr="src.attr" ... src.attr →接続→ {node_type}.attr  \n'
    func += f'    └ attr="3" ... 3 →設定→ {node_type}.attr  \n'
    func += '    \n'
    func += '    アトリビュート名の末尾に"!"をつけることで、そのアトリビュートの値を転写することができます。  \n'
    func += f'    └ attr="src.attr!" ... src.attr →転写→ {node_type}.attr  \n'
    func += '    \n'
    func += '    "multi型のアトリビュート(attr[0], attr[1], attr[2] のようにインデックスで管理するアトリビュート)の場合、引数はリスト型になります。  \n'
    func += '    Noneを設定すると、そのインデックスの設定はスキップされます。  \n'
    func += f'    └ mult_attr=["src1.attr", "src2.attr!", None, 3] ... src1.attr →接続→ {node_type}.attr[0], src2.attr →転写→ {node_type}.attr[1], 設定しない→ {node_type}.attr[2], 3 →設定→ {node_type}.attr[3]  \n'
    func += '    \n'
    func += '    "compound型のアトリビュート(vectorやangleのように複数のアトリビュートを複合したアトリビュート)の場合、接続の場合"src.attr"の形の文字列、値の設定の場合、リストで設定します。  \n'
    func += '    Noneを設定すると、その要素の設定はスキップされます。  \n'
    func += f'    └ vector_attr= "src.attr" ... src.attr →接続→ {node_type}.attr  \n'
    func += f'    └ vector_attr= [2, 4, 1] ... 2, 4, 1 →設定→ {node_type}.attrX, Y, Z  \n'
    func += f'    └ vector_attr= ["src.attrX", 4, None] ... src.attrX →接続→ {node_type}.attrX, 4 →設定→ {node_type}.attrY, 設定しない→ {node_type}.attrZ  \n'
    func += '    \n'
    func += '    "multi型の要素の一つとしてcompound型のアトリビュートが内包されている場合、それぞれの設定方法を複合します。  \n'
    func += f'    └ multi_attr= [[0, 1, 2], "src.vectorAttr", None, [src.attrX!, 3, None]]  \n'
    func += '    \n'
    func += '    ショートネームの末尾に"_dest"がついているフラグは、ノードに対して目的側のアトリビュートをリストで設定します。  \n'
    func += f'    └ attr_dest=["dest1.attr", dest2.attr] ... {node_type}.attr →接続→ dest1.attr, {node_type}.attr →接続→ dest2.attr  \n'
    func += '    \n'
    func += '    dest付きかつ、compound型のアトリビュート名の末尾に、":"をつけると、その後に続く文字を目的側アトリビュートにつけ足し、順次接続を実行します。  \n'
    func += f'    └ attr_dest=["dest.attr:X:Y:Z"] ... {node_type}.attrR →接続→ dest.attrX, {node_type}.attrG →接続→ dest.attrY, {node_type}.attrB →接続→ dest.attrZ  \n'
    func += f'    └ attr_dest=["dest.attr:[0]:[1]:[2]"] ... {node_type}.attrX →接続→ dest.attr[0], {node_type}.attrY →接続→ dest.attr[1], {node_type}.attrZ →接続→ dest.attr[2]  \n'
    func += '    \n'
    func += '    Args:\n'
    func += comment
    func += '    Returns:\n'
    func += '    \n'
    func += '        str : 作成されたノード名。\n'
    func += '    """\n'
    func += '    \n'
    func += f'    _node = cmds.createNode("{node_type}", name=node_name)\n'
    func += '    \n'
    func += '    _data = {}\n'

    for key, tag in zip(keys, tags):
        func += f'    _data["{key}"] = {{"value":{tag[0]}, "attr":"{tag[1]}", "type":"{tag[2]}", "inout":"{tag[3]}", "childern":{tag[4]}}}\n'

    func += '    \n'
    func += '    _src, _dest = sort_out_attr(node_name, _data, debug_print=debug_print)\n'
    func += '    connect_attr(_src, _dest, debug_print=debug_print)\n'
    func += '    \n'
    func += f'    return _node'

    print(func)