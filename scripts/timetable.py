from html.parser import HTMLParser
import datetime as dt
from urllib.parse import quote

SOURCE = "https://timetable.magtu.ru/" + quote("АПОб-22-")


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ' '.join(' '.join(c.text() if isinstance(c, Node) else c for c in self.children).split())

    def find(self, cls):
        return next((n for n in self.walk() if cls in n.attrs.get('class', '').split()), None)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()


class Tree(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in self.VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_schedule(html):
    tree = Tree(html).root
    weeks = {}
    for w in (1, 2):
        block = next((n for n in tree.walk() if n.attrs.get('id') == f'week-{w}'), None)
        if block is None:
            raise ValueError('На странице отсутствует одна из недель')
        days = [[] for _ in range(6)]
        for cell in block.walk():
            ident = cell.attrs.get('id', '')
            if not ident.startswith('less-'):
                continue
            _, week_index, day, number = ident.split('-')
            day, number = int(day), int(number)
            if int(week_index) != w-1 or not 0 <= day < 6:
                raise ValueError('Изменилась структура расписания')
            for lesson in (n for n in cell.walk() if 'less' in n.attrs.get('class', '').split()):
                def value(cls):
                    n = lesson.find(cls)
                    return n.text() if n else ''
                title, teacher, timing = value('title'), value('teacher'), value('time')
                parts = timing.replace('—', '–').split('–')
                if not title or len(parts) != 2:
                    raise ValueError('Не удалось прочитать предмет или время')
                start, end = [p.strip() for p in parts]
                for t in (start, end):
                    dt.datetime.strptime(t, '%H:%M')
                ad = lesson.find('ad')
                kind = ad.text().replace(teacher, '').strip() if ad else ''
                days[day].append(dict(number=number, title=title, teacher=teacher,
                    room=value('aud'), kind=kind, start=start, end=end,
                    subgroup=' '.join(c for c in lesson.attrs.get('class', '').split() if c.startswith('group-'))))
        weeks[str(w)] = days
    if not sum(len(day) for days in weeks.values() for day in days):
        raise ValueError('Сайт вернул пустое расписание; сохранённая версия оставлена')
    return dict(group='АПОб-22-', source=SOURCE, weeks=weeks)


