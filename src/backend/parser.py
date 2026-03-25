from dataclasses import dataclass
from lxml import etree
from typing import Generator, List, Optional


@dataclass
class ElementData:
    id: str
    tag: str
    attrs: dict
    text: str
    path: str
    line: Optional[int] = None


class StreamParser:
    def __init__(self, input_path: str, ignore_tags: Optional[List[str]] = None, events=('end',)):
        self.input_path = input_path
        self.ignore_tags = set(ignore_tags or [])
        self.events = events

    def _build_path(self, elem: etree._Element) -> str:
        parts = []
        cur = elem
        while cur is not None:
            parts.append(etree.QName(cur).localname)
            cur = cur.getparent()
        return '/'.join(reversed(parts))

    def iter_elements(self) -> Generator[ElementData, None, None]:
        context = etree.iterparse(self.input_path, events=self.events, recover=True, huge_tree=True)
        for event, elem in context:
            tag = etree.QName(elem).localname
            if tag in self.ignore_tags:
                # clear and skip yielding this element
                parent = elem.getparent()
                elem.clear()
                if parent is not None:
                    try:
                        while parent.getprevious() is not None:
                            del parent.getparent()[0]
                    except Exception:
                        pass
                continue

            elem_id = elem.get('id') or elem.get('name') or ''
            text = (elem.text or '').strip()
            attrs = dict(elem.items())
            path = self._build_path(elem)
            line = getattr(elem, 'sourceline', None)
            yield ElementData(elem_id, tag, attrs, text, path, line)

            # free memory
            parent = elem.getparent()
            elem.clear()
            if parent is not None:
                try:
                    while parent.getprevious() is not None:
                        del parent.getparent()[0]
                except Exception:
                    pass
        try:
            del context
        except Exception:
            pass
